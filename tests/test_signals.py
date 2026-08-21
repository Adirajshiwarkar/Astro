import datetime
import pytest

from app.domain.astrology.models import Aspect, HousePlacement, PlanetPlacement, WesternChart
from app.domain.numerology.engine import NumerologyEngine
from app.domain.signals.engine import SignalEngine
from app.domain.signals.models import (
    AstrologicalSignal,
    FactorPolarity,
    SignalDomain,
    SignalEngineOutput,
    SignalType,
    SourceSystem,
)
from app.domain.vedic.models import (
    BhavaPlacement,
    GrahaPlacement,
    VedicCalculationMetadata,
    VedicChart,
)


def create_mock_western_chart() -> WesternChart:
    placements = [
        PlanetPlacement(
            name="sun",
            longitude=15.0,
            latitude=0.0,
            speed=1.0,
            is_retrograde=False,
            sign="Aries",
            sign_degree=15.0,
            house=10,  # 10th house career!
        ),
        PlanetPlacement(
            name="jupiter",
            longitude=45.0,
            latitude=0.0,
            speed=0.2,
            is_retrograde=False,
            sign="Taurus",
            sign_degree=15.0,
            house=2,  # 2nd house finance!
        ),
        PlanetPlacement(
            name="venus",
            longitude=195.0,
            latitude=0.0,
            speed=1.2,
            is_retrograde=False,
            sign="Libra",
            sign_degree=15.0,
            house=7,  # 7th house relationship!
        ),
        PlanetPlacement(
            name="mercury",
            longitude=75.0,
            latitude=0.0,
            speed=1.5,
            is_retrograde=False,
            sign="Gemini",
            sign_degree=15.0,
            house=9,  # 9th house education & travel!
        ),
        PlanetPlacement(
            name="moon",
            longitude=105.0,
            latitude=0.0,
            speed=13.0,
            is_retrograde=False,
            sign="Cancer",
            sign_degree=15.0,
            house=4,  # 4th house family!
        ),
    ]
    houses = [
        HousePlacement(number=i, cusp=float((i - 1) * 30), sign="Aries", sign_degree=0.0)
        for i in range(1, 13)
    ]
    aspects = [
        Aspect(
            point1="sun",
            point2="jupiter",
            aspect_type="trine",
            angle=120.0,
            exact_angle=120.0,
            orb=0.0,
            strength=1.0,
        ),
        Aspect(
            point1="venus",
            point2="jupiter",
            aspect_type="trine",
            angle=120.0,
            exact_angle=120.0,
            orb=0.0,
            strength=1.0,
        ),
    ]
    return WesternChart(
        placements=placements,
        houses=houses,
        ascendant=15.0,
        mc=285.0,
        aspects=aspects,
        derived_factors=[],
    )


def create_mock_vedic_chart() -> VedicChart:
    grahas = [
        GrahaPlacement(
            vedic_name="Surya",
            western_name="Sun",
            longitude=15.0,
            latitude=0.0,
            speed=1.0,
            is_retrograde=False,
            rashi="Mesha",
            rashi_degree=15.0,
            bhava=10,  # 10th bhava career!
            nakshatra="Bharani",
            nakshatra_pada=1,
        ),
        GrahaPlacement(
            vedic_name="Guru",
            western_name="Jupiter",
            longitude=45.0,
            latitude=0.0,
            speed=0.2,
            is_retrograde=False,
            rashi="Vrishabha",
            rashi_degree=15.0,
            bhava=11,  # 11th bhava gains/finance!
            nakshatra="Rohini",
            nakshatra_pada=2,
        ),
        GrahaPlacement(
            vedic_name="Shukra",
            western_name="Venus",
            longitude=195.0,
            latitude=0.0,
            speed=1.2,
            is_retrograde=False,
            rashi="Tula",
            rashi_degree=15.0,
            bhava=7,  # 7th bhava marriage & relationship!
            nakshatra="Swati",
            nakshatra_pada=3,
        ),
        GrahaPlacement(
            vedic_name="Budha",
            western_name="Mercury",
            longitude=75.0,
            latitude=0.0,
            speed=1.5,
            is_retrograde=False,
            rashi="Mithuna",
            rashi_degree=15.0,
            bhava=4,  # 4th bhava education/vidya!
            nakshatra="Ardra",
            nakshatra_pada=4,
        ),
        GrahaPlacement(
            vedic_name="Rahu",
            western_name="North Node",
            longitude=345.0,
            latitude=0.0,
            speed=-0.05,
            is_retrograde=True,
            rashi="Meena",
            rashi_degree=15.0,
            bhava=12,  # 12th bhava foreign travel/relocation!
            nakshatra="Uttara Bhadrapada",
            nakshatra_pada=1,
        ),
    ]
    bhavas = [
        BhavaPlacement(number=i, cusp=float((i - 1) * 30), rashi="Mesha", rashi_degree=0.0)
        for i in range(1, 13)
    ]
    metadata = VedicCalculationMetadata(
        methodology="Parashari System",
        ayanamsa="lahiri",
        calculation_timestamp="2026-08-18T00:00:00",
        engine_version="1.0.0",
    )
    return VedicChart(
        lagna="Mesha",
        lagna_degree=15.0,
        grahas=grahas,
        bhavas=bhavas,
        aspects=[],
        vimshottari_dasha=[],
        metadata=metadata,
    )


def test_signal_engine_cross_system_correlation() -> None:
    engine = SignalEngine()

    west = create_mock_western_chart()
    vedic = create_mock_vedic_chart()

    num_engine = NumerologyEngine()
    # DOB: 1980-08-08 -> Life Path 8 (Executive/Career/Finance)
    # Target Year 2026: Personal Year 8
    num_profile = num_engine.calculate_profile(
        dob=datetime.date(1980, 8, 8),
        name="John Doe",
        target_year=2026,
    )

    output: SignalEngineOutput = engine.evaluate_signals(
        western_chart=west,
        vedic_chart=vedic,
        numerology_profile=num_profile,
        timeframe="2026",
    )

    assert len(output.signals) == 10
    assert len(output.evaluated_systems) == 3
    assert set(output.evaluated_systems) == {"WESTERN", "VEDIC", "NUMEROLOGY"}

    signals_by_domain = {s.domain: s for s in output.signals}

    # 1. Career signal: Western (Sun H10, Sun-Jupiter trine) + Vedic (Surya B10) + Numerology (LP 8, PY 8)
    career_sig = signals_by_domain[SignalDomain.CAREER]
    assert career_sig.domain == SignalDomain.CAREER
    assert career_sig.source_system == SourceSystem.CROSS_SYSTEM_CORRELATED
    assert career_sig.correlation_score == 1.0  # All 3 systems concurred
    assert career_sig.strength > 0.80
    assert career_sig.signal_type in (SignalType.OPPORTUNITY, SignalType.TRANSITION)
    assert len(career_sig.supporting_factors) >= 4

    # 2. Finance signal: Western (Jupiter H2, Venus-Jupiter trine) + Vedic (Guru B11) + Numerology (LP 8, PY 8)
    fin_sig = signals_by_domain[SignalDomain.FINANCE]
    assert fin_sig.source_system == SourceSystem.CROSS_SYSTEM_CORRELATED
    assert fin_sig.strength > 0.80
    assert fin_sig.correlation_score == 1.0

    # 3. Relationship & Marriage signals
    rel_sig = signals_by_domain[SignalDomain.RELATIONSHIP]
    assert rel_sig.source_system == SourceSystem.CROSS_SYSTEM_CORRELATED
    assert rel_sig.strength > 0.70

    mar_sig = signals_by_domain[SignalDomain.MARRIAGE]
    assert mar_sig.strength > 0.60

    # 4. Education, Business, Travel, Relocation, Family, Personal Development
    for dom in [
        SignalDomain.EDUCATION,
        SignalDomain.BUSINESS,
        SignalDomain.TRAVEL,
        SignalDomain.RELOCATION,
        SignalDomain.FAMILY,
        SignalDomain.PERSONAL_DEVELOPMENT,
    ]:
        sig = signals_by_domain[dom]
        assert sig.domain == dom
        assert 0.0 <= sig.strength <= 1.0
        assert sig.rule_version == "1.0.0"


def test_signal_engine_single_system_evaluation() -> None:
    engine = SignalEngine()
    west = create_mock_western_chart()

    output = engine.evaluate_signals(western_chart=west)
    assert output.evaluated_systems == ["WESTERN"]

    career_sig = next(s for s in output.signals if s.domain == SignalDomain.CAREER)
    assert career_sig.source_system == SourceSystem.WESTERN
    assert career_sig.correlation_score == 1.0


def test_supporting_vs_conflicting_factors() -> None:
    engine = SignalEngine()

    # Create Western chart with conflicting placement (Saturn retrograde in 2nd house)
    placements = [
        PlanetPlacement(
            name="saturn",
            longitude=45.0,
            latitude=0.0,
            speed=-0.05,
            is_retrograde=True,  # Retrograde Saturn in 2nd house -> challenging finance factor
            sign="Taurus",
            sign_degree=15.0,
            house=2,
        )
    ]
    houses = [
        HousePlacement(number=i, cusp=float((i - 1) * 30), sign="Aries", sign_degree=0.0)
        for i in range(1, 13)
    ]
    w_chart = WesternChart(
        placements=placements,
        houses=houses,
        ascendant=0.0,
        mc=270.0,
        aspects=[],
        derived_factors=[],
    )

    output = engine.evaluate_signals(western_chart=w_chart)
    fin_sig = next(s for s in output.signals if s.domain == SignalDomain.FINANCE)

    assert len(fin_sig.conflicting_factors) >= 1
    assert fin_sig.conflicting_factors[0].polarity == FactorPolarity.NEGATIVE


def test_signal_engine_strict_schema_and_zero_prose() -> None:
    engine = SignalEngine()
    west = create_mock_western_chart()
    output = engine.evaluate_signals(western_chart=west)

    for sig in output.signals:
        assert isinstance(sig, AstrologicalSignal)
        assert sig.signal_id.startswith("SIG-")
        assert sig.rule_version == "1.0.0"
        assert 0.0 <= sig.strength <= 1.0
        assert 0.0 <= sig.correlation_score <= 1.0
        # Verify factor attributes
        for f in sig.supporting_factors + sig.conflicting_factors:
            assert f.factor_id != ""
            assert f.weight >= 0.0
            assert f.description != ""
