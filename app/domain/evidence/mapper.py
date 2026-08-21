from typing import Any

from app.domain.evidence.models import EvidenceItem
from app.domain.signals.models import FactorPolarity, SignalDomain, SignalFactor, SourceSystem


class EvidenceMapper:
    """Deterministic mapper converting SignalFactors and astronomical parameters into EvidenceItems."""

    def __init__(self, engine_version: str = "1.0.0") -> None:
        self.engine_version = engine_version

    def factor_to_evidence(
        self,
        factor: SignalFactor,
        domain: SignalDomain,
        counter: int = 1,
    ) -> EvidenceItem:
        """Map a domain SignalFactor into a traceable EvidenceItem."""
        sys_name = factor.source_system.value if hasattr(factor.source_system, "value") else str(factor.source_system)
        evid_id = f"EVID-{domain.value.upper()}-{sys_name}-{counter:03d}"

        # Formulate canonical rule reference
        rule_ref = f"RULE_{sys_name}_{domain.value.upper()}_{factor.factor_id.replace('-', '_')}_v1"

        # Methodology description
        if sys_name == "WESTERN":
            methodology = "Western Tropical Zodiac with Placidus/Topocentric House Cusps and Ptolemaic Aspects"
        elif sys_name == "VEDIC":
            methodology = "Vedic Sidereal Lahiri Zodiac with Whole Sign Bhavas, Parashari Drishtis, and Vimshottari Dashas"
        elif sys_name == "NUMEROLOGY":
            methodology = "Pythagorean Numerology Reduction and Cyclical Vibration System"
        else:
            methodology = "Cross-System Unified Canonical Astrological Engine"

        # Calculation reference
        if factor.metadata:
            calc_ref = f"Params: {factor.metadata} | Weight: {factor.weight:.2f} | Polarity: {factor.polarity.value}"
        else:
            calc_ref = f"Calculation: {factor.description} | Weight: {factor.weight:.2f} | Polarity: {factor.polarity.value}"

        return EvidenceItem(
            evidence_id=evid_id,
            source_system=sys_name,
            source_factor=factor.name,
            calculation_reference=calc_ref,
            rule_reference=rule_ref,
            strength=factor.weight,
            timeframe=factor.timeframe,
            methodology=methodology,
            engine_version=self.engine_version,
            polarity=factor.polarity,
        )
