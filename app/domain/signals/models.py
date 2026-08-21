from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SignalDomain(str, Enum):
    CAREER = "career"
    FINANCE = "finance"
    RELATIONSHIP = "relationship"
    MARRIAGE = "marriage"
    EDUCATION = "education"
    BUSINESS = "business"
    TRAVEL = "travel"
    RELOCATION = "relocation"
    FAMILY = "family"
    PERSONAL_DEVELOPMENT = "personal_development"


class SignalType(str, Enum):
    OPPORTUNITY = "OPPORTUNITY"
    CHALLENGE = "CHALLENGE"
    TRANSITION = "TRANSITION"
    STABILITY = "STABILITY"
    TRANSFORMATION = "TRANSFORMATION"
    NEUTRAL = "NEUTRAL"


class SourceSystem(str, Enum):
    WESTERN = "WESTERN"
    VEDIC = "VEDIC"
    NUMEROLOGY = "NUMEROLOGY"
    CROSS_SYSTEM_CORRELATED = "CROSS_SYSTEM_CORRELATED"


class FactorPolarity(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class SignalFactor(BaseModel):
    factor_id: str = Field(..., description="Unique deterministic factor ID")
    name: str = Field(..., description="Factor name")
    source_system: SourceSystem = Field(..., description="Origin system of the factor")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Factor weight/intensity")
    polarity: FactorPolarity = Field(default=FactorPolarity.POSITIVE, description="Supporting or conflicting polarity")
    description: str = Field(..., description="Structured calculation or configuration tag")
    timeframe: str = Field(default="natal", description="Applicable timeframe")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Underlying planetary or cycle data")


class AstrologicalSignal(BaseModel):
    signal_id: str = Field(..., description="Deterministic signal identifier")
    domain: SignalDomain = Field(..., description="Life domain for the signal")
    signal_type: SignalType = Field(..., description="Categorical classification of the signal")
    strength: float = Field(..., ge=0.0, le=1.0, description="Computed signal strength from 0.0 to 1.0")
    timeframe: str = Field(..., description="Time window of applicability")
    source_system: SourceSystem = Field(..., description="Origin system or cross-system correlated")
    supporting_factors: list[SignalFactor] = Field(default_factory=list, description="Positively aligned factors")
    conflicting_factors: list[SignalFactor] = Field(default_factory=list, description="Challenging or dissonant factors")
    rule_version: str = Field(default="1.0.0", description="Rule set version")
    correlation_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Cross-system consensus metric (0.0 to 1.0)"
    )


class SignalEngineOutput(BaseModel):
    signals: list[AstrologicalSignal] = Field(default_factory=list, description="Evaluated domain signals")
    domain_scores: dict[str, float] = Field(
        default_factory=dict, description="Aggregate strength scores by domain"
    )
    engine_version: str = Field(default="1.0.0", description="Signal engine version")
    evaluated_systems: list[str] = Field(
        default_factory=list, description="List of systems included in evaluation"
    )
