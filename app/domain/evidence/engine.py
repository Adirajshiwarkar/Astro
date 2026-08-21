from collections import defaultdict
from typing import Any

from app.domain.evidence.mapper import EvidenceMapper
from app.domain.evidence.models import (
    CrossSystemAgreement,
    CrossSystemDisagreement,
    EvidenceItem,
    EvidenceReport,
    EvidenceScore,
    SignalExplanation,
)
from app.domain.signals.models import AstrologicalSignal, FactorPolarity, SignalDomain


class EvidenceEngine:
    """Deterministic, rule-based Evidence Engine providing complete provenance,

    cross-system consensus/divergence analysis, and audit trails for all astrological signals.
    """

    def __init__(
        self,
        mapper: EvidenceMapper | None = None,
        engine_version: str = "1.0.0",
    ) -> None:
        self.mapper = mapper or EvidenceMapper(engine_version=engine_version)
        self.engine_version = engine_version

    def generate_evidence_for_signal(self, signal: AstrologicalSignal) -> SignalExplanation:
        """Generate structured evidence, cross-system consensus, and audit trail for a signal."""
        supporting_items: list[EvidenceItem] = []
        conflicting_items: list[EvidenceItem] = []
        audit_trail: list[str] = []

        audit_trail.append(
            f"1. Initiated evidence trace for Signal ID: {signal.signal_id} (Domain: {signal.domain.value.upper()})."
        )
        audit_trail.append(
            f"2. Signal Classification: {signal.signal_type.value}, Calculated Strength: {signal.strength:.4f}, Timeframe: {signal.timeframe}."
        )

        # 1. Map Supporting Factors
        for i, factor in enumerate(signal.supporting_factors, start=1):
            evid = self.mapper.factor_to_evidence(factor, signal.domain, counter=i)
            supporting_items.append(evid)
            audit_trail.append(
                f"   - Supporting Evidence #{i}: [{evid.source_system}] {evid.source_factor} (Weight: {evid.strength:.2f}, Rule: {evid.rule_reference})."
            )

        # 2. Map Conflicting Factors
        for j, factor in enumerate(signal.conflicting_factors, start=1):
            evid = self.mapper.factor_to_evidence(factor, signal.domain, counter=len(supporting_items) + j)
            conflicting_items.append(evid)
            audit_trail.append(
                f"   - Conflicting Evidence #{j}: [{evid.source_system}] {evid.source_factor} (Weight: {evid.strength:.2f}, Rule: {evid.rule_reference})."
            )

        # 3. Calculate Deterministic Evidence Score
        sup_weight = sum(e.strength for e in supporting_items)
        conf_weight = sum(e.strength for e in conflicting_items)
        total_weight = sup_weight + conf_weight
        net_score = max(0.0, min(1.0, (sup_weight - 0.5 * conf_weight) / max(total_weight, 1.0)))

        supporting_systems = {e.source_system for e in supporting_items}
        conflicting_systems = {e.source_system for e in conflicting_items}
        all_systems = supporting_systems | conflicting_systems

        agreement_score = len(supporting_systems) / max(len(all_systems), 1)

        evidence_score = EvidenceScore(
            total_evidence_count=len(supporting_items) + len(conflicting_items),
            supporting_count=len(supporting_items),
            conflicting_count=len(conflicting_items),
            supporting_weight_sum=round(sup_weight, 4),
            conflicting_weight_sum=round(conf_weight, 4),
            net_evidence_score=round(net_score, 4),
            agreement_score=round(agreement_score, 4),
        )

        audit_trail.append(
            f"3. Score Derivation: Supporting Weight={sup_weight:.2f}, Conflicting Weight={conf_weight:.2f}, "
            f"Net Score={net_score:.4f}, System Agreement Rate={agreement_score * 100.0:.1f}%."
        )

        # 4. Analyze Cross-System Agreements
        agreements: list[CrossSystemAgreement] = []
        if len(supporting_systems) >= 2:
            agr_desc = (
                f"Cross-system convergence detected in {signal.domain.value} domain across "
                f"{len(supporting_systems)} systems ({', '.join(sorted(supporting_systems))})."
            )
            agreements.append(
                CrossSystemAgreement(
                    domain=signal.domain,
                    concurring_systems=sorted(list(supporting_systems)),
                    evidence_items=supporting_items,
                    consensus_strength=round(sup_weight / max(len(supporting_systems), 1), 4),
                    description=agr_desc,
                )
            )
            audit_trail.append(f"4. Cross-System Agreement: {agr_desc}")

        # 5. Analyze Cross-System Disagreements
        disagreements: list[CrossSystemDisagreement] = []
        overlap_opposing = supporting_systems & conflicting_systems
        purely_opposing = conflicting_systems - supporting_systems

        if conflicting_items and (overlap_opposing or purely_opposing):
            dis_desc = (
                f"Cross-system tension detected in {signal.domain.value} domain. "
                f"Supporting systems: {sorted(list(supporting_systems))}; "
                f"Challenging systems: {sorted(list(conflicting_systems))}."
            )
            disagreements.append(
                CrossSystemDisagreement(
                    domain=signal.domain,
                    supporting_systems=sorted(list(supporting_systems)),
                    conflicting_systems=sorted(list(conflicting_systems)),
                    supporting_items=supporting_items,
                    conflicting_items=conflicting_items,
                    divergence_level=round(conf_weight / max(total_weight, 1.0), 4),
                    description=dis_desc,
                )
            )
            audit_trail.append(f"5. Cross-System Disagreement: {dis_desc}")

        # 6. Synthesize Deterministic "Why Generated" Summary
        if not supporting_items and not conflicting_items:
            why_summary = (
                f"Signal {signal.signal_id} assigned baseline neutral status (0.50) due to absence "
                f"of active domain indicators in {signal.domain.value}."
            )
        elif len(supporting_systems) >= 2:
            why_summary = (
                f"Signal {signal.signal_id} generated with {signal.signal_type.value} classification (strength {signal.strength:.2f}) "
                f"driven by cross-system consensus across {', '.join(sorted(supporting_systems))} "
                f"with {len(supporting_items)} supporting factors (net score {net_score:.2f})."
            )
        else:
            prime_sys = next(iter(supporting_systems)) if supporting_systems else "SYSTEM"
            why_summary = (
                f"Signal {signal.signal_id} generated based on {prime_sys} system indicators "
                f"with {len(supporting_items)} supporting and {len(conflicting_items)} conflicting factors."
            )

        audit_trail.append(f"6. Final Explanation: {why_summary}")

        return SignalExplanation(
            signal_id=signal.signal_id,
            domain=signal.domain,
            signal_type=signal.signal_type,
            signal_strength=signal.strength,
            timeframe=signal.timeframe,
            source_system=signal.source_system,
            why_generated_summary=why_summary,
            evidence_score=evidence_score,
            supporting_evidence=supporting_items,
            conflicting_evidence=conflicting_items,
            cross_system_agreements=agreements,
            cross_system_disagreements=disagreements,
            audit_trail=audit_trail,
        )

    def generate_evidence_report(self, signals: list[AstrologicalSignal]) -> EvidenceReport:
        """Compile a comprehensive master EvidenceReport for an array of signals."""
        explanations: dict[str, SignalExplanation] = {}
        total_items = 0
        sys_counts: dict[str, int] = defaultdict(int)
        total_agr = 0
        total_dis = 0

        for sig in signals:
            exp = self.generate_evidence_for_signal(sig)
            explanations[sig.signal_id] = exp
            total_items += len(exp.supporting_evidence) + len(exp.conflicting_evidence)
            total_agr += len(exp.cross_system_agreements)
            total_dis += len(exp.cross_system_disagreements)

            for e in exp.supporting_evidence + exp.conflicting_evidence:
                sys_counts[e.source_system] += 1

        return EvidenceReport(
            explanations=explanations,
            total_evidence_items=total_items,
            system_breakdown=dict(sys_counts),
            cross_system_agreements_count=total_agr,
            cross_system_disagreements_count=total_dis,
        )

    def explain_signal(self, signal_id: str, report: EvidenceReport) -> SignalExplanation:
        """Lookup and return the deterministic explanation for a specific signal ID."""
        if signal_id not in report.explanations:
            raise KeyError(f"Signal ID '{signal_id}' not found in EvidenceReport.")
        return report.explanations[signal_id]
