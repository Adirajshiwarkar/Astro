import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.domain.canonical.models import CanonicalChartRepresentation
from app.domain.evidence.models import EvidenceItem, EvidenceReport
from app.domain.signals.models import AstrologicalSignal, SignalDomain


class ForecastingWindow(StrEnum):
    ONE_MONTH = "1_month"
    THREE_MONTHS = "3_months"
    SIX_MONTHS = "6_months"
    TEN_MONTHS = "10_months"
    TWELVE_MONTHS = "12_months"
    CUSTOM = "custom"


class TimeWindowConfig(BaseModel):
    window_type: ForecastingWindow = Field(
        default=ForecastingWindow.SIX_MONTHS, description="Standard or custom forecasting window"
    )
    start_date: datetime.date = Field(
        default_factory=datetime.date.today, description="Start date of forecasting period"
    )
    end_date: datetime.date | None = Field(
        default=None, description="Explicit end date if custom range"
    )
    custom_days: int | None = Field(
        default=None, description="Number of days if custom window without explicit end date"
    )

    def get_end_date(self) -> datetime.date:
        if self.end_date is not None:
            return self.end_date
        if self.window_type == ForecastingWindow.ONE_MONTH:
            return self.start_date + datetime.timedelta(days=30)
        elif self.window_type == ForecastingWindow.THREE_MONTHS:
            return self.start_date + datetime.timedelta(days=91)
        elif self.window_type == ForecastingWindow.SIX_MONTHS:
            return self.start_date + datetime.timedelta(days=182)
        elif self.window_type == ForecastingWindow.TEN_MONTHS:
            return self.start_date + datetime.timedelta(days=304)
        elif self.window_type == ForecastingWindow.TWELVE_MONTHS:
            return self.start_date + datetime.timedelta(days=365)
        elif self.window_type == ForecastingWindow.CUSTOM and self.custom_days:
            return self.start_date + datetime.timedelta(days=self.custom_days)
        return self.start_date + datetime.timedelta(days=182)


class UncertaintyLevel(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    INDETERMINATE = "INDETERMINATE"


class UncertaintyMetadata(BaseModel):
    uncertainty_level: UncertaintyLevel = Field(
        ..., description="Categorical uncertainty rating based on factor consistency"
    )
    uncertainty_factors: list[str] = Field(
        default_factory=list, description="Factors contributing to uncertainty"
    )
    certainty_disclaimer: str = Field(
        default=(
            "Astrological forecasts represent symbolic and cyclical resonance patterns derived "
            "deterministically under classical rules. They do not constitute empirical or physical certitudes."
        ),
        description="Non-certainty and non-deterministic advisory disclaimer",
    )
    confidence_score_definition: str = Field(
        default=(
            "SupportScore is the normalized algebraic ratio of supporting evidence weights minus conflicting "
            "evidence penalties in [0.0, 1.0]. It is an alignment index, not an empirical probability."
        ),
        description="Explicit mathematical definition of confidence/support score",
    )


class CandidateEvent(BaseModel):
    event_id: str = Field(..., description="Deterministic unique event ID")
    title: str = Field(..., description="Structured event classification title")
    event_type: str = Field(..., description="Event type (OPPORTUNITY, CHALLENGE, TRANSITION, STABILITY, TRANSFORMATION)")
    domain: SignalDomain = Field(..., description="Domain of the candidate event")
    timeframe: str = Field(..., description="Forecasting time window description")
    support_score: float = Field(..., ge=0.0, le=1.0, description="Normalized support score")
    supporting_evidence: list[EvidenceItem] = Field(
        default_factory=list, description="Direct supporting evidence items"
    )
    conflicting_evidence: list[EvidenceItem] = Field(
        default_factory=list, description="Direct conflicting evidence items"
    )
    uncertainty_metadata: UncertaintyMetadata = Field(..., description="Uncertainty profile")
    traceable_signal_ids: list[str] = Field(
        default_factory=list, description="Originating signal IDs"
    )


class PredictionRequest(BaseModel):
    user_query: str | None = Field(default=None, description="Optional natural language query (for domain routing only)")
    domain: SignalDomain | None = Field(default=None, description="Target domain filter if specific")
    normalized_chart: CanonicalChartRepresentation | None = Field(
        default=None, description="Canonical normalized chart representation"
    )
    signals: list[AstrologicalSignal] = Field(
        default_factory=list, description="Evaluated domain signals from SignalEngine"
    )
    evidence: EvidenceReport | list[EvidenceItem] | None = Field(
        default=None, description="Evidence report or evidence items from EvidenceEngine"
    )
    time_window: TimeWindowConfig = Field(
        default_factory=TimeWindowConfig, description="Forecasting time window configuration"
    )


class PredictionResponse(BaseModel):
    candidate_events: list[CandidateEvent] = Field(
        default_factory=list, description="Forecasted candidate events"
    )
    domain: SignalDomain | None = Field(default=None, description="Evaluated domain filter")
    timeframe: str = Field(..., description="Forecasting window description")
    overall_support_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall support score across evaluated events"
    )
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)
    conflicting_evidence: list[EvidenceItem] = Field(default_factory=list)
    uncertainty_metadata: UncertaintyMetadata = Field(..., description="Aggregated uncertainty profile")
    engine_version: str = Field(default="1.0.0", description="Prediction engine version")


class TimelineInterval(BaseModel):
    start_date: datetime.date = Field(..., description="Start date of the interval")
    end_date: datetime.date = Field(..., description="End date of the interval")
    label: str = Field(..., description="Label for the interval, e.g., 'Week 1', 'Month 1'")
    active_signals: list[AstrologicalSignal] = Field(
        default_factory=list, description="Active astrological signals during this interval"
    )


class TimelineForecast(BaseModel):
    intervals: list[TimelineInterval] = Field(default_factory=list, description="Partitioned intervals")
    total_intervals: int = Field(..., description="Total number of intervals")


class Scenario(BaseModel):
    scenario_id: str = Field(..., description="Unique deterministic identifier for the scenario")
    domain: SignalDomain = Field(..., description="The astrological domain of this scenario")
    timeframe: str = Field(..., description="Time window of applicability")
    support_score: float = Field(..., ge=0.0, le=1.0, description="Normalized support score")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Direct supporting evidence items")
    supporting_signals: list[AstrologicalSignal] = Field(default_factory=list, description="Signals supporting this scenario")
    conflicting_signals: list[AstrologicalSignal] = Field(default_factory=list, description="Signals conflicting with this scenario")
    uncertainty: UncertaintyMetadata = Field(..., description="Uncertainty profile of this scenario")


class ScenarioSet(BaseModel):
    primary: Scenario = Field(..., description="The highly probable, primary path")
    alternative: Scenario = Field(..., description="The secondary, alternative path")
    challenge: Scenario = Field(..., description="The challenge/conflicting path")

    @property
    def conflicting(self) -> Scenario:
        return self.challenge

