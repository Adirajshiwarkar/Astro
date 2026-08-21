import pytest

from app.domain.context.builder import ContextBuilder
from app.domain.context.models import ContextPackage


@pytest.fixture
def sample_astrology_data() -> dict:
    return {
        "chart": {
            "birth_date": "1990-01-01",
            "timezone": "UTC",
            "western_ascendant": "Aries",
            "vedic_lagna": "Mesha",
        },
        "western_factors": [
            {"factor_id": "W1", "name": "Sun in Aries"},
            {"factor_id": "W2", "name": "Moon in Taurus"},
            {"factor_id": "W3", "name": "Mars in Gemini"},
            {"factor_id": "W4", "name": "Venus in Cancer"},
            {"factor_id": "W5", "name": "Jupiter in Leo"},
            {"factor_id": "W6", "name": "Saturn in Virgo"},
        ],
        "vedic_factors": [
            {"factor_id": "V1", "name": "Surya in Mesha"},
            {"factor_id": "V2", "name": "Chandra in Vrishabha"},
        ],
        "numerology_factors": [
            {"factor_id": "N1", "name": "Life Path 1"},
        ],
        "signals": [
            {"signal_id": "SIG-CAREER-001", "domain": "career", "strength": 0.9},
            {"signal_id": "SIG-FINANCE-001", "domain": "finance", "strength": 0.8},
            {"signal_id": "SIG-RELATIONSHIP-001", "domain": "relationship", "strength": 0.75},
            {"signal_id": "SIG-HEALTH-001", "domain": "health", "strength": 0.5},
            {"signal_id": "SIG-CAREER-002", "domain": "career", "strength": 0.6},
            {"signal_id": "SIG-CAREER-003", "domain": "career", "strength": 0.4},
        ],
        "evidence": [
            {"evidence_id": "EVID-CAREER-001", "signal_id": "SIG-CAREER-001"},
            {"evidence_id": "EVID-FINANCE-001", "signal_id": "SIG-FINANCE-001"},
            {"evidence_id": "EVID-REL-001", "signal_id": "SIG-RELATIONSHIP-001"},
        ],
        "predictions": [
            {"prediction_id": "PRED-1", "domain": "career"},
            {"prediction_id": "PRED-2", "domain": "finance"},
            {"prediction_id": "PRED-3", "domain": "relationship"},
            {"prediction_id": "PRED-4", "domain": "health"},
        ],
        "timeline": {
            "total_intervals": 2,
            "intervals": [
                {
                    "label": "Month 1",
                    "active_signals": [
                        {"domain": "career", "signal_id": "SIG-CAREER-001"},
                        {"domain": "finance", "signal_id": "SIG-FINANCE-001"},
                        {"domain": "relationship", "signal_id": "SIG-RELATIONSHIP-001"},
                        {"domain": "health", "signal_id": "SIG-HEALTH-001"},
                    ],
                }
            ],
        },
        "scenarios": [
            {"scenario_id": "SCEN-CAREER-1", "domain": "career"},
            {"scenario_id": "SCEN-FINANCE-1", "domain": "finance"},
        ],
        "rag_results": [
            {"content": "Western astrology Midheaven details", "system": "Western"},
            {"content": "Vedic astrology Karma Bhava details", "system": "Vedic"},
        ],
        "relevant_memory": [
            {"memory_id": "MEM-1", "text": "User asked about career goals last week"},
            {"memory_id": "MEM-2", "text": "User is interested in investment"},
            {"memory_id": "MEM-3", "text": "User prefers Western chart"},
            {"memory_id": "MEM-4", "text": "Extra memory item that should be trimmed"},
        ],
        "chart_validation_results": {
            "is_valid": True,
            "errors": [],
            "warnings": ["Warning 1", "Warning 2", "Warning 3"],
        },
    }


def test_context_builder_system_filtering_western(sample_astrology_data: dict) -> None:
    builder = ContextBuilder(
        astrology_engine_version="2.1.0",
        prediction_rules_version="1.2.0",
        knowledge_version="3.0.0",
        prompt_version="4.5.0",
    )

    query = "Tell me about my career using the Placidus system and houses."
    pkg: ContextPackage = builder.build_context(
        query=query,
        chart=sample_astrology_data["chart"],
        western_factors=sample_astrology_data["western_factors"],
        vedic_factors=sample_astrology_data["vedic_factors"],
        numerology_factors=sample_astrology_data["numerology_factors"],
        signals=sample_astrology_data["signals"],
        evidence=sample_astrology_data["evidence"],
        predictions=sample_astrology_data["predictions"],
        timeline=sample_astrology_data["timeline"],
        scenarios=sample_astrology_data["scenarios"],
        rag_results=sample_astrology_data["rag_results"],
        relevant_memory=sample_astrology_data["relevant_memory"],
        chart_validation_results=sample_astrology_data["chart_validation_results"],
    )

    # Verify target routing
    assert pkg.relevant_system == "Western"
    assert "career" in pkg.relevant_domains

    # Verify factor system isolation (Vedic & Numerology should be filtered out)
    assert pkg.western_factors is not None
    assert len(pkg.western_factors) == 6
    assert pkg.vedic_factors is None
    assert pkg.numerology_factors is None

    # Verify chart isolation
    assert pkg.chart is not None
    assert "western_ascendant" in pkg.chart
    assert "vedic_lagna" not in pkg.chart

    # Verify version metadata
    assert pkg.version_metadata.astrology_engine_version == "2.1.0"
    assert pkg.version_metadata.prediction_rules_version == "1.2.0"
    assert pkg.version_metadata.knowledge_version == "3.0.0"
    assert pkg.version_metadata.prompt_version == "4.5.0"


def test_context_builder_domain_filtering_career(sample_astrology_data: dict) -> None:
    builder = ContextBuilder()

    query = "Will I get a promotion soon at work?"
    pkg = builder.build_context(
        query=query,
        chart=sample_astrology_data["chart"],
        western_factors=sample_astrology_data["western_factors"],
        vedic_factors=sample_astrology_data["vedic_factors"],
        numerology_factors=sample_astrology_data["numerology_factors"],
        signals=sample_astrology_data["signals"],
        evidence=sample_astrology_data["evidence"],
        predictions=sample_astrology_data["predictions"],
        timeline=sample_astrology_data["timeline"],
        scenarios=sample_astrology_data["scenarios"],
        rag_results=sample_astrology_data["rag_results"],
        relevant_memory=sample_astrology_data["relevant_memory"],
    )

    assert "career" in pkg.relevant_domains

    # Signals should be filtered to only career domain
    for sig in pkg.signals:
        assert sig["domain"] == "career"

    # Predictions should be filtered to only career domain
    for pred in pkg.predictions:
        assert pred["domain"] == "career"

    # Scenarios should be filtered to only career domain
    for scen in pkg.scenarios:
        assert scen["domain"] == "career"

    # Timeline active signals should be filtered to only career domain
    assert pkg.timeline is not None
    for interval in pkg.timeline["intervals"]:
        for sig in interval["active_signals"]:
            assert sig["domain"] == "career"


def test_context_builder_capping_and_safety(sample_astrology_data: dict) -> None:
    builder = ContextBuilder()

    query = "General reading query."
    pkg = builder.build_context(
        query=query,
        chart=sample_astrology_data["chart"],
        western_factors=sample_astrology_data["western_factors"],
        vedic_factors=sample_astrology_data["vedic_factors"],
        numerology_factors=sample_astrology_data["numerology_factors"],
        signals=sample_astrology_data["signals"],
        evidence=sample_astrology_data["evidence"],
        predictions=sample_astrology_data["predictions"],
        timeline=sample_astrology_data["timeline"],
        scenarios=sample_astrology_data["scenarios"],
        rag_results=sample_astrology_data["rag_results"],
        relevant_memory=sample_astrology_data["relevant_memory"],
        chart_validation_results=sample_astrology_data["chart_validation_results"],
    )

    # Fallback check: since no system is specified, it should fall back to max 5 factors
    assert len(pkg.western_factors) == 5
    assert len(pkg.vedic_factors) == 2  # input has 2, so it stays 2
    assert len(pkg.numerology_factors) == 1

    # Signal capping (max 5)
    assert len(pkg.signals) <= 5

    # Prediction capping (max 3)
    assert len(pkg.predictions) <= 3

    # Scenario capping (max 3)
    assert len(pkg.scenarios) <= 3

    # Memory capping (max 3)
    assert len(pkg.relevant_memory) == 3

    # Validation logs capping (max 2 warnings)
    assert pkg.chart_validation_results is not None
    assert len(pkg.chart_validation_results["warnings"]) == 2
