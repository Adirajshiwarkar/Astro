from app.domain.evidence.models import EvidenceItem, EvidenceReport
from app.domain.prediction.models import (
    Scenario,
    ScenarioSet,
    UncertaintyLevel,
    UncertaintyMetadata,
)
from app.domain.signals.models import (
    AstrologicalSignal,
    FactorPolarity,
    SignalDomain,
    SignalType,
)


class ScenarioEngine:
    """ScenarioEngine generates structured primary, alternative, and challenge/conflicting scenarios

    deterministically, without using an LLM or generating prose.
    """

    def __init__(self, engine_version: str = "1.0.0") -> None:
        self.engine_version = engine_version

    def generate_scenarios(
        self,
        domain: SignalDomain,
        signals: list[AstrologicalSignal],
        evidence: list[EvidenceItem] | EvidenceReport | None = None,
        timeframe: str = "6_months",
    ) -> ScenarioSet:
        """Deterministically generate a set of primary, alternative, and challenge scenarios for a domain."""
        # 1. Filter signals for the given domain
        domain_signals = [s for s in signals if s.domain == domain]
        if not domain_signals:
            from app.domain.signals.models import SourceSystem
            baseline_sig = AstrologicalSignal(
                signal_id=f"SIG-{domain.value.upper()}-BASELINE",
                domain=domain,
                signal_type=SignalType.NEUTRAL,
                strength=0.50,
                timeframe=timeframe,
                source_system=SourceSystem.WESTERN,
                supporting_factors=[],
                conflicting_factors=[],
                rule_version="1.0.0",
                correlation_score=1.0,
            )
            domain_signals = [baseline_sig]

        # 2. Filter evidence items for the given domain
        domain_evidence: list[EvidenceItem] = []
        if isinstance(evidence, EvidenceReport):
            if domain in evidence.explanations:
                expl = evidence.explanations[domain]
                domain_evidence.extend(expl.supporting_evidence)
                domain_evidence.extend(expl.conflicting_evidence)
        elif isinstance(evidence, list):
            for item in evidence:
                if domain.value.upper() in item.evidence_id.upper() or item.evidence_id.startswith(f"EVID-{domain.value.upper()}"):
                    domain_evidence.append(item)

        # Split evidence by polarity
        pos_evidence = [e for e in domain_evidence if e.polarity == FactorPolarity.POSITIVE]
        neg_evidence = [e for e in domain_evidence if e.polarity == FactorPolarity.NEGATIVE]

        # 3. Construct Primary Scenario
        primary_sig = max(domain_signals, key=lambda s: s.strength)
        is_primary_challenge = (primary_sig.signal_type == SignalType.CHALLENGE)

        if not is_primary_challenge:
            primary_support_sigs = [s for s in domain_signals if s.signal_type != SignalType.CHALLENGE]
            primary_conflict_sigs = [s for s in domain_signals if s.signal_type == SignalType.CHALLENGE]
            primary_evidence = pos_evidence
            pos_weight = sum(e.strength for e in pos_evidence)
            neg_weight = sum(e.strength for e in neg_evidence)
            if pos_weight + neg_weight > 0:
                primary_score = max(0.0, min(1.0, (pos_weight - 0.5 * neg_weight) / (pos_weight + neg_weight)))
            else:
                primary_score = primary_sig.strength
        else:
            primary_support_sigs = [s for s in domain_signals if s.signal_type == SignalType.CHALLENGE]
            primary_conflict_sigs = [s for s in domain_signals if s.signal_type != SignalType.CHALLENGE]
            primary_evidence = neg_evidence
            neg_weight = sum(e.strength for e in neg_evidence)
            pos_weight = sum(e.strength for e in pos_evidence)
            if pos_weight + neg_weight > 0:
                primary_score = max(0.0, min(1.0, (neg_weight - 0.5 * pos_weight) / (pos_weight + neg_weight)))
            else:
                primary_score = primary_sig.strength

        primary_unc_factors = []
        if primary_conflict_sigs or neg_evidence:
            primary_unc_factors.append(f"Friction detected: {len(neg_evidence)} conflicting factors present in {domain.value}.")
        if primary_score < 0.50:
            primary_unc_factors.append(f"Low support score ({primary_score:.2f}) indicates high baseline uncertainty.")

        if primary_score >= 0.75:
            primary_unc_level = UncertaintyLevel.LOW
        elif primary_score >= 0.45:
            primary_unc_level = UncertaintyLevel.MODERATE
        else:
            primary_unc_level = UncertaintyLevel.HIGH

        primary_uncertainty = UncertaintyMetadata(
            uncertainty_level=primary_unc_level,
            uncertainty_factors=primary_unc_factors,
        )

        primary_scenario = Scenario(
            scenario_id=f"SCEN-{domain.value.upper()}-PRIMARY",
            domain=domain,
            timeframe=timeframe,
            support_score=round(primary_score, 4),
            evidence=primary_evidence,
            supporting_signals=primary_support_sigs,
            conflicting_signals=primary_conflict_sigs,
            uncertainty=primary_uncertainty,
        )

        # 4. Construct Alternative Scenario
        alt_sigs = [s for s in domain_signals if s.signal_type in (SignalType.STABILITY, SignalType.TRANSITION, SignalType.NEUTRAL)]
        if not alt_sigs:
            alt_sigs = [primary_sig]

        alt_score = round(max(0.30, primary_score * 0.75), 4)
        alt_unc_factors = ["Alternative development path represents a secondary, lower-probability trajectory."]
        if neg_evidence:
            alt_unc_factors.append("Presence of conflicting factors increases alternative scenario variability.")

        alt_unc_level = UncertaintyLevel.LOW if alt_score >= 0.75 else (UncertaintyLevel.MODERATE if alt_score >= 0.45 else UncertaintyLevel.HIGH)
        alt_uncertainty = UncertaintyMetadata(
            uncertainty_level=alt_unc_level,
            uncertainty_factors=alt_unc_factors,
        )

        alternative_scenario = Scenario(
            scenario_id=f"SCEN-{domain.value.upper()}-ALTERNATIVE",
            domain=domain,
            timeframe=timeframe,
            support_score=alt_score,
            evidence=pos_evidence if not is_primary_challenge else neg_evidence,
            supporting_signals=alt_sigs,
            conflicting_signals=[s for s in domain_signals if s not in alt_sigs],
            uncertainty=alt_uncertainty,
        )

        # 5. Construct Challenge / Conflicting Scenario
        challenge_sigs = [s for s in domain_signals if s.signal_type == SignalType.CHALLENGE]
        if not challenge_sigs:
            challenge_sigs = [s for s in domain_signals if s.strength < 0.60] or [primary_sig]

        neg_weight = sum(e.strength for e in neg_evidence)
        if neg_weight > 0:
            challenge_score = min(1.0, neg_weight / len(neg_evidence))
        else:
            challenge_score = round(max(0.10, 1.0 - primary_score), 4)

        challenge_unc_factors = ["Challenge path represents potential friction, delays, or opposing developmental forces."]
        if pos_evidence:
            challenge_unc_factors.append("Strong positive indicators act as countervailing stabilizers against this challenge.")

        challenge_unc_level = UncertaintyLevel.LOW if challenge_score >= 0.75 else (UncertaintyLevel.MODERATE if challenge_score >= 0.45 else UncertaintyLevel.HIGH)
        challenge_uncertainty = UncertaintyMetadata(
            uncertainty_level=challenge_unc_level,
            uncertainty_factors=challenge_unc_factors,
        )

        challenge_scenario = Scenario(
            scenario_id=f"SCEN-{domain.value.upper()}-CHALLENGE",
            domain=domain,
            timeframe=timeframe,
            support_score=round(challenge_score, 4),
            evidence=neg_evidence if neg_evidence else pos_evidence,
            supporting_signals=challenge_sigs,
            conflicting_signals=[s for s in domain_signals if s not in challenge_sigs],
            uncertainty=challenge_uncertainty,
        )

        return ScenarioSet(
            primary=primary_scenario,
            alternative=alternative_scenario,
            challenge=challenge_scenario,
        )
