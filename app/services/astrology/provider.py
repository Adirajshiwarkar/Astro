import abc
import datetime
from typing import Any

import swisseph


class AstrologyCalculationProvider(abc.ABC):
    @abc.abstractmethod
    def calculate_chart(
        self,
        utc_dt: datetime.datetime,
        latitude: float,
        longitude: float,
        zodiac_type: str = "tropical",
        ayanamsa: str = "lahiri",
        house_system: str = "placidus",
    ) -> dict[str, Any]:
        """Calculate planetary positions and house cusps for a given UTC datetime and location.

        Returns:
            dict containing:
                - planets: dict mapping planet names to their longitude, latitude, speed, is_retrograde
                - houses: dict containing ascendant, mc, and cusps list
                - calculation_metadata: dict containing parameters used for calculation
        """
        pass


class SwissEphemerisProvider(AstrologyCalculationProvider):
    def __init__(self, ephe_path: str | None = None) -> None:
        if ephe_path:
            swisseph.set_ephe_path(ephe_path)

        # Mapping for house systems
        self._house_systems = {
            "placidus": b"P",
            "koch": b"K",
            "equal": b"E",
            "whole_sign": b"W",
            "campanus": b"C",
            "regiomontanus": b"R",
        }

        # Mapping for ayanamsas
        self._ayanamsas = {
            "lahiri": swisseph.SIDM_LAHIRI,
            "fagan_bradley": swisseph.SIDM_FAGAN_BRADLEY,
            "raman": swisseph.SIDM_RAMAN,
            "krishnamurti": swisseph.SIDM_KRISHNAMURTI,
        }

        # Planetary/Point IDs in swisseph
        self._bodies = {
            "sun": swisseph.SUN,
            "moon": swisseph.MOON,
            "mercury": swisseph.MERCURY,
            "venus": swisseph.VENUS,
            "mars": swisseph.MARS,
            "jupiter": swisseph.JUPITER,
            "saturn": swisseph.SATURN,
            "uranus": swisseph.URANUS,
            "neptune": swisseph.NEPTUNE,
            "pluto": swisseph.PLUTO,
            "north_node": swisseph.TRUE_NODE,  # True Lunar Node
        }

    def _get_julian_day(self, utc_dt: datetime.datetime) -> float:
        hour_decimal = (
            utc_dt.hour
            + utc_dt.minute / 60.0
            + utc_dt.second / 3600.0
            + utc_dt.microsecond / 3600000000.0
        )
        return float(
            swisseph.julday(utc_dt.year, utc_dt.month, utc_dt.day, hour_decimal)
        )

    def calculate_chart(
        self,
        utc_dt: datetime.datetime,
        latitude: float,
        longitude: float,
        zodiac_type: str = "tropical",
        ayanamsa: str = "lahiri",
        house_system: str = "placidus",
    ) -> dict[str, Any]:
        # 1. Convert UTC datetime to Julian Day (UT)
        jd_ut = self._get_julian_day(utc_dt)

        # 2. Configure Zodiac Type and Ayanamsa
        flags = swisseph.FLG_SPEED
        ayanamsa_id = None

        if zodiac_type.lower() == "sidereal":
            flags |= swisseph.FLG_SIDEREAL
            ayan_name = ayanamsa.lower()
            if ayan_name not in self._ayanamsas:
                raise ValueError(
                    f"Unsupported ayanamsa: {ayanamsa}. Supported: {list(self._ayanamsas.keys())}"
                )
            ayanamsa_id = self._ayanamsas[ayan_name]
            swisseph.set_sid_mode(ayanamsa_id)

        # 3. Calculate Planetary Positions
        planets_data = {}
        for name, body_id in self._bodies.items():
            res, _ = swisseph.calc_ut(jd_ut, body_id, flags)
            lon, lat, dist, speed_lon, _, _ = res

            planets_data[name] = {
                "longitude": lon,
                "latitude": lat,
                "speed": speed_lon,
                "is_retrograde": speed_lon < 0,
            }

        # Derive South Node (exactly 180 degrees from North Node)
        nn_lon = planets_data["north_node"]["longitude"]
        nn_lat = planets_data["north_node"]["latitude"]
        nn_speed = planets_data["north_node"]["speed"]

        planets_data["south_node"] = {
            "longitude": (nn_lon + 180.0) % 360.0,
            "latitude": -nn_lat,
            "speed": nn_speed,
            "is_retrograde": nn_speed < 0,
        }

        # 4. Calculate House Cusps, Ascendant, and MC
        h_sys_name = house_system.lower()
        if h_sys_name not in self._house_systems:
            raise ValueError(
                f"Unsupported house system: {house_system}. Supported: {list(self._house_systems.keys())}"
            )
        h_sys_code = self._house_systems[h_sys_name]

        # swisseph.houses returns (cusps, ascmc)
        # cusps is a 13-element tuple (cusps[1] to cusps[12] are 1st to 12th house cusps)
        # ascmc contains Ascendant at [0] and MC at [1]
        cusps_raw, ascmc_raw = swisseph.houses(jd_ut, latitude, longitude, h_sys_code)

        # Map to a clean list of 12 cusps
        cusps = [float(c) for c in cusps_raw]
        ascendant = float(ascmc_raw[0])
        mc = float(ascmc_raw[1])

        # If sidereal, houses are usually also offset by ayanamsa value.
        # pyswisseph handles this when FLG_SIDEREAL is set?
        # Wait, swisseph.houses does NOT use the sidereal flags automatically.
        # We need to subtract the ayanamsa from the tropical houses if we want sidereal houses!
        # Let's verify: swisseph.get_ayanamsa_ut(jd_ut) gets the ayanamsa value.
        # If zodiac_type is sidereal, we shift all houses by subtracting ayanamsa.
        # Let's check: Yes! This is the standard procedure to get sidereal houses.
        if zodiac_type.lower() == "sidereal":
            ayanamsa_val = swisseph.get_ayanamsa_ut(jd_ut)
            cusps = [(c - ayanamsa_val) % 360.0 for c in cusps]
            ascendant = (ascendant - ayanamsa_val) % 360.0
            mc = (mc - ayanamsa_val) % 360.0

        houses_data = {
            "ascendant": ascendant,
            "mc": mc,
            "cusps": cusps,
        }

        # 5. Populate metadata for exact chart reproduction
        metadata = {
            "julian_day": jd_ut,
            "zodiac_type": zodiac_type,
            "ayanamsa": ayanamsa if zodiac_type.lower() == "sidereal" else None,
            "ayanamsa_value": float(swisseph.get_ayanamsa_ut(jd_ut))
            if zodiac_type.lower() == "sidereal"
            else 0.0,
            "house_system": house_system,
            "swiss_ephe_version": swisseph.version,
        }

        return {
            "planets": planets_data,
            "houses": houses_data,
            "calculation_metadata": metadata,
        }
