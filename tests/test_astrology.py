import datetime

import pytest

from app.services.astrology.provider import SwissEphemerisProvider
from app.services.astrology.timezone import local_to_utc


def test_timezone_conversion_and_dst() -> None:
    # Test London Winter (GMT, no DST)
    utc_dt, is_dst = local_to_utc(
        datetime.date(2023, 12, 25), datetime.time(12, 0, 0), "Europe/London"
    )
    assert utc_dt == datetime.datetime(2023, 12, 25, 12, 0, 0, tzinfo=datetime.UTC)
    assert is_dst is False

    # Test London Summer (BST, +1h DST active)
    utc_dt, is_dst = local_to_utc(
        datetime.date(2023, 7, 15), datetime.time(12, 0, 0), "Europe/London"
    )
    # 12:00:00 BST = 11:00:00 UTC
    assert utc_dt == datetime.datetime(2023, 7, 15, 11, 0, 0, tzinfo=datetime.UTC)
    assert is_dst is True

    # Test New York Summer (EDT, -4h UTC)
    utc_dt, is_dst = local_to_utc(
        datetime.date(2023, 7, 15), datetime.time(12, 0, 0), "America/New_York"
    )
    # 12:00:00 EDT = 16:00:00 UTC
    assert utc_dt == datetime.datetime(2023, 7, 15, 16, 0, 0, tzinfo=datetime.UTC)
    assert is_dst is True


def test_timezone_conversion_invalid() -> None:
    with pytest.raises(ValueError):
        local_to_utc(
            datetime.date(2023, 12, 25),
            datetime.time(12, 0, 0),
            "Invalid/Timezone_Name",
        )


def test_boundary_times() -> None:
    provider = SwissEphemerisProvider()

    # Far past (year 1800)
    utc_dt = datetime.datetime(1800, 1, 1, 0, 0, tzinfo=datetime.UTC)
    res = provider.calculate_chart(utc_dt, 0.0, 0.0)
    assert res["planets"]["sun"]["longitude"] is not None

    # Far future (year 2100)
    utc_dt = datetime.datetime(2100, 12, 31, 23, 59, 59, tzinfo=datetime.UTC)
    res = provider.calculate_chart(utc_dt, 0.0, 0.0)
    assert res["planets"]["sun"]["longitude"] is not None


def test_retrograde_state() -> None:
    provider = SwissEphemerisProvider()

    # On Jan 1, 2000, Saturn is retrograde
    utc_dt = datetime.datetime(2000, 1, 1, 12, 0, tzinfo=datetime.UTC)
    res = provider.calculate_chart(utc_dt, 51.5074, -0.1278)
    assert res["planets"]["saturn"]["speed"] < 0
    assert res["planets"]["saturn"]["is_retrograde"] is True

    # Sun is never retrograde
    assert res["planets"]["sun"]["speed"] > 0
    assert res["planets"]["sun"]["is_retrograde"] is False


def test_houses_and_ascendant() -> None:
    provider = SwissEphemerisProvider()
    utc_dt = datetime.datetime(2000, 1, 1, 12, 0, tzinfo=datetime.UTC)

    # Test Placidus
    res_placidus = provider.calculate_chart(
        utc_dt, 51.5074, -0.1278, house_system="placidus"
    )
    assert len(res_placidus["houses"]["cusps"]) == 12
    # Ascendant is cusp 1 in Placidus
    assert (
        abs(res_placidus["houses"]["ascendant"] - res_placidus["houses"]["cusps"][0])
        < 1e-5
    )

    # Test Koch
    res_koch = provider.calculate_chart(utc_dt, 51.5074, -0.1278, house_system="koch")
    assert len(res_koch["houses"]["cusps"]) == 12

    # Test Whole Sign
    res_whole = provider.calculate_chart(
        utc_dt, 51.5074, -0.1278, house_system="whole_sign"
    )
    # In whole sign, houses start at 0, 30, 60, etc., offset by the sign boundary of the Ascendant sign
    for cusp in res_whole["houses"]["cusps"]:
        assert cusp % 30.0 == 0.0


def test_golden_chart_london_2000() -> None:
    provider = SwissEphemerisProvider()

    # 2000-01-01 at 12:00:00 UTC in London
    utc_dt = datetime.datetime(2000, 1, 1, 12, 0, tzinfo=datetime.UTC)
    res = provider.calculate_chart(utc_dt, 51.5074, -0.1278)

    # Golden planetary positions (tropical)
    assert abs(res["planets"]["sun"]["longitude"] - 280.3689) < 0.01
    assert abs(res["planets"]["moon"]["longitude"] - 223.3237) < 0.01
    assert abs(res["planets"]["jupiter"]["longitude"] - 25.2530) < 0.01
    assert abs(res["planets"]["saturn"]["longitude"] - 40.3956) < 0.01

    # Golden houses (tropical, placidus)
    assert abs(res["houses"]["ascendant"] - 24.0145) < 0.01
    assert abs(res["houses"]["mc"] - 279.4932) < 0.01
