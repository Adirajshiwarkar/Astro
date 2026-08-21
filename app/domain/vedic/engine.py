import datetime
from typing import Any

from app.domain.vedic.config import VedicEngineConfig
from app.domain.vedic.models import (
    AntardashaPeriod,
    BhavaPlacement,
    GrahaPlacement,
    MahadashaPeriod,
    VedicAspect,
    VedicCalculationMetadata,
    VedicChart,
    VedicTransitPlacement,
)

RASHIS = [
    "Mesha",  # Aries
    "Vrishabha",  # Taurus
    "Mithuna",  # Gemini
    "Karka",  # Cancer
    "Simha",  # Leo
    "Kanya",  # Virgo
    "Tula",  # Libra
    "Vrishchika",  # Scorpio
    "Dhanu",  # Sagittarius
    "Makara",  # Capricorn
    "Kumbha",  # Aquarius
    "Meena",  # Pisces
]

NAKSHATRAS = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

GRAHA_NAME_MAP = {
    "sun": ("Surya", "Sun"),
    "moon": ("Chandra", "Moon"),
    "mars": ("Mangala", "Mars"),
    "mercury": ("Budha", "Mercury"),
    "jupiter": ("Guru", "Jupiter"),
    "venus": ("Shukra", "Venus"),
    "saturn": ("Shani", "Saturn"),
    "north_node": ("Rahu", "North Node"),
    "south_node": ("Ketu", "South Node"),
}

DASHA_LORDS = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
]
DASHA_YEARS = [7, 20, 6, 10, 7, 18, 16, 19, 17]


class VedicAstrologyEngine:
    def __init__(self, config: VedicEngineConfig | None = None) -> None:
        self.config = config or VedicEngineConfig()

    def get_rashi(self, longitude: float) -> tuple[str, float]:
        """Convert longitude to Rashi name and degree within that Rashi."""
        lon = longitude % 360.0
        rashi_index = int(lon // 30.0)
        rashi_degree = lon % 30.0
        return RASHIS[rashi_index], rashi_degree

    def get_nakshatra(self, longitude: float) -> tuple[str, int]:
        """Convert longitude to Nakshatra name and Pada (1-4)."""
        lon = longitude % 360.0
        nak_width = 360.0 / 27.0  # 13.33333333 degrees
        nak_index = int(lon // nak_width)
        nak_name = NAKSHATRAS[nak_index]

        pada_width = nak_width / 4.0  # 3.33333333 degrees
        pada = int((lon % nak_width) // pada_width) + 1
        return nak_name, pada

    def get_bhava_equal(self, longitude: float, lagna_longitude: float) -> int:
        """Calculate Bhava (house 1-12) using Whole Sign / Equal house from Lagna."""
        lagna_sign_idx = int((lagna_longitude % 360.0) // 30.0)
        target_sign_idx = int((longitude % 360.0) // 30.0)
        return (target_sign_idx - lagna_sign_idx) % 12 + 1

    def calculate_drishti(
        self, grahas_data: list[GrahaPlacement]
    ) -> list[VedicAspect]:
        """Calculate Vedic aspects (Drishti) between Grahas."""
        aspects = []
        for g1 in grahas_data:
            s1 = RASHIS.index(g1.rashi)
            for g2 in grahas_data:
                if g1.vedic_name == g2.vedic_name:
                    continue

                s2 = RASHIS.index(g2.rashi)
                house_distance = (s2 - s1) % 12 + 1

                # 1. Every Graha aspects the 7th house from itself
                is_aspect = False
                aspect_type = "7th house aspect"

                if house_distance == 7:
                    is_aspect = True

                # 2. Special Drishtis
                elif g1.vedic_name == "Mangala" and house_distance in [4, 8]:
                    is_aspect = True
                    aspect_type = f"Special Mars {house_distance}th house aspect"
                elif g1.vedic_name == "Guru" and house_distance in [5, 9]:
                    is_aspect = True
                    aspect_type = f"Special Jupiter {house_distance}th house aspect"
                elif g1.vedic_name == "Shani" and house_distance in [3, 10]:
                    is_aspect = True
                    aspect_type = f"Special Saturn {house_distance}th house aspect"

                if is_aspect:
                    aspects.append(
                        VedicAspect(
                            aspecting_graha=g1.vedic_name,
                            aspected_point=g2.vedic_name,
                            house_distance=house_distance,
                            aspect_type=aspect_type,
                        )
                    )
        return aspects

    def calculate_vimshottari_dasha(
        self, birth_dt: datetime.datetime, moon_lon: float
    ) -> list[MahadashaPeriod]:
        """Calculate Vimshottari Dasha and Antardasha periods for a 120-year timeline."""
        moon_lon = moon_lon % 360.0
        nak_width = 360.0 / 27.0
        nak_idx = int(moon_lon // nak_width)
        nak_start = nak_idx * nak_width
        elapsed = moon_lon - nak_start
        fraction_elapsed = elapsed / nak_width

        first_lord_idx = nak_idx % 9

        # Theoretical start of the first Mahadasha
        mahadasha_full_years = DASHA_YEARS[first_lord_idx]
        theoretical_start = birth_dt - datetime.timedelta(
            days=fraction_elapsed * mahadasha_full_years * 365.25
        )

        dashas = []
        current_mahadasha_start = theoretical_start
        curr_lord_idx = first_lord_idx

        # Generate a full 120-year cycle (9 Mahadashas) from the theoretical start
        for _ in range(9):
            lord = DASHA_LORDS[curr_lord_idx]
            mahadasha_years = DASHA_YEARS[curr_lord_idx]
            mahadasha_end = current_mahadasha_start + datetime.timedelta(
                days=mahadasha_years * 365.25
            )

            # Skip if this Mahadasha ended before birth
            if mahadasha_end <= birth_dt:
                current_mahadasha_start = mahadasha_end
                curr_lord_idx = (curr_lord_idx + 1) % 9
                continue

            # Calculate Antardashas
            antardashas = []
            current_ant_start = current_mahadasha_start
            for j in range(9):
                ant_lord_idx = (curr_lord_idx + j) % 9
                ant_lord = DASHA_LORDS[ant_lord_idx]
                ant_years = (
                    mahadasha_years * DASHA_YEARS[ant_lord_idx]
                ) / 120.0
                ant_end = current_ant_start + datetime.timedelta(
                    days=ant_years * 365.25
                )

                if ant_end > birth_dt:
                    actual_start = max(current_ant_start, birth_dt)
                    antardashas.append(
                        AntardashaPeriod(
                            lord=ant_lord,
                            duration_years=float(ant_years),
                            start_date=actual_start.isoformat(),
                            end_date=ant_end.isoformat(),
                        )
                    )
                current_ant_start = ant_end

            actual_mahadasha_start = max(current_mahadasha_start, birth_dt)
            dashas.append(
                MahadashaPeriod(
                    lord=lord,
                    duration_years=float(mahadasha_years),
                    start_date=actual_mahadasha_start.isoformat(),
                    end_date=mahadasha_end.isoformat(),
                    antardashas=antardashas,
                )
            )

            current_mahadasha_start = mahadasha_end
            curr_lord_idx = (curr_lord_idx + 1) % 9

        return dashas

    def calculate_vedic_chart(
        self,
        birth_dt: datetime.datetime,
        astro_data: dict[str, Any],
    ) -> VedicChart:
        """Construct the Vedic Chart using sidereal astronomical data."""
        # Check that we are calculating in sidereal zodiac
        metadata_in = astro_data.get("calculation_metadata", {})
        zodiac_type = metadata_in.get("zodiac_type", "tropical")
        ayanamsa_name = metadata_in.get("ayanamsa", self.config.default_ayanamsa)

        if zodiac_type.lower() != "sidereal":
            raise ValueError(
                "Vedic Astrology calculations require sidereal astronomical data."
            )

        # 1. Lagna (Ascendant)
        lagna_lon = astro_data["houses"]["ascendant"]
        lagna_rashi, lagna_deg = self.get_rashi(lagna_lon)

        # 2. Bhavas (Equal/Whole Sign division from Lagna)
        bhavas = []
        lagna_sign_idx = RASHIS.index(lagna_rashi)
        for i in range(12):
            bhava_rashi_idx = (lagna_sign_idx + i) % 12
            bhava_rashi = RASHIS[bhava_rashi_idx]
            # In Whole Sign, each house cusp is defined as 0 degrees of its Rashi
            bhavas.append(
                BhavaPlacement(
                    number=i + 1,
                    cusp=float(bhava_rashi_idx * 30.0),
                    rashi=bhava_rashi,
                    rashi_degree=0.0,
                )
            )

        # 3. Grahas
        grahas = []
        planets_data = astro_data["planets"]
        moon_longitude = 0.0

        for west_name, g_data in planets_data.items():
            if west_name not in GRAHA_NAME_MAP:
                continue

            v_name, formal_west = GRAHA_NAME_MAP[west_name]
            lon = g_data["longitude"]
            lat = g_data["latitude"]
            speed = g_data["speed"]
            is_retro = g_data["is_retrograde"]

            rashi, rashi_deg = self.get_rashi(lon)
            bhava = self.get_bhava_equal(lon, lagna_lon)
            nakshatra, pada = self.get_nakshatra(lon)

            if west_name == "moon":
                moon_longitude = lon

            grahas.append(
                GrahaPlacement(
                    vedic_name=v_name,
                    western_name=formal_west,
                    longitude=lon,
                    latitude=lat,
                    speed=speed,
                    is_retrograde=is_retro,
                    rashi=rashi,
                    rashi_degree=rashi_deg,
                    bhava=bhava,
                    nakshatra=nakshatra,
                    nakshatra_pada=pada,
                )
            )

        # 4. Vedic Aspects (Drishti)
        aspects = self.calculate_drishti(grahas)

        # 5. Vimshottari Dasha
        dasha = self.calculate_vimshottari_dasha(birth_dt, moon_longitude)

        # 6. Metadata
        metadata = VedicCalculationMetadata(
            methodology=(
                "Vedic Astrology Engine utilizing the Sidereal Zodiac. "
                "Bhavas are determined using the Whole Sign/Equal House system from Lagna. "
                "Aspects (Drishti) are calculated on a sign-to-sign basis including special "
                "planetary Drishtis for Mars, Jupiter, and Saturn. "
                "Vimshottari Dasha is calculated using Chandra's exact Nakshatra longitude at birth."
            ),
            ayanamsa=str(ayanamsa_name),
            calculation_timestamp=datetime.datetime.now(
                datetime.UTC
            ).isoformat(),
            engine_version=self.config.engine_version,
            source_metadata=metadata_in,
        )

        return VedicChart(
            lagna=lagna_rashi,
            lagna_degree=lagna_deg,
            grahas=grahas,
            bhavas=bhavas,
            aspects=aspects,
            vimshottari_dasha=dasha,
            metadata=metadata,
        )

    # --- Extensibility Interfaces ---

    def calculate_divisional_placement(
        self, longitude: float, division: int
    ) -> tuple[str, float]:
        """Calculate placement in a divisional chart (Varga).

        Supports Navamsha (D9) calculation as reference implementation.
        """
        if division == 9:
            # Navamsha D9
            lon = longitude % 360.0
            rashi_idx = int(lon // 30.0)
            deg_in_rashi = lon % 30.0
            # Each Navamsha is 3°20' (200 minutes)
            nav_idx = int(deg_in_rashi // 3.3333333333333335)

            # Starting sign in Navamsha depends on Rashi element:
            # Fire (Aries, Leo, Sag) starts at Aries
            # Earth (Taurus, Virgo, Cap) starts at Capricorn
            # Air (Gemini, Libra, Aqu) starts at Libra
            # Water (Cancer, Sco, Pis) starts at Cancer
            rashi_group = rashi_idx % 4
            if rashi_group == 0:  # Fire
                start_sign = 0  # Aries
            elif rashi_group == 1:  # Earth
                start_sign = 9  # Capricorn
            elif rashi_group == 2:  # Air
                start_sign = 6  # Libra
            else:  # Water
                start_sign = 3  # Cancer

            target_sign_idx = (start_sign + nav_idx) % 12
            return RASHIS[target_sign_idx], (deg_in_rashi % 3.3333333333333335)

        raise NotImplementedError(
            f"Divisional chart D{division} is not implemented. Extend here."
        )

    def detect_yogas(self, chart: VedicChart) -> list[str]:
        """Detect Vedic Yogas (planetary combinations).

        Extendable framework. Demonstrates Gajakesari Yoga.
        """
        yogas = []
        # Gajakesari Yoga: Jupiter (Guru) is in a Kendra (house 1, 4, 7, 10) from Moon (Chandra)
        chandra = next((g for g in chart.grahas if g.vedic_name == "Chandra"), None)
        guru = next((g for g in chart.grahas if g.vedic_name == "Guru"), None)

        if chandra and guru:
            s_chandra = RASHIS.index(chandra.rashi)
            s_guru = RASHIS.index(guru.rashi)
            dist = (s_guru - s_chandra) % 12 + 1
            if dist in [1, 4, 7, 10]:
                yogas.append("Gajakesari Yoga")

        return yogas

    def calculate_transits(
        self, natal_chart: VedicChart, transit_astro_data: dict[str, Any]
    ) -> list[VedicTransitPlacement]:
        """Calculate Vedic Transits (Gochara) relative to the Natal Moon sign (Chandra Rashi)."""
        chandra = next(
            (g for g in natal_chart.grahas if g.vedic_name == "Chandra"), None
        )
        if not chandra:
            raise ValueError(
                "Natal chart must contain Chandra (Moon) placement for Vedic transits."
            )

        natal_moon_idx = RASHIS.index(chandra.rashi)
        transits = []

        planets_data = transit_astro_data["planets"]
        for west_name, g_data in planets_data.items():
            if west_name not in GRAHA_NAME_MAP:
                continue

            v_name, _ = GRAHA_NAME_MAP[west_name]
            lon = g_data["longitude"]
            transit_rashi, _ = self.get_rashi(lon)
            transit_sign_idx = RASHIS.index(transit_rashi)

            house_from_chandra = (transit_sign_idx - natal_moon_idx) % 12 + 1

            transits.append(
                VedicTransitPlacement(
                    graha_name=v_name,
                    transit_sign=transit_rashi,
                    house_from_chandra=house_from_chandra,
                    transit_longitude=lon,
                )
            )

        return transits
