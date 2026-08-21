import datetime
import pytest

from app.domain.astrology.models import Aspect, HousePlacement, PlanetPlacement, WesternChart
from app.domain.evidence.engine import EvidenceEngine
from app.domain.evidence.models import (
    CrossSystemAgreement,
    CrossSystemDisagreement,
    EvidenceItem,
    EvidenceReport,
    SignalExplanation,
)
from app.domain.numerology.engine import NumerologyEngine
from app.domain.signals.engine import SignalEngine
from app.domain.signals.models import (
    AstrologicalSignal,
    FactorPolarity,
    SignalDomain,
    SignalFactor,
    SignalType,
    SourceSystem,
)
from app.domain.vedic.models import (
    BhavaPlacement,
    GrahaPlacement,
    VedicCalculationMetadata,
    VedicChart,
)


def create_sample_career_signal() -> AstrologicalSignal:
    return AstrologicalSignal(
        signal_id="SIG-CAREER-001",
        domain=SignalDomain.CAREER,
        signal_type=SignalType.OPPORTUNITY,
        strength=0.92,
        timeframe="2026",
        source_system=SourceSystem.CROSS_SYSTEM_CORRELATED,
        supporting_factors=[
            SignalFactor(
                factor_id="WEST-PL-SUN-H10",
                name="Western Sun in 10th House",
                source_system=SourceSystem.WESTERN,
                weight=0.90,
                polarity=FactorPolarity.POSITIVE,
                description="Sun situated in 10th house of career",
                timeframe="natal",
                metadata={"planet": "sun", "house": 10},
            ),
            SignalFactor(
                factor_id="VEDIC-GRAHA-SURYA-B10",
                name="Vedic Surya in 10th Bhava",
                source_system=SourceSystem.VEDIC,
                weight=0.92,
                polarity=FactorPolarity.POSITIVE,
                description="Surya in 10th Bhava (Karma Sthana)",
                timeframe="natal",
                metadata={"graha": "Surya", "bhava": 10},
            ),
            SignalFactor(
                factor_id="NUM-PY-8-CAR",
                name="Personal Year 8 (Executive Expansion)",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.90,
                polarity=FactorPolarity.POSITIVE,
                description="Personal Year 8 creates strong professional acceleration",
                timeframe="Personal Year 8",
            ),
        ],
        conflicting_factors=[],
        rule_version="1.0.0",
        correlation_score=1.0,
    )


def test_positive_evidence() -> None:
    engine = EvidenceEngine()
    signal = create_sample_career_signal()

    explanation: SignalExplanation = engine.generate_evidence_for_signal(signal)

    assert explanation.signal_id == "SIG-CAREER-001"
    assert explanation.domain == SignalDomain.CAREER
    assert len(explanation.supporting_evidence) == 3
    assert len(explanation.conflicting_evidence) == 0

    # Verify field completeness on every evidence item
    for e in explanation.supporting_evidence:
        assert isinstance(e, EvidenceItem)
        assert e.evidence_id.startswith("EVID-CAREER-")
        assert e.source_system in ("WESTERN", "VEDIC", "NUMEROLOGY")
        assert e.source_factor != ""
        assert e.calculation_reference != ""
        assert e.rule_reference.startswith("RULE_")
        assert 0.0 <= e.strength <= 1.0
        assert e.timeframe != ""
        assert e.methodology != ""
        assert e.engine_version == "1.0.0"
        assert e.polarity == FactorPolarity.POSITIVE

    assert explanation.evidence_score.supporting_count == 3
    assert explanation.evidence_score.conflicting_count == 0
    assert explanation.evidence_score.net_evidence_score > 0.85


def test_conflicting_evidence() -> None:
    engine = EvidenceEngine()

    conflicting_signal = AstrologicalSignal(
        signal_id="SIG-FINANCE-002",
        domain=SignalDomain.FINANCE,
        signal_type=SignalType.CHALLENGE,
        strength=0.35,
        timeframe="2026",
        source_system=SourceSystem.CROSS_SYSTEM_CORRELATED,
        supporting_factors=[
            SignalFactor(
                factor_id="WEST-PL-JUPITER-H2",
                name="Western Jupiter in 2nd House",
                source_system=SourceSystem.WESTERN,
                weight=0.85,
                polarity=FactorPolarity.POSITIVE,
                description="Jupiter in 2nd house of wealth",
            ),
        ],
        conflicting_factors=[
            SignalFactor(
                factor_id="VEDIC-SATURN-RETRO-B2",
                name="Vedic Shani Retrograde in 2nd Bhava",
                source_system=SourceSystem.VEDIC,
                weight=0.90,
                polarity=FactorPolarity.NEGATIVE,
                description="Retrograde Shani in Dhana Bhava creating delays",
            ),
        ],
        rule_version="1.0.0",
        correlation_score=0.5,
    )

    explanation = engine.generate_evidence_for_signal(conflicting_signal)

    assert len(explanation.supporting_evidence) == 1
    assert len(explanation.conflicting_evidence) == 1
    assert explanation.evidence_score.conflicting_count == 1
    assert explanation.evidence_score.net_evidence_score < 0.60

    # Verify cross-system disagreement detection
    assert len(explanation.cross_system_disagreements) == 1
    disagreement = explanation.cross_system_disagreements[0]
    assert "WESTERN" in disagreement.supporting_systems
    assert "VEDIC" in disagreement.conflicting_systems
    assert disagreement.divergence_level > 0.0


def test_multiple_source_evidence() -> None:
    engine = EvidenceEngine()
    signal = create_sample_career_signal()

    explanation = engine.generate_evidence_for_signal(signal)

    assert len(explanation.cross_system_agreements) == 1
    agreement: CrossSystemAgreement = explanation.cross_system_agreements[0]
    assert agreement.domain == SignalDomain.CAREER
    assert set(agreement.concurring_systems) == {"WESTERN", "VEDIC", "NUMEROLOGY"}
    assert agreement.consensus_strength > 0.80
    assert len(agreement.evidence_items) == 3


def test_missing_evidence() -> None:
    engine = EvidenceEngine()

    baseline_signal = AstrologicalSignal(
        signal_id="SIG-FAMILY-BASELINE",
        domain=SignalDomain.FAMILY,
        signal_type=SignalType.NEUTRAL,
        strength=0.50,
        timeframe="natal",
        source_system=SourceSystem.WESTERN,
        supporting_factors=[],
        conflicting_factors=[],
        rule_version="1.0.0",
        correlation_score=1.0,
    )

    explanation = engine.generate_evidence_for_signal(baseline_signal)

    assert explanation.signal_id == "SIG-FAMILY-BASELINE"
    assert len(explanation.supporting_evidence) == 0
    assert len(explanation.conflicting_evidence) == 0
    assert explanation.evidence_score.total_evidence_count == 0
    assert "baseline neutral" in explanation.why_generated_summary.lower()


def test_deterministic_why_query_and_report() -> None:
    engine = EvidenceEngine()
    signal = create_sample_career_signal()

    report: EvidenceReport = engine.generate_evidence_report([signal])

    assert report.total_evidence_items == 3
    assert report.system_breakdown["WESTERN"] == 1
    assert report.system_breakdown["VEDIC"] == 1
    assert report.system_breakdown["NUMEROLOGY"] == 1
    assert report.cross_system_agreements_count == 1

    # Query "Why was this signal generated?"
    explanation = engine.explain_signal("SIG-CAREER-001", report)
    assert explanation.signal_id == "SIG-CAREER-001"
    assert len(explanation.audit_trail) >= 4
    assert any("Initiated evidence trace" in step for step in explanation.audit_trail)
    assert any("Score Derivation" in step for step in explanation.audit_trail)
    assert any("Final Explanation" in step for step in explanation.audit_trail)

    # Negative lookup
    with pytest.raises(KeyError):
        engine.explain_signal("NON-EXISTENT-SIGNAL", report)
