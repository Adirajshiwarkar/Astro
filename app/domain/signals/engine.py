import datetime
from typing import Any

from app.domain.astrology.models import WesternChart
from app.domain.canonical.models import CanonicalChartRepresentation
from app.domain.numerology.models import NumerologyProfile
from app.domain.signals.models import (
    AstrologicalSignal,
    FactorPolarity,
    SignalDomain,
    SignalEngineOutput,
    SignalFactor,
    SignalType,
    SourceSystem,
)
from app.domain.signals.rules import (
    extract_canonical_signals,
    extract_numerology_signals,
    extract_vedic_signals,
    extract_western_signals,
)
from app.domain.vedic.models import VedicChart


class SignalEngine:
    """Deterministic, rule-based Signal Engine consuming normalized Western, Vedic,

    and Numerology factors across 10 life domains with cross-system correlation.
    """

    def __init__(self, rule_version: str = "1.0.0") -> None:
        self.rule_version = rule_version

    def evaluate_signals(
        self,
        western_chart: WesternChart | None = None,
        vedic_chart: VedicChart | None = None,
        numerology_profile: NumerologyProfile | None = None,
        canonical_chart: CanonicalChartRepresentation | None = None,
        timeframe: str = "natal",
    ) -> SignalEngineOutput:
        """Evaluate and aggregate domain signals across all provided astrological and numerological systems."""
        active_systems: list[str] = []
        domain_factors: dict[SignalDomain, list[SignalFactor]] = {d: [] for d in SignalDomain}

        # 1. Extract Western factors
        if western_chart is not None:
            active_systems.append("WESTERN")
            w_factors = extract_western_signals(western_chart)
            for dom, f_list in w_factors.items():
                domain_factors[dom].extend(f_list)

        # 2. Extract Vedic factors
        if vedic_chart is not None:
            active_systems.append("VEDIC")
            v_factors = extract_vedic_signals(vedic_chart)
            for dom, f_list in v_factors.items():
                domain_factors[dom].extend(f_list)

        # 3. Extract Numerology factors
        if numerology_profile is not None:
            active_systems.append("NUMEROLOGY")
            n_factors = extract_numerology_signals(numerology_profile)
            for dom, f_list in n_factors.items():
                domain_factors[dom].extend(f_list)

        # 4. Extract Canonical factors if provided
        if canonical_chart is not None and not (western_chart or vedic_chart):
            active_systems.append("CANONICAL")
            c_factors = extract_canonical_signals(canonical_chart)
            for dom, f_list in c_factors.items():
                domain_factors[dom].extend(f_list)

        total_active_systems = max(len(active_systems), 1)

        generated_signals: list[AstrologicalSignal] = []
        domain_scores: dict[str, float] = {}

        # 5. Process each domain deterministically
        for domain in SignalDomain:
            all_factors = domain_factors[domain]
            if not all_factors:
                # Default baseline signal if no specific factors present
                signal = AstrologicalSignal(
                    signal_id=f"SIG-{domain.value.upper()}-BASELINE",
                    domain=domain,
                    signal_type=SignalType.NEUTRAL,
                    strength=0.50,
                    timeframe=timeframe,
                    source_system=SourceSystem.CROSS_SYSTEM_CORRELATED if len(active_systems) > 1 else (
                        SourceSystem[active_systems[0]] if active_systems else SourceSystem.WESTERN
                    ),
                    supporting_factors=[],
                    conflicting_factors=[],
                    rule_version=self.rule_version,
                    correlation_score=1.0,
                )
                generated_signals.append(signal)
                domain_scores[domain.value] = 0.50
                continue

            supporting = [f for f in all_factors if f.polarity == FactorPolarity.POSITIVE]
            conflicting = [f for f in all_factors if f.polarity == FactorPolarity.NEGATIVE]

            sum_pos = sum(f.weight for f in supporting)
            sum_neg = sum(f.weight for f in conflicting)
            sum_total = sum(f.weight for f in all_factors)

            # Mathematical strength formula: RawScore / max(total_weight, 1.0)
            raw_score = sum_pos - (0.5 * sum_neg)
            normalized_strength = max(0.0, min(1.0, raw_score / max(sum_total, 1.0)))

            # Cross-system correlation: distinct systems providing supporting factors
            contributing_systems = {f.source_system for f in supporting}
            correlation = round(len(contributing_systems) / total_active_systems, 2)

            # Source system attribution
            if len(contributing_systems) > 1:
                source_sys = SourceSystem.CROSS_SYSTEM_CORRELATED
            elif len(contributing_systems) == 1:
                source_sys = next(iter(contributing_systems))
            else:
                source_sys = SourceSystem.CROSS_SYSTEM_CORRELATED

            # Classify signal type deterministically
            if domain == SignalDomain.PERSONAL_DEVELOPMENT and normalized_strength >= 0.75:
                sig_type = SignalType.TRANSFORMATION
            elif len(conflicting) >= len(supporting) and sum_neg > sum_pos:
                sig_type = SignalType.CHALLENGE
            elif normalized_strength >= 0.70:
                sig_type = SignalType.OPPORTUNITY
            elif any("Personal Year" in f.timeframe or "cycle" in f.timeframe for f in all_factors):
                sig_type = SignalType.TRANSITION
            elif normalized_strength >= 0.45:
                sig_type = SignalType.STABILITY
            else:
                sig_type = SignalType.NEUTRAL

            signal = AstrologicalSignal(
                signal_id=f"SIG-{domain.value.upper()}-{len(generated_signals) + 1:03d}",
                domain=domain,
                signal_type=sig_type,
                strength=round(normalized_strength, 4),
                timeframe=timeframe,
                source_system=source_sys,
                supporting_factors=supporting,
                conflicting_factors=conflicting,
                rule_version=self.rule_version,
                correlation_score=correlation,
            )
            generated_signals.append(signal)
            domain_scores[domain.value] = round(normalized_strength, 4)

        return SignalEngineOutput(
            signals=generated_signals,
            domain_scores=domain_scores,
            engine_version=self.rule_version,
            evaluated_systems=active_systems,
        )
