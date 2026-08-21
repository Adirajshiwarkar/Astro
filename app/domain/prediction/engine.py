import datetime
from typing import Any

from app.domain.evidence.engine import EvidenceEngine
from app.domain.evidence.models import EvidenceItem, EvidenceReport
from app.domain.prediction.models import (
    CandidateEvent,
    ForecastingWindow,
    PredictionRequest,
    PredictionResponse,
    TimeWindowConfig,
    UncertaintyLevel,
    UncertaintyMetadata,
)
from app.domain.signals.models import AstrologicalSignal, FactorPolarity, SignalDomain, SignalType

DOMAIN_EVENT_TITLES: dict[SignalDomain, dict[str, str]] = {
    SignalDomain.CAREER: {
        "OPPORTUNITY": "Professional Advancement & Executive Authority Acceleration",
        "CHALLENGE": "Structural Career Realignment & Responsibility Resistance",
        "TRANSITION": "Professional Role Evolution & Sector Pivot",
        "STABILITY": "Career Status Consolidation & Established Operational Flow",
        "TRANSFORMATION": "Complete Professional Identity Metamorphosis",
        "NEUTRAL": "Routine Professional Cadence",
    },
    SignalDomain.FINANCE: {
        "OPPORTUNITY": "Resource Consolidation & Capital Growth Expansion",
        "CHALLENGE": "Resource Pressure & Fiscal Rebalancing Phase",
        "TRANSITION": "Financial Restructuring & Investment Pivot",
        "STABILITY": "Steady Resource Flow & Fiscal Security",
        "TRANSFORMATION": "Wealth Architecture Overhaul",
        "NEUTRAL": "Baseline Financial Maintenance",
    },
    SignalDomain.RELATIONSHIP: {
        "OPPORTUNITY": "Interpersonal Harmony & Significant Partnership Synergy",
        "CHALLENGE": "Relational Friction & Boundary Clarification Demand",
        "TRANSITION": "Relationship Dynamics Shift & Covenant Recalibration",
        "STABILITY": "Harmonious Interpersonal Stability",
        "TRANSFORMATION": "Deep Relational Rebirth & Bond Realignment",
        "NEUTRAL": "Standard Relational Balance",
    },
    SignalDomain.MARRIAGE: {
        "OPPORTUNITY": "Solemn Domestic Commitment & Marital Auspiciousness",
        "CHALLENGE": "Marital Tension & Mutual Expectation Alignment Phase",
        "TRANSITION": "Domestic Relationship Structural Evolution",
        "STABILITY": "Marital Stability & Enduring Domestic Harmony",
        "TRANSFORMATION": "Marital Transformation & Foundational Realignment",
        "NEUTRAL": "Equable Marital Status",
    },
    SignalDomain.EDUCATION: {
        "OPPORTUNITY": "Intellectual Mastery & Advanced Knowledge Acquisition",
        "CHALLENGE": "Academic Rigor & Intellectual Friction Point",
        "TRANSITION": "Disciplinary Transition & Analytical Shift",
        "STABILITY": "Consistent Academic Progression",
        "TRANSFORMATION": "Philosophical & Epistemological Breakthrough",
        "NEUTRAL": "Routine Educational Trajectory",
    },
    SignalDomain.BUSINESS: {
        "OPPORTUNITY": "Commercial Enterprise Scaling & Venture Launch",
        "CHALLENGE": "Market Friction & Business Operational Headwinds",
        "TRANSITION": "Commercial Pivot & Business Model Adaptation",
        "STABILITY": "Commercial Operational Equilibrium",
        "TRANSFORMATION": "Enterprise Restructuring & Market Disruptive Pivot",
        "NEUTRAL": "Steady Commercial Flow",
    },
    SignalDomain.TRAVEL: {
        "OPPORTUNITY": "Auspicious Long-Distance Travel & Geographic Expansion",
        "CHALLENGE": "Transit Disruption & Travel Logistics Friction",
        "TRANSITION": "Dynamic Movement & Multi-Location Transitions",
        "STABILITY": "Local Mobility & Low-Volatility Travel Cadence",
        "TRANSFORMATION": "Pilgrimage & Life-Altering Transnational Journey",
        "NEUTRAL": "Routine Local Travel",
    },
    SignalDomain.RELOCATION: {
        "OPPORTUNITY": "Favorable Domestic Relocation & Residential Migration",
        "CHALLENGE": "Domestic Relocation Friction & Housing Delays",
        "TRANSITION": "Residential Transition & Living Space Mutation",
        "STABILITY": "Rooted Domestic Stability & Territorial Invariance",
        "TRANSFORMATION": "Complete Homeland Disconnection & Transnational Move",
        "NEUTRAL": "Residential Status Quo",
    },
    SignalDomain.FAMILY: {
        "OPPORTUNITY": "Domestic Auspiciousness & Lineage Cohesion",
        "CHALLENGE": "Domestic Responsibility Surge & Kinship Friction",
        "TRANSITION": "Family Structural Evolution & Generational Transition",
        "STABILITY": "Household Harmony & Domestic Security",
        "TRANSFORMATION": "Family System Transformation",
        "NEUTRAL": "Equable Family Flow",
    },
    SignalDomain.PERSONAL_DEVELOPMENT: {
        "OPPORTUNITY": "Consciousness Awakening & Self-Actualization Surge",
        "CHALLENGE": "Existential Crucible & Shadow Integration Demand",
        "TRANSITION": "Personal Paradigm Shift & Core Values Realignment",
        "STABILITY": "Character Integration & Grounded Self-Awareness",
        "TRANSFORMATION": "Total Spiritual Metamorphosis & Inner Rebirth",
        "NEUTRAL": "Standard Personal Growth Continuum",
    },
}


class PredictionEngine:
    """Deterministic Prediction Engine forecasting candidate astrological events

    mapped from normalized charts, signals, and evidence across structured time windows.
    """

    def __init__(
        self,
        evidence_engine: EvidenceEngine | None = None,
        engine_version: str = "1.0.0",
    ) -> None:
        self.evidence_engine = evidence_engine or EvidenceEngine()
        self.engine_version = engine_version

    def predict(self, request: PredictionRequest) -> PredictionResponse:
        """Forecast candidate events and uncertainty metadata deterministically."""
        start_d = request.time_window.start_date
        end_d = request.time_window.get_end_date()
        timeframe_str = (
            f"{start_d.isoformat()} to {end_d.isoformat()} "
            f"({request.time_window.window_type.value} window)"
        )

        # 1. Collect all evidence items
        evidence_items_by_domain: dict[SignalDomain, list[EvidenceItem]] = {
            d: [] for d in SignalDomain
        }
        if isinstance(request.evidence, EvidenceReport):
            for exp in request.evidence.explanations.values():
                evidence_items_by_domain[exp.domain].extend(
                    exp.supporting_evidence + exp.conflicting_evidence
                )
        elif isinstance(request.evidence, list):
            for item in request.evidence:
                # Infer domain from item ID
                for dom in SignalDomain:
                    if dom.value.upper() in item.evidence_id:
                        evidence_items_by_domain[dom].append(item)
                        break

        # Filter target domains
        domains_to_evaluate = (
            [request.domain] if request.domain is not None else list(SignalDomain)
        )

        # If user query provided without explicit domain, perform deterministic keyword routing
        if request.user_query and request.domain is None:
            q_lower = request.user_query.lower()
            detected_domains = []
            for dom in SignalDomain:
                if dom.value in q_lower or (dom == SignalDomain.CAREER and "job" in q_lower) or (dom == SignalDomain.FINANCE and "money" in q_lower):
                    detected_domains.append(dom)
            if detected_domains:
                domains_to_evaluate = detected_domains

        candidate_events: list[CandidateEvent] = []
        all_supporting: list[EvidenceItem] = []
        all_conflicting: list[EvidenceItem] = []

        # 2. Build candidate events from signals
        signals_by_domain = {s.domain: s for s in request.signals}

        for dom in domains_to_evaluate:
            sig = signals_by_domain.get(dom)
            dom_evidence = evidence_items_by_domain.get(dom, [])

            if sig:
                sig_type_str = sig.signal_type.value if hasattr(sig.signal_type, "value") else str(sig.signal_type)
                event_title = DOMAIN_EVENT_TITLES.get(dom, {}).get(
                    sig_type_str, f"{dom.value.title()} Event Pattern"
                )

                # Extract supporting & conflicting evidence
                supporting_ev = [e for e in dom_evidence if e.polarity == FactorPolarity.POSITIVE]
                conflicting_ev = [e for e in dom_evidence if e.polarity == FactorPolarity.NEGATIVE]

                if not dom_evidence and (sig.supporting_factors or sig.conflicting_factors):
                    # Generate evidence on the fly via evidence engine
                    exp = self.evidence_engine.generate_evidence_for_signal(sig)
                    supporting_ev = exp.supporting_evidence
                    conflicting_ev = exp.conflicting_evidence

                # Calculate deterministic support score
                sup_w = sum(e.strength for e in supporting_ev)
                conf_w = sum(e.strength for e in conflicting_ev)
                total_w = sup_w + conf_w

                if total_w > 0:
                    score = max(0.0, min(1.0, (sup_w - 0.5 * conf_w) / max(total_w, 1.0)))
                else:
                    score = sig.strength

                # Evaluate Uncertainty Metadata
                unc_factors = []
                if conflicting_ev:
                    unc_factors.append(
                        f"Cross-factor tension: {len(conflicting_ev)} conflicting indicators detected in {dom.value}."
                    )
                if score < 0.50:
                    unc_factors.append(f"Low net alignment index ({score:.2f}) for this domain.")
                if request.time_window.window_type in (ForecastingWindow.TEN_MONTHS, ForecastingWindow.TWELVE_MONTHS):
                    unc_factors.append("Extended temporal horizon increases long-range transit variability.")

                if len(conflicting_ev) >= len(supporting_ev) and conflicting_ev:
                    unc_level = UncertaintyLevel.HIGH
                elif unc_factors:
                    unc_level = UncertaintyLevel.MODERATE
                elif not supporting_ev and not conflicting_ev:
                    unc_level = UncertaintyLevel.INDETERMINATE
                else:
                    unc_level = UncertaintyLevel.LOW

                unc_meta = UncertaintyMetadata(
                    uncertainty_level=unc_level,
                    uncertainty_factors=unc_factors,
                )

                event = CandidateEvent(
                    event_id=f"EVT-{dom.value.upper()}-{len(candidate_events) + 1:03d}",
                    title=event_title,
                    event_type=sig_type_str,
                    domain=dom,
                    timeframe=timeframe_str,
                    support_score=round(score, 4),
                    supporting_evidence=supporting_ev,
                    conflicting_evidence=conflicting_ev,
                    uncertainty_metadata=unc_meta,
                    traceable_signal_ids=[sig.signal_id],
                )

                candidate_events.append(event)
                all_supporting.extend(supporting_ev)
                all_conflicting.extend(conflicting_ev)

        # 3. Overall response aggregation
        if candidate_events:
            overall_score = round(
                sum(e.support_score for e in candidate_events) / len(candidate_events), 4
            )
            has_high_unc = any(
                e.uncertainty_metadata.uncertainty_level == UncertaintyLevel.HIGH
                for e in candidate_events
            )
            overall_unc_level = (
                UncertaintyLevel.HIGH
                if has_high_unc
                else (
                    UncertaintyLevel.MODERATE
                    if any(
                        e.uncertainty_metadata.uncertainty_level == UncertaintyLevel.MODERATE
                        for e in candidate_events
                    )
                    else UncertaintyLevel.LOW
                )
            )
        else:
            overall_score = 0.50
            overall_unc_level = UncertaintyLevel.INDETERMINATE

        response_unc_meta = UncertaintyMetadata(
            uncertainty_level=overall_unc_level,
            uncertainty_factors=[
                factor
                for event in candidate_events
                for factor in event.uncertainty_metadata.uncertainty_factors
            ],
        )

        return PredictionResponse(
            candidate_events=candidate_events,
            domain=request.domain,
            timeframe=timeframe_str,
            overall_support_score=overall_score,
            supporting_evidence=all_supporting,
            conflicting_evidence=all_conflicting,
            uncertainty_metadata=response_unc_meta,
            engine_version=self.engine_version,
        )
