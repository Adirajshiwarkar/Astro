from typing import Any

from app.domain.astrology.config import AstrologyEngineConfig
from app.domain.astrology.models import (
    Aspect,
    DerivedFactor,
    HousePlacement,
    PlanetPlacement,
    WesternChart,
)

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


def is_angle_between(angle: float, start: float, end: float) -> bool:
    """Check if an angle is between start and end angles, handling circular wrap-around."""
    a = angle % 360.0
    s = start % 360.0
    e = end % 360.0
    if s <= e:
        return s <= a < e
    else:
        return a >= s or a < e


def angular_distance(lon1: float, lon2: float) -> float:
    """Calculate the shortest angular distance between two longitudes."""
    diff = abs(lon1 - lon2) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


class WesternAstrologyEngine:
    def __init__(self, config: AstrologyEngineConfig | None = None) -> None:
        self.config = config or AstrologyEngineConfig()

        self._aspects_def = [
            ("conjunction", 0.0),
            ("sextile", 60.0),
            ("square", 90.0),
            ("trine", 120.0),
            ("opposition", 180.0),
        ]

    def get_sign(self, longitude: float) -> tuple[str, float]:
        """Convert longitude to sign name and degree within that sign."""
        lon = longitude % 360.0
        sign_index = int(lon // 30.0)
        sign_degree = lon % 30.0
        return SIGNS[sign_index], sign_degree

    def get_house(self, longitude: float, cusps: list[float]) -> int:
        """Find which house (1-12) a given longitude falls into."""
        # cusps is a 12-element list of house cusp longitudes
        for i in range(12):
            start = cusps[i]
            end = cusps[(i + 1) % 12]
            if is_angle_between(longitude, start, end):
                return i + 1

        # Fallback to closest cusp if float rounding issues occur
        min_dist = 360.0
        closest_house = 1
        for i in range(12):
            dist = angular_distance(longitude, cusps[i])
            if dist < min_dist:
                min_dist = dist
                closest_house = i + 1
        return closest_house

    def calculate_natal_chart(
        self, astro_data: dict[str, Any], timeframe: str = "natal"
    ) -> WesternChart:
        """Convert raw astronomical data into a Western Chart with placements, aspects, and derived factors."""
        # 1. Parse houses
        cusps_raw = astro_data["houses"]["cusps"]
        houses = []
        for i, cusp in enumerate(cusps_raw):
            sign, deg = self.get_sign(cusp)
            houses.append(
                HousePlacement(number=i + 1, cusp=cusp, sign=sign, sign_degree=deg)
            )

        ascendant = astro_data["houses"]["ascendant"]
        mc = astro_data["houses"]["mc"]

        # 2. Parse planets
        placements = []
        planets_data = astro_data["planets"]
        for name, data in planets_data.items():
            lon = data["longitude"]
            lat = data["latitude"]
            speed = data["speed"]
            is_retro = data["is_retrograde"]

            sign, deg = self.get_sign(lon)
            house = self.get_house(lon, cusps_raw)

            placements.append(
                PlanetPlacement(
                    name=name,
                    longitude=lon,
                    latitude=lat,
                    speed=speed,
                    is_retrograde=is_retro,
                    sign=sign,
                    sign_degree=deg,
                    house=house,
                )
            )

        # 3. Calculate aspects
        aspects = []
        points = list(planets_data.keys())
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                pt1, pt2 = points[i], points[j]
                lon1 = planets_data[pt1]["longitude"]
                lon2 = planets_data[pt2]["longitude"]

                dist = angular_distance(lon1, lon2)

                for aspect_name, aspect_angle in self._aspects_def:
                    max_orb = self.config.orbs.get(aspect_name, 8.0)
                    orb = abs(dist - aspect_angle)
                    if orb <= max_orb:
                        strength = 1.0 - (orb / max_orb) if max_orb > 0 else 1.0
                        aspects.append(
                            Aspect(
                                point1=pt1,
                                point2=pt2,
                                aspect_type=aspect_name,
                                angle=aspect_angle,
                                exact_angle=dist,
                                orb=orb,
                                strength=strength,
                            )
                        )

        # 4. Compile derived factors
        derived_factors = []

        # Placements factors
        for p in placements:
            derived_factors.append(
                DerivedFactor(
                    source="placement",
                    calculation=f"{p.name} at {p.sign_degree:.2f}° {p.sign} in House {p.house}",
                    methodology="Zodiac sign and house position based on tropical zodiac and house cusps.",
                    strength=1.0,
                    timeframe=timeframe,
                    engine_version=self.config.engine_version,
                )
            )

        # Aspects factors
        for asp in aspects:
            derived_factors.append(
                DerivedFactor(
                    source="aspect",
                    calculation=f"{asp.point1} {asp.aspect_type} {asp.point2} (orb {asp.orb:.2f}°)",
                    methodology=f"{asp.aspect_type.capitalize()} aspect (exact angle {asp.angle}°) within configured orb limit.",
                    strength=asp.strength,
                    timeframe=timeframe,
                    engine_version=self.config.engine_version,
                )
            )

        # Retrograde factors
        for p in placements:
            if p.is_retrograde:
                derived_factors.append(
                    DerivedFactor(
                        source="retrograde",
                        calculation=f"{p.name} retrograde (speed: {p.speed:.4f}°/day)",
                        methodology="Planet speed relative to Earth is negative.",
                        strength=1.0,
                        timeframe=timeframe,
                        engine_version=self.config.engine_version,
                    )
                )

        return WesternChart(
            placements=placements,
            houses=houses,
            ascendant=ascendant,
            mc=mc,
            aspects=aspects,
            derived_factors=derived_factors,
        )

    def calculate_transit_aspects(
        self, natal_chart: WesternChart, transit_chart: WesternChart
    ) -> list[DerivedFactor]:
        """Compare transit planet positions to natal planet positions and return transit-to-natal aspects."""
        transit_factors = []

        for t_p in transit_chart.placements:
            for n_p in natal_chart.placements:
                dist = angular_distance(t_p.longitude, n_p.longitude)

                for aspect_name, aspect_angle in self._aspects_def:
                    max_orb = self.config.orbs.get(aspect_name, 8.0)
                    orb = abs(dist - aspect_angle)
                    if orb <= max_orb:
                        strength = 1.0 - (orb / max_orb) if max_orb > 0 else 1.0
                        transit_factors.append(
                            DerivedFactor(
                                source="transit_aspect",
                                calculation=f"Transit {t_p.name} {aspect_name} Natal {n_p.name} (orb {orb:.2f}°)",
                                methodology=f"Transit planet forming a {aspect_name} aspect (exact angle {aspect_angle}°) with natal placement.",
                                strength=strength,
                                timeframe="temporary",
                                engine_version=self.config.engine_version,
                            )
                        )

        return transit_factors
