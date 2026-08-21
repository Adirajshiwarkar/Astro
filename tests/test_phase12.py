import datetime

from app.domain.evidence.models import EvidenceItem
from app.domain.prediction.models import (
    ForecastingWindow,
    ScenarioSet,
    TimeWindowConfig,
)
from app.domain.prediction.scenario import ScenarioEngine
from app.domain.prediction.timeline import TimelineEngine
from app.domain.signals.models import (
    AstrologicalSignal,
    FactorPolarity,
    SignalDomain,
    SignalFactor,
    SignalType,
    SourceSystem,
)


def create_test_signals_and_evidence() -> tuple[list[AstrologicalSignal], list[EvidenceItem]]:
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
        timeframe="2026-08-18 to 2027-02-16",
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

    evidence_items = [
        EvidenceItem(
            evidence_id="EVID-CAREER-001",
            source_system="WESTERN",
            source_factor="Sun in 10th House",
            calculation_reference="house=10",
            rule_reference="RULE_SUN_H10",
            strength=0.90,
            timeframe="natal",
            methodology="Western Astrology",
            polarity=FactorPolarity.POSITIVE,
        ),
        EvidenceItem(
            evidence_id="EVID-FINANCE-001",
            source_system="WESTERN",
            source_factor="Jupiter in 2nd House",
            calculation_reference="house=2",
            rule_reference="RULE_JUPITER_H2",
            strength=0.80,
            timeframe="natal",
            methodology="Western Astrology",
            polarity=FactorPolarity.POSITIVE,
        ),
        EvidenceItem(
            evidence_id="EVID-FINANCE-002",
            source_system="VEDIC",
            source_factor="Shani Retrograde in 2nd Bhava",
            calculation_reference="bhava=2,is_retrograde=True",
            rule_reference="RULE_SHANI_RETRO_B2",
            strength=0.90,
            timeframe="natal",
            methodology="Vedic Astrology",
            polarity=FactorPolarity.NEGATIVE,
        ),
    ]

    return [career_signal, finance_signal], evidence_items


def test_timeline_engine_partitioning_and_association() -> None:
    engine = TimelineEngine()
    signals, _ = create_test_signals_and_evidence()

    start_date = datetime.date(2026, 8, 18)

    # Test 1 Month (should partition into weeks)
    cfg_1m = TimeWindowConfig(window_type=ForecastingWindow.ONE_MONTH, start_date=start_date)
    timeline_1m = engine.generate_timeline(signals, cfg_1m)

    assert timeline_1m.total_intervals == 4
    assert timeline_1m.intervals[0].label == "Week 1"
    assert timeline_1m.intervals[3].label == "Week 4"
    assert timeline_1m.intervals[0].start_date == start_date
    assert timeline_1m.intervals[3].end_date == cfg_1m.get_end_date()

    # Test 6 Months (should partition into months)
    cfg_6m = TimeWindowConfig(window_type=ForecastingWindow.SIX_MONTHS, start_date=start_date)
    timeline_6m = engine.generate_timeline(signals, cfg_6m)

    assert timeline_6m.total_intervals == 6
    assert timeline_6m.intervals[0].label == "Month 1"
    assert timeline_6m.intervals[5].label == "Month 6"
    assert timeline_6m.intervals[0].start_date == start_date
    assert timeline_6m.intervals[5].end_date == cfg_6m.get_end_date()

    # Check signal activity association
    for interval in timeline_6m.intervals:
        active_ids = [s.signal_id for s in interval.active_signals]
        assert "SIG-FINANCE-002" in active_ids
        if interval.label == "Month 6":
            # SIG-CAREER-001 has timeframe "2026" which does not overlap with Month 6 (Jan-Feb 2027)
            assert "SIG-CAREER-001" not in active_ids
            assert len(interval.active_signals) == 1
        else:
            assert "SIG-CAREER-001" in active_ids
            assert len(interval.active_signals) == 2



def test_scenario_engine_generation() -> None:
    engine = ScenarioEngine()
    signals, evidence = create_test_signals_and_evidence()

    # Test Career scenarios (net positive/opportunity)
    scenarios_career: ScenarioSet = engine.generate_scenarios(
        domain=SignalDomain.CAREER,
        signals=signals,
        evidence=evidence,
        timeframe="2026",
    )

    # Assert basic structure
    assert scenarios_career.primary.scenario_id == "SCEN-CAREER-PRIMARY"
    assert scenarios_career.primary.domain == SignalDomain.CAREER
    assert scenarios_career.primary.timeframe == "2026"
    assert scenarios_career.primary.support_score > 0.80
    assert len(scenarios_career.primary.supporting_signals) == 1
    assert scenarios_career.primary.supporting_signals[0].signal_id == "SIG-CAREER-001"
    assert len(scenarios_career.primary.evidence) == 1
    assert scenarios_career.primary.evidence[0].evidence_id == "EVID-CAREER-001"

    assert scenarios_career.alternative.scenario_id == "SCEN-CAREER-ALTERNATIVE"
    assert scenarios_career.alternative.support_score < scenarios_career.primary.support_score

    assert scenarios_career.challenge.scenario_id == "SCEN-CAREER-CHALLENGE"
    assert scenarios_career.conflicting.scenario_id == "SCEN-CAREER-CHALLENGE"  # check conflicting property

    # Test Finance scenarios (dissonant/challenge dominant)
    scenarios_finance = engine.generate_scenarios(
        domain=SignalDomain.FINANCE,
        signals=signals,
        evidence=evidence,
        timeframe="2026-08-18 to 2027-02-16",
    )

    assert scenarios_finance.primary.scenario_id == "SCEN-FINANCE-PRIMARY"
    assert scenarios_finance.primary.domain == SignalDomain.FINANCE
    # Primary scenario for finance is challenge/dissonant because the strongest finance signal is CHALLENGE
    assert scenarios_finance.primary.supporting_signals[0].signal_id == "SIG-FINANCE-002"
    assert len(scenarios_finance.primary.evidence) == 1
    assert scenarios_finance.primary.evidence[0].evidence_id == "EVID-FINANCE-002"  # negative polarity

    assert scenarios_finance.challenge.scenario_id == "SCEN-FINANCE-CHALLENGE"
    assert len(scenarios_finance.challenge.evidence) == 1
    assert scenarios_finance.challenge.evidence[0].evidence_id == "EVID-FINANCE-002"
