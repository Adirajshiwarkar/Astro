from app.domain.astrology.engine import (
    WesternAstrologyEngine,
    angular_distance,
    is_angle_between,
)


def test_is_angle_between() -> None:
    # Standard range [0, 90)
    assert is_angle_between(45.0, 0.0, 90.0) is True
    assert is_angle_between(95.0, 0.0, 90.0) is False
    assert is_angle_between(0.0, 0.0, 90.0) is True

    # Wrapping range [300, 30) (covers 300 to 360, and 0 to 30)
    assert is_angle_between(350.0, 300.0, 30.0) is True
    assert is_angle_between(10.0, 300.0, 30.0) is True
    assert is_angle_between(45.0, 300.0, 30.0) is False


def test_angular_distance() -> None:
    assert angular_distance(10.0, 20.0) == 10.0
    assert angular_distance(350.0, 10.0) == 20.0
    assert angular_distance(180.0, 0.0) == 180.0
    assert angular_distance(270.0, 90.0) == 180.0


def test_natal_chart_calculation() -> None:
    # Setup mock astronomical data for London 2000 chart
    astro_data = {
        "houses": {
            "ascendant": 24.0,
            "mc": 279.0,
            # Simple cusps: each house is 30 degrees starting from 24 degrees
            "cusps": [(24.0 + 30.0 * i) % 360.0 for i in range(12)],
        },
        "planets": {
            "sun": {
                "longitude": 280.0,  # 10 degrees Capricorn (270 to 300)
                "latitude": 0.0,
                "speed": 1.0,
                "is_retrograde": False,
            },
            "moon": {
                "longitude": 100.0,  # 10 degrees Cancer (90 to 120)
                "latitude": 5.0,
                "speed": 12.0,
                "is_retrograde": False,
            },
            "saturn": {
                "longitude": 40.0,  # 10 degrees Taurus (30 to 60)
                "latitude": -2.0,
                "speed": -0.02,
                "is_retrograde": True,
            },
        },
    }

    engine = WesternAstrologyEngine()
    chart = engine.calculate_natal_chart(astro_data)

    # Placements checks
    sun_placement = next(p for p in chart.placements if p.name == "sun")
    assert sun_placement.sign == "Capricorn"
    assert abs(sun_placement.sign_degree - 10.0) < 1e-5
    # Cusp 1 is at 24.0. Cusp 9 is at 24.0 + 8 * 30 = 264.0. Cusp 10 is at 24.0 + 9 * 30 = 294.0.
    # Longitude 280.0 is between 264.0 and 294.0, so it's in House 9.
    assert sun_placement.house == 9

    saturn_placement = next(p for p in chart.placements if p.name == "saturn")
    assert saturn_placement.sign == "Taurus"
    assert saturn_placement.is_retrograde is True

    # Aspects check
    # Sun is at 280.0, Moon is at 100.0. Distance is 180.0 (Opposition).
    opposition_aspect = next(
        a
        for a in chart.aspects
        if a.aspect_type == "opposition" and {a.point1, a.point2} == {"sun", "moon"}
    )
    assert opposition_aspect.orb == 0.0
    assert opposition_aspect.strength == 1.0

    # Derived factors validation
    assert len(chart.derived_factors) > 0
    for factor in chart.derived_factors:
        assert factor.source in ["placement", "aspect", "retrograde"]
        assert factor.calculation != ""
        assert factor.methodology != ""
        assert 0.0 <= factor.strength <= 1.0
        assert factor.timeframe == "natal"
        assert factor.engine_version == "1.0.0"


def test_transit_aspects_calculation() -> None:
    engine = WesternAstrologyEngine()

    # Mock natal chart with Sun at 280.0
    natal_data = {
        "houses": {
            "ascendant": 0.0,
            "mc": 0.0,
            "cusps": [30.0 * i for i in range(12)],
        },
        "planets": {
            "sun": {
                "longitude": 280.0,
                "latitude": 0.0,
                "speed": 1.0,
                "is_retrograde": False,
            }
        },
    }
    natal_chart = engine.calculate_natal_chart(natal_data)

    # Mock transit chart with Mars at 100.2 (Opposing natal Sun with 0.2 orb)
    transit_data = {
        "houses": {
            "ascendant": 0.0,
            "mc": 0.0,
            "cusps": [30.0 * i for i in range(12)],
        },
        "planets": {
            "mars": {
                "longitude": 100.2,
                "latitude": 0.0,
                "speed": 0.5,
                "is_retrograde": False,
            }
        },
    }
    transit_chart = engine.calculate_natal_chart(transit_data)

    transit_factors = engine.calculate_transit_aspects(natal_chart, transit_chart)
    assert len(transit_factors) == 1

    tf = transit_factors[0]
    assert tf.source == "transit_aspect"
    assert "mars" in tf.calculation.lower()
    assert "sun" in tf.calculation.lower()
    assert tf.timeframe == "temporary"
    assert tf.strength > 0.95
