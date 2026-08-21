import datetime
import pytest

from app.domain.evidence.engine import EvidenceEngine
from app.domain.evidence.models import EvidenceItem
from app.domain.prediction.engine import PredictionEngine
from app.domain.prediction.models import (
    CandidateEvent,
    ForecastingWindow,
    PredictionRequest,
    PredictionResponse,
    TimeWindowConfig,
    UncertaintyLevel,
)
from app.domain.signals.models import (
    AstrologicalSignal,
    FactorPolarity,
    SignalDomain,
    SignalFactor,
    SignalType,
    SourceSystem,
)


def create_sample_signals_and_evidence() -> tuple[list[AstrologicalSignal], list[EvidenceItem]]:
    career_signal = AstrologicalSignal(
        signal_id="SIG-CAREER-001",
        domain=SignalDomain.CAREER,
        signal_type=SignalType.OPPORTUNITY,
        strength=0.90,
        timeframe="2026",
        source_system=SourceSystem.CROSS_SYSTEM_CORRELATED,
        supporting_factors=[
            SignalFactor(
                factor_id="WEST-PL-SUN-H10",
                name="Western Sun in 10th House",
                source_system=SourceSystem.WESTERN,
                weight=0.90,
                polarity=FactorPolarity.POSITIVE,
                description="Sun in 10th house",
            )
        ],
        conflicting_factors=[],
        rule_version="1.0.0",
        correlation_score=1.0,
    )

    finance_signal = AstrologicalSignal(
        signal_id="SIG-FINANCE-002",
        domain=SignalDomain.FINANCE,
        signal_type=SignalType.CHALLENGE,
        strength=0.35,
        timeframe="2026",
        source_system=SourceSystem.CROSS_SYSTEM_CORRELATED,
        supporting_factors=[
            SignalFactor(
                factor_id="WEST-PL-JUP-H2",
                name="Western Jupiter in 2nd House",
                source_system=SourceSystem.WESTERN,
                weight=0.80,
                polarity=FactorPolarity.POSITIVE,
                description="Jupiter in 2nd house",
            )
        ],
        conflicting_factors=[
            SignalFactor(
                factor_id="VEDIC-SAT-RETRO-B2",
                name="Vedic Shani Retrograde in 2nd Bhava",
                source_system=SourceSystem.VEDIC,
                weight=0.90,
                polarity=FactorPolarity.NEGATIVE,
                description="Retrograde Shani in 2nd bhava",
            )
        ],
        rule_version="1.0.0",
        correlation_score=0.5,
    )

    ev_engine = EvidenceEngine()
    exp_career = ev_engine.generate_evidence_for_signal(career_signal)
    exp_finance = ev_engine.generate_evidence_for_signal(finance_signal)

    all_evidence = (
        exp_career.supporting_evidence
        + exp_finance.supporting_evidence
        + exp_finance.conflicting_evidence
    )

    return [career_signal, finance_signal], all_evidence


def test_forecasting_windows() -> None:
    engine = PredictionEngine()
    signals, evidence = create_sample_signals_and_evidence()

    start_date = datetime.date(2026, 8, 18)

    # Test 1 Month
    cfg_1m = TimeWindowConfig(window_type=ForecastingWindow.ONE_MONTH, start_date=start_date)
    assert cfg_1m.get_end_date() == datetime.date(2026, 9, 17)

    # Test 3 Months
    cfg_3m = TimeWindowConfig(window_type=ForecastingWindow.THREE_MONTHS, start_date=start_date)
    assert cfg_3m.get_end_date() == datetime.date(2026, 11, 17)

    # Test 6 Months
    cfg_6m = TimeWindowConfig(window_type=ForecastingWindow.SIX_MONTHS, start_date=start_date)
    assert cfg_6m.get_end_date() == datetime.date(2027, 2, 16)

    # Test 10 Months
    cfg_10m = TimeWindowConfig(window_type=ForecastingWindow.TEN_MONTHS, start_date=start_date)
    assert cfg_10m.get_end_date() == datetime.date(2027, 6, 18)

    # Test 12 Months
    cfg_12m = TimeWindowConfig(window_type=ForecastingWindow.TWELVE_MONTHS, start_date=start_date)
    assert cfg_12m.get_end_date() == datetime.date(2027, 8, 18)

    # Test Custom Range
    cfg_custom = TimeWindowConfig(
        window_type=ForecastingWindow.CUSTOM,
        start_date=start_date,
        end_date=datetime.date(2026, 12, 31),
    )
    assert cfg_custom.get_end_date() == datetime.date(2026, 12, 31)

    req = PredictionRequest(
        domain=SignalDomain.CAREER,
        signals=signals,
        evidence=evidence,
        time_window=cfg_6m,
    )
    res = engine.predict(req)
    assert "2026-08-18 to 2027-02-16" in res.timeframe
    assert "6_months" in res.timeframe


def test_candidate_events_traceability() -> None:
    engine = PredictionEngine()
    signals, evidence = create_sample_signals_and_evidence()

    req = PredictionRequest(
        domain=SignalDomain.CAREER,
        signals=signals,
        evidence=evidence,
        time_window=TimeWindowConfig(window_type=ForecastingWindow.THREE_MONTHS),
    )
    res: PredictionResponse = engine.predict(req)

    assert len(res.candidate_events) == 1
    event: CandidateEvent = res.candidate_events[0]
    assert event.domain == SignalDomain.CAREER
    assert event.event_type == "OPPORTUNITY"
    assert "Professional" in event.title
    assert event.support_score > 0.85
    assert len(event.supporting_evidence) >= 1
    assert event.traceable_signal_ids == ["SIG-CAREER-001"]


def test_support_score_and_uncertainty_definition() -> None:
    engine = PredictionEngine()
    signals, evidence = create_sample_signals_and_evidence()

    req = PredictionRequest(
        domain=SignalDomain.CAREER,
        signals=signals,
        evidence=evidence,
        time_window=TimeWindowConfig(window_type=ForecastingWindow.SIX_MONTHS),
    )
    res = engine.predict(req)

    # Check uncertainty metadata
    assert res.uncertainty_metadata.uncertainty_level in (
        UncertaintyLevel.LOW,
        UncertaintyLevel.MODERATE,
    )
    assert "not constitute empirical or physical certitudes" in res.uncertainty_metadata.certainty_disclaimer
    assert "alignment index, not an empirical probability" in res.uncertainty_metadata.confidence_score_definition


def test_conflicting_evidence_in_prediction() -> None:
    engine = PredictionEngine()
    signals, evidence = create_sample_signals_and_evidence()

    req = PredictionRequest(
        domain=SignalDomain.FINANCE,
        signals=signals,
        evidence=evidence,
        time_window=TimeWindowConfig(window_type=ForecastingWindow.SIX_MONTHS),
    )
    res = engine.predict(req)

    assert len(res.candidate_events) == 1
    fin_event = res.candidate_events[0]
    assert fin_event.domain == SignalDomain.FINANCE
    assert len(fin_event.conflicting_evidence) >= 1
    # Conflicting evidence elevates uncertainty
    assert fin_event.uncertainty_metadata.uncertainty_level in (
        UncertaintyLevel.MODERATE,
        UncertaintyLevel.HIGH,
    )
    assert any("conflicting indicators" in f for f in fin_event.uncertainty_metadata.uncertainty_factors)


def test_all_domains_prediction() -> None:
    engine = PredictionEngine()
    signals, evidence = create_sample_signals_and_evidence()

    req = PredictionRequest(
        domain=None,  # All domains
        signals=signals,
        evidence=evidence,
        time_window=TimeWindowConfig(window_type=ForecastingWindow.TWELVE_MONTHS),
    )
    res = engine.predict(req)

    assert len(res.candidate_events) >= 2
    assert 0.0 <= res.overall_support_score <= 1.0
    assert res.engine_version == "1.0.0"
