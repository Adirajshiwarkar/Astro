import datetime
from typing import Any

from app.domain.astrology.models import WesternChart
from app.domain.canonical.models import (
    CanonicalChartMetadata,
    CanonicalChartRepresentation,
    CanonicalDashaInfo,
    CanonicalDashaPeriod,
    CanonicalField,
    CanonicalHousePlacement,
    CanonicalPlanetPlacement,
    CanonicalPointPlacement,
    ProvenanceMetadata,
)
from app.domain.image_intelligence.models import (
    ExtractedField,
    StructuredChartRepresentation,
)
from app.domain.vedic.models import VedicChart

CANONICAL_PLANET_NAMES = {
    "sun": "Sun", "surya": "Sun", "ravi": "Sun",
    "moon": "Moon", "chandra": "Moon", "soma": "Moon",
    "mars": "Mars", "mangal": "Mars", "kuja": "Mars",
    "mercury": "Mercury", "budha": "Mercury", "budh": "Mercury",
    "jupiter": "Jupiter", "guru": "Jupiter", "brihaspati": "Jupiter",
    "venus": "Venus", "shukra": "Venus", "sukra": "Venus",
    "saturn": "Saturn", "shani": "Saturn", "sani": "Saturn",
    "rahu": "Rahu", "north_node": "Rahu", "north node": "Rahu",
    "ketu": "Ketu", "south_node": "Ketu", "south node": "Ketu",
    "uranus": "Uranus", "harshal": "Uranus",
    "neptune": "Neptune", "varun": "Neptune",
    "pluto": "Pluto", "yama": "Pluto",
    "ascendant": "Ascendant", "lagna": "Ascendant", "asc": "Ascendant",
}

SIGN_NUMBER_TO_NAME = {
    1: "Aries", 2: "Taurus", 3: "Gemini", 4: "Cancer",
    5: "Leo", 6: "Virgo", 7: "Libra", 8: "Scorpio",
    9: "Sagittarius", 10: "Capricorn", 11: "Aquarius", 12: "Pisces"
}

SIGN_NAME_TO_NUMBER = {
    "ARIES": 1, "MESHA": 1, "मेष": 1,
    "TAURUS": 2, "VRISHABHA": 2, "वृषभ": 2,
    "GEMINI": 3, "MITHUNA": 3, "मिथुन": 3,
    "CANCER": 4, "KARKA": 4, "कर्क": 4,
    "LEO": 5, "SIMHA": 5, "सिंह": 5,
    "VIRGO": 6, "KANYA": 6, "कन्या": 6,
    "LIBRA": 7, "TULA": 7, "तुला": 7,
    "SCORPIO": 8, "VRISCHIKA": 8, "वृश्चिक": 8,
    "SAGITTARIUS": 9, "DHANU": 9, "धनु": 9,
    "CAPRICORN": 10, "MAKARA": 10, "मकर": 10,
    "AQUARIUS": 11, "KUMBHA": 11, "कुम्भ": 11,
    "PISCES": 12, "MEENA": 12, "मीन": 12,
}


class ChartNormalizer:
    """Transforms disparate astrological data sources into CanonicalChartRepresentation."""

    def normalize_planet_name(self, name: str) -> str:
        cleaned = name.strip().lower()
        return CANONICAL_PLANET_NAMES.get(cleaned, name.strip().title())

    def normalize_sign(self, sign_name_or_num: str | int) -> tuple[str, int]:
        if isinstance(sign_name_or_num, int):
            num = max(1, min(12, sign_name_or_num))
            return SIGN_NUMBER_TO_NAME[num], num

        clean_str = str(sign_name_or_num).strip().upper()
        if clean_str.isdigit():
            num = max(1, min(12, int(clean_str)))
            return SIGN_NUMBER_TO_NAME[num], num

        num = SIGN_NAME_TO_NUMBER.get(clean_str, 1)
        return SIGN_NUMBER_TO_NAME[num], num

    def from_image_extraction(
        self, img_chart: StructuredChartRepresentation
    ) -> CanonicalChartRepresentation:
        """Normalize an image intelligence extracted chart."""
        root_prov = ProvenanceMetadata(
            source="image_extraction",
            method=f"vision_ocr_{img_chart.chart_type.value}",
            confidence=img_chart.overall_confidence,
            engine_version=img_chart.engine_version,
            calculation_config={"detected_chart_type": img_chart.chart_type.value},
        )

        def make_field(extracted: ExtractedField[Any] | None, default_prov: ProvenanceMetadata) -> CanonicalField[Any] | None:
            if extracted is None:
                return None
            f_prov = ProvenanceMetadata(
                source="image_extraction",
                method=extracted.extraction_method,
                confidence=extracted.confidence,
                engine_version=img_chart.engine_version,
                source_region=extracted.source_region.model_dump() if extracted.source_region else None,
            )
            return CanonicalField(value=extracted.value, provenance=f_prov)

        # 1. Ascendant
        asc_placement: CanonicalPointPlacement | None = None
        if img_chart.ascendant:
            s_name, s_num = self.normalize_sign(img_chart.ascendant.sign.value)
            asc_prov = ProvenanceMetadata(
                source="image_extraction",
                method=img_chart.ascendant.sign.extraction_method,
                confidence=img_chart.ascendant.sign.confidence,
                engine_version=img_chart.engine_version,
            )
            asc_placement = CanonicalPointPlacement(
                name=CanonicalField(value="Ascendant", provenance=asc_prov),
                sign=CanonicalField(value=s_name, provenance=asc_prov),
                sign_number=CanonicalField(value=s_num, provenance=asc_prov),
                degree=make_field(img_chart.ascendant.degree, asc_prov),
                total_longitude=None,
                nakshatra=make_field(img_chart.ascendant.nakshatra, asc_prov),
                pada=make_field(img_chart.ascendant.pada, asc_prov),
            )

        # 2. Planets
        planets_dict: dict[str, CanonicalPlanetPlacement] = {}
        for p in img_chart.planets:
            c_name = self.normalize_planet_name(p.planet.value)
            p_prov = ProvenanceMetadata(
                source="image_extraction",
                method=p.planet.extraction_method,
                confidence=p.planet.confidence,
                engine_version=img_chart.engine_version,
                source_region=p.planet.source_region.model_dump() if p.planet.source_region else None,
            )
            s_name, s_num = self.normalize_sign(p.sign.value) if p.sign else ("Aries", 1)

            planets_dict[c_name] = CanonicalPlanetPlacement(
                planet=CanonicalField(value=c_name, provenance=p_prov),
                sign=CanonicalField(value=s_name, provenance=p_prov) if p.sign else None,
                sign_number=CanonicalField(value=s_num, provenance=p_prov) if p.sign_number or p.sign else None,
                degree=make_field(p.degree, p_prov),
                total_longitude=None,
                house=make_field(p.house, p_prov),
                nakshatra=make_field(p.nakshatra, p_prov),
                pada=make_field(p.pada, p_prov),
                is_retrograde=make_field(p.is_retrograde, p_prov),
                is_combust=make_field(p.is_combust, p_prov),
            )

        # 3. Houses
        houses_list: list[CanonicalHousePlacement] = []
        for h in img_chart.houses:
            h_prov = ProvenanceMetadata(
                source="image_extraction",
                method=h.house_number.extraction_method,
                confidence=h.house_number.confidence,
                engine_version=img_chart.engine_version,
            )
            s_name, s_num = self.normalize_sign(h.sign.value) if h.sign else (None, None)
            houses_list.append(
                CanonicalHousePlacement(
                    house_number=CanonicalField(value=h.house_number.value, provenance=h_prov),
                    sign=CanonicalField(value=s_name, provenance=h_prov) if s_name else None,
                    sign_number=CanonicalField(value=s_num, provenance=h_prov) if s_num else None,
                    cusp_degree=make_field(h.cusp_degree, h_prov),
                    occupants=[
                        CanonicalField(value=self.normalize_planet_name(occ.value), provenance=h_prov)
                        for occ in h.occupants
                    ],
                )
            )

        # 4. Dasha
        dasha_info: CanonicalDashaInfo | None = None
        if img_chart.dasha:
            d_prov = ProvenanceMetadata(source="image_extraction", method="table_dasha_parser", confidence=0.90)
            dasha_info = CanonicalDashaInfo(
                current_mahadasha=make_field(img_chart.dasha.current_mahadasha, d_prov),
                current_antardasha=make_field(img_chart.dasha.current_antardasha, d_prov),
                balance_at_birth=make_field(img_chart.dasha.balance_at_birth, d_prov),
            )

        # 5. Metadata
        meta_prov = ProvenanceMetadata(source="image_extraction", method="ocr_metadata", confidence=0.88)
        meta = CanonicalChartMetadata(
            native_name=make_field(img_chart.metadata.native_name, meta_prov),
            birth_date=make_field(img_chart.metadata.birth_date, meta_prov),
            birth_time=make_field(img_chart.metadata.birth_time, meta_prov),
            birth_place=make_field(img_chart.metadata.birth_place, meta_prov),
            chart_title=make_field(img_chart.metadata.chart_title, meta_prov),
            ayanamsa=make_field(img_chart.metadata.ayanamsa, meta_prov),
        )

        return CanonicalChartRepresentation(
            zodiac_system="sidereal",
            ascendant=asc_placement,
            planets=planets_dict,
            houses=houses_list,
            dasha=dasha_info,
            metadata=meta,
            provenance=root_prov,
        )

    def from_vedic_chart(self, vedic: VedicChart) -> CanonicalChartRepresentation:
        """Normalize a Vedic domain engine calculated chart."""
        root_prov = ProvenanceMetadata(
            source="vedic_engine",
            method=vedic.metadata.methodology,
            confidence=1.0,
            engine_version=vedic.metadata.engine_version,
            calculation_config={"ayanamsa": vedic.metadata.ayanamsa},
        )

        # Ascendant
        s_name, s_num = self.normalize_sign(vedic.lagna)
        asc_placement = CanonicalPointPlacement(
            name=CanonicalField(value="Ascendant", provenance=root_prov),
            sign=CanonicalField(value=s_name, provenance=root_prov),
            sign_number=CanonicalField(value=s_num, provenance=root_prov),
            degree=CanonicalField(value=round(vedic.lagna_degree % 30.0, 4), provenance=root_prov),
            total_longitude=CanonicalField(value=round(vedic.lagna_degree, 4), provenance=root_prov),
        )

        # Planets
        planets_dict: dict[str, CanonicalPlanetPlacement] = {}
        for g in vedic.grahas:
            c_name = self.normalize_planet_name(g.western_name)
            ps_name, ps_num = self.normalize_sign(g.rashi)
            planets_dict[c_name] = CanonicalPlanetPlacement(
                planet=CanonicalField(value=c_name, provenance=root_prov),
                sign=CanonicalField(value=ps_name, provenance=root_prov),
                sign_number=CanonicalField(value=ps_num, provenance=root_prov),
                degree=CanonicalField(value=round(g.rashi_degree, 4), provenance=root_prov),
                total_longitude=CanonicalField(value=round(g.longitude, 4), provenance=root_prov),
                house=CanonicalField(value=g.bhava, provenance=root_prov),
                nakshatra=CanonicalField(value=g.nakshatra, provenance=root_prov),
                pada=CanonicalField(value=g.nakshatra_pada, provenance=root_prov),
                is_retrograde=CanonicalField(value=g.is_retrograde, provenance=root_prov),
                speed=CanonicalField(value=round(g.speed, 4), provenance=root_prov),
            )

        # Houses
        houses_list: list[CanonicalHousePlacement] = []
        for b in vedic.bhavas:
            bs_name, bs_num = self.normalize_sign(b.rashi)
            houses_list.append(
                CanonicalHousePlacement(
                    house_number=CanonicalField(value=b.number, provenance=root_prov),
                    sign=CanonicalField(value=bs_name, provenance=root_prov),
                    sign_number=CanonicalField(value=bs_num, provenance=root_prov),
                    cusp_degree=CanonicalField(value=round(b.rashi_degree, 4), provenance=root_prov),
                    cusp_longitude=CanonicalField(value=round(b.cusp, 4), provenance=root_prov),
                )
            )

        return CanonicalChartRepresentation(
            zodiac_system="sidereal",
            ascendant=asc_placement,
            planets=planets_dict,
            houses=houses_list,
            metadata=CanonicalChartMetadata(
                ayanamsa=CanonicalField(value=vedic.metadata.ayanamsa, provenance=root_prov)
            ),
            provenance=root_prov,
        )

    def from_western_chart(self, west: WesternChart) -> CanonicalChartRepresentation:
        """Normalize a Western domain engine calculated chart."""
        root_prov = ProvenanceMetadata(
            source="western_engine",
            method="tropical_western_astrology",
            confidence=1.0,
            engine_version="1.0.0",
        )

        # Ascendant
        asc_sign_num = int(west.ascendant // 30) + 1
        asc_sign_name = SIGN_NUMBER_TO_NAME[asc_sign_num]
        asc_placement = CanonicalPointPlacement(
            name=CanonicalField(value="Ascendant", provenance=root_prov),
            sign=CanonicalField(value=asc_sign_name, provenance=root_prov),
            sign_number=CanonicalField(value=asc_sign_num, provenance=root_prov),
            degree=CanonicalField(value=round(west.ascendant % 30.0, 4), provenance=root_prov),
            total_longitude=CanonicalField(value=round(west.ascendant, 4), provenance=root_prov),
        )

        # MC
        mc_sign_num = int(west.mc // 30) + 1
        mc_sign_name = SIGN_NUMBER_TO_NAME[mc_sign_num]
        mc_placement = CanonicalPointPlacement(
            name=CanonicalField(value="MC", provenance=root_prov),
            sign=CanonicalField(value=mc_sign_name, provenance=root_prov),
            sign_number=CanonicalField(value=mc_sign_num, provenance=root_prov),
            degree=CanonicalField(value=round(west.mc % 30.0, 4), provenance=root_prov),
            total_longitude=CanonicalField(value=round(west.mc, 4), provenance=root_prov),
        )

        # Planets
        planets_dict: dict[str, CanonicalPlanetPlacement] = {}
        for p in west.placements:
            c_name = self.normalize_planet_name(p.name)
            s_name, s_num = self.normalize_sign(p.sign)
            planets_dict[c_name] = CanonicalPlanetPlacement(
                planet=CanonicalField(value=c_name, provenance=root_prov),
                sign=CanonicalField(value=s_name, provenance=root_prov),
                sign_number=CanonicalField(value=s_num, provenance=root_prov),
                degree=CanonicalField(value=round(p.sign_degree, 4), provenance=root_prov),
                total_longitude=CanonicalField(value=round(p.longitude, 4), provenance=root_prov),
                house=CanonicalField(value=p.house, provenance=root_prov),
                is_retrograde=CanonicalField(value=p.is_retrograde, provenance=root_prov),
                speed=CanonicalField(value=round(p.speed, 4), provenance=root_prov),
            )

        # Houses
        houses_list: list[CanonicalHousePlacement] = []
        for h in west.houses:
            hs_name, hs_num = self.normalize_sign(h.sign)
            houses_list.append(
                CanonicalHousePlacement(
                    house_number=CanonicalField(value=h.number, provenance=root_prov),
                    sign=CanonicalField(value=hs_name, provenance=root_prov),
                    sign_number=CanonicalField(value=hs_num, provenance=root_prov),
                    cusp_degree=CanonicalField(value=round(h.sign_degree, 4), provenance=root_prov),
                    cusp_longitude=CanonicalField(value=round(h.cusp, 4), provenance=root_prov),
                )
            )

        return CanonicalChartRepresentation(
            zodiac_system="tropical",
            ascendant=asc_placement,
            midheaven=mc_placement,
            planets=planets_dict,
            houses=houses_list,
            provenance=root_prov,
        )

    def from_ephemeris_dict(
        self,
        ephe_data: dict[str, Any],
        birth_datetime: datetime.datetime | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> CanonicalChartRepresentation:
        """Normalize raw ephemeris calculation output."""
        meta_dict = ephe_data.get("calculation_metadata", {})
        root_prov = ProvenanceMetadata(
            source="ephemeris_calculation",
            method="swiss_ephemeris",
            confidence=1.0,
            engine_version=meta_dict.get("swiss_ephe_version", "1.0.0"),
            calculation_config=meta_dict,
        )

        houses_data = ephe_data.get("houses", {})
        asc_deg = float(houses_data.get("ascendant", 0.0))
        asc_sign_num = int(asc_deg // 30) + 1
        asc_placement = CanonicalPointPlacement(
            name=CanonicalField(value="Ascendant", provenance=root_prov),
            sign=CanonicalField(value=SIGN_NUMBER_TO_NAME[asc_sign_num], provenance=root_prov),
            sign_number=CanonicalField(value=asc_sign_num, provenance=root_prov),
            degree=CanonicalField(value=round(asc_deg % 30.0, 4), provenance=root_prov),
            total_longitude=CanonicalField(value=round(asc_deg, 4), provenance=root_prov),
        )

        planets_dict: dict[str, CanonicalPlanetPlacement] = {}
        for p_name, p_val in ephe_data.get("planets", {}).items():
            c_name = self.normalize_planet_name(p_name)
            lon = float(p_val.get("longitude", 0.0))
            s_num = int(lon // 30) + 1
            s_deg = lon % 30.0

            # Estimate house from cusps if available
            cusps = houses_data.get("cusps", [])
            house_num: int = 1
            if len(cusps) >= 13:
                # cusps 1..12
                for i in range(1, 13):
                    c1 = cusps[i]
                    c2 = cusps[1] if i == 12 else cusps[i + 1]
                    if c1 <= c2:
                        if c1 <= lon < c2:
                            house_num = i
                            break
                    else:
                        if lon >= c1 or lon < c2:
                            house_num = i
                            break

            planets_dict[c_name] = CanonicalPlanetPlacement(
                planet=CanonicalField(value=c_name, provenance=root_prov),
                sign=CanonicalField(value=SIGN_NUMBER_TO_NAME[s_num], provenance=root_prov),
                sign_number=CanonicalField(value=s_num, provenance=root_prov),
                degree=CanonicalField(value=round(s_deg, 4), provenance=root_prov),
                total_longitude=CanonicalField(value=round(lon, 4), provenance=root_prov),
                house=CanonicalField(value=house_num, provenance=root_prov),
                is_retrograde=CanonicalField(value=bool(p_val.get("is_retrograde", False)), provenance=root_prov),
                speed=CanonicalField(value=round(float(p_val.get("speed", 0.0)), 4), provenance=root_prov),
            )

        houses_list: list[CanonicalHousePlacement] = []
        cusps_list = houses_data.get("cusps", [])
        for i in range(1, 13):
            c_lon = float(cusps_list[i]) if len(cusps_list) > i else float((i - 1) * 30)
            hs_num = int(c_lon // 30) + 1
            houses_list.append(
                CanonicalHousePlacement(
                    house_number=CanonicalField(value=i, provenance=root_prov),
                    sign=CanonicalField(value=SIGN_NUMBER_TO_NAME[hs_num], provenance=root_prov),
                    sign_number=CanonicalField(value=hs_num, provenance=root_prov),
                    cusp_degree=CanonicalField(value=round(c_lon % 30.0, 4), provenance=root_prov),
                    cusp_longitude=CanonicalField(value=round(c_lon, 4), provenance=root_prov),
                )
            )

        meta = CanonicalChartMetadata(
            birth_date=CanonicalField(value=birth_datetime.date().isoformat(), provenance=root_prov) if birth_datetime else None,
            birth_time=CanonicalField(value=birth_datetime.time().isoformat(), provenance=root_prov) if birth_datetime else None,
            latitude=CanonicalField(value=latitude, provenance=root_prov) if latitude is not None else None,
            longitude=CanonicalField(value=longitude, provenance=root_prov) if longitude is not None else None,
            ayanamsa=CanonicalField(value=str(meta_dict.get("ayanamsa")), provenance=root_prov) if meta_dict.get("ayanamsa") else None,
        )

        return CanonicalChartRepresentation(
            zodiac_system=meta_dict.get("zodiac_type", "sidereal"),
            ascendant=asc_placement,
            planets=planets_dict,
            houses=houses_list,
            metadata=meta,
            provenance=root_prov,
        )
