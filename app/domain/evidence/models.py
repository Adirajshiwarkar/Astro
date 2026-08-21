from typing import Any
from pydantic import BaseModel, Field

from app.domain.signals.models import FactorPolarity, SignalDomain, SignalType, SourceSystem


class EvidenceItem(BaseModel):
    evidence_id: str = Field(..., description="Deterministic unique evidence identifier")
    source_system: str = Field(..., description="Origin system: WESTERN, VEDIC, NUMEROLOGY, IMAGE_EXTRACTION, EPHEMERIS")
    source_factor: str = Field(..., description="Specific astrological placement, aspect, or cycle")
    calculation_reference: str = Field(..., description="Exact parameter values and intermediate computation details")
    rule_reference: str = Field(..., description="Canonical rule code identifier")
    strength: float = Field(default=1.0, ge=0.0, le=1.0, description="Evidence intensity score")
    timeframe: str = Field(default="natal", description="Applicable timeframe")
    methodology: str = Field(..., description="Formal methodology definition")
    engine_version: str = Field(default="1.0.0", description="Engine version identifier")
    polarity: FactorPolarity = Field(default=FactorPolarity.POSITIVE, description="Supporting or conflicting polarity")


class CrossSystemAgreement(BaseModel):
    domain: SignalDomain = Field(..., description="Life domain for the agreement")
    concurring_systems: list[str] = Field(..., description="List of concurring source systems")
    evidence_items: list[EvidenceItem] = Field(default_factory=list, description="Associated evidence items")
    consensus_strength: float = Field(..., ge=0.0, le=1.0, description="Aggregated consensus strength")
    description: str = Field(..., description="Deterministic agreement breakdown")


class CrossSystemDisagreement(BaseModel):
    domain: SignalDomain = Field(..., description="Life domain for the disagreement")
    supporting_systems: list[str] = Field(..., description="Systems contributing positive evidence")
    conflicting_systems: list[str] = Field(..., description="Systems contributing negative/challenging evidence")
    supporting_items: list[EvidenceItem] = Field(default_factory=list, description="Supporting evidence items")
    conflicting_items: list[EvidenceItem] = Field(default_factory=list, description="Conflicting evidence items")
    divergence_level: float = Field(..., ge=0.0, le=1.0, description="Divergence intensity")
    description: str = Field(..., description="Deterministic disagreement breakdown")


class EvidenceScore(BaseModel):
    total_evidence_count: int
    supporting_count: int
    conflicting_count: int
    supporting_weight_sum: float
    conflicting_weight_sum: float
    net_evidence_score: float
    agreement_score: float


class SignalExplanation(BaseModel):
    signal_id: str
    domain: SignalDomain
    signal_type: SignalType
    signal_strength: float
    timeframe: str
    source_system: SourceSystem
    why_generated_summary: str
    evidence_score: EvidenceScore
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)
    conflicting_evidence: list[EvidenceItem] = Field(default_factory=list)
    cross_system_agreements: list[CrossSystemAgreement] = Field(default_factory=list)
    cross_system_disagreements: list[CrossSystemDisagreement] = Field(default_factory=list)
    audit_trail: list[str] = Field(default_factory=list)


class EvidenceReport(BaseModel):
    explanations: dict[str, SignalExplanation] = Field(
        default_factory=dict, description="Explanations keyed by signal_id"
    )
    total_evidence_items: int = 0
    system_breakdown: dict[str, int] = Field(default_factory=dict)
    cross_system_agreements_count: int = 0
    cross_system_disagreements_count: int = 0
