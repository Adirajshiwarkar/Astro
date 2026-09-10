import re
from typing import Any

from app.domain.image_intelligence.models import (
    BoundingBox,
    ExtractedAscendant,
    ExtractedChartMetadata,
    ExtractedDashaInfo,
    ExtractedDashaPeriod,
    ExtractedField,
    ExtractedHousePlacement,
    ExtractedPlanetPlacement,
    SourceRegion,
)
from app.domain.image_intelligence.parsers.base import (
    PLANET_CANONICAL_MAP,
    SIGN_NAME_TO_NUMBER,
    SIGN_NUMBER_TO_NAME,
    BaseChartParser,
)
from app.domain.image_intelligence.preprocessing import PreprocessedImage
from app.domain.image_intelligence.providers.base import (
    OCRResult,
    VisionLayoutResult,
)


class TableReportParser(BaseChartParser):
    """Parses tabular/text-based Kundli planetary reports and dasha printouts."""

    def parse(
        self,
        vision_result: VisionLayoutResult,
        ocr_result: OCRResult,
        image_info: PreprocessedImage,
    ) -> tuple[
        ExtractedAscendant | None,
        list[ExtractedPlanetPlacement],
        list[ExtractedHousePlacement],
        ExtractedDashaInfo | None,
        ExtractedChartMetadata,
        list[ExtractedField[str]],
    ]:
        planets: list[ExtractedPlanetPlacement] = []
        houses: list[ExtractedHousePlacement] = []
        chart_labels: list[ExtractedField[str]] = []
        metadata = self.extract_common_metadata(ocr_result)
        ascendant: ExtractedAscendant | None = None
        dasha_info: ExtractedDashaInfo | None = None
        dasha_periods: list[ExtractedDashaPeriod] = []

        lines = ocr_result.lines or ocr_result.full_text.splitlines()

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # 1. Dasha Headers & Balance
            dasha_balance_match = re.search(
                r"(?:Balance\s+of\s+Dasha|Dasha\s+Balance|Balance|दशा\s*शेष)[\s:-]+([A-Za-z0-9\s.,-]+)",
                line_str,
                re.IGNORECASE,
            )
            if dasha_balance_match:
                if dasha_info is None:
                    dasha_info = ExtractedDashaInfo()
                dasha_info.balance_at_birth = ExtractedField(
                    value=dasha_balance_match.group(1).strip(),
                    confidence=0.92,
                    extraction_method="table_dasha_parser",
                )

            mahadasha_match = re.search(r"(?:Mahadasha|MD|महादशा)[\s:-]+([A-Za-z]+)", line_str, re.IGNORECASE)
            if mahadasha_match:
                if dasha_info is None:
                    dasha_info = ExtractedDashaInfo()
                dasha_info.current_mahadasha = ExtractedField(
                    value=mahadasha_match.group(1).strip(),
                    confidence=0.92,
                    extraction_method="table_dasha_parser",
                )

            antardasha_match = re.search(r"(?:Antardasha|AD|अन्तर्दशा)[\s:-]+([A-Za-z]+)", line_str, re.IGNORECASE)
            if antardasha_match:
                if dasha_info is None:
                    dasha_info = ExtractedDashaInfo()
                dasha_info.current_antardasha = ExtractedField(
                    value=antardasha_match.group(1).strip(),
                    confidence=0.90,
                    extraction_method="table_dasha_parser",
                )

            # Check Dasha period rows (e.g., "Jupiter 1995-02-10 2011-02-10 16y")
            dasha_row_match = re.search(
                r"\b(Sun|Moon|Mars|Rahu|Jupiter|Saturn|Mercury|Ketu|Venus)\b.*?(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}).*?(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})",
                line_str,
                re.IGNORECASE,
            )
            if dasha_row_match:
                d_lord = dasha_row_match.group(1).title()
                d_start = dasha_row_match.group(2)
                d_end = dasha_row_match.group(3)
                dasha_periods.append(
                    ExtractedDashaPeriod(
                        lord=ExtractedField(value=d_lord, confidence=0.92, extraction_method="table_dasha_row"),
                        start_date=ExtractedField(value=d_start, confidence=0.90, extraction_method="table_dasha_row"),
                        end_date=ExtractedField(value=d_end, confidence=0.90, extraction_method="table_dasha_row"),
                    )
                )

            # 2. Planetary Table Row Parsing
            tokens = line_str.split()
            if not tokens:
                continue

            # Look for planet name anywhere in line
            found_planet_name: str | None = None
            first_token = tokens[0].upper().rstrip(".,:;")
            if first_token in PLANET_CANONICAL_MAP:
                found_planet_name = PLANET_CANONICAL_MAP[first_token]
            else:
                for t in tokens:
                    tu = t.upper().rstrip(".,:;")
                    if tu in PLANET_CANONICAL_MAP:
                        found_planet_name = PLANET_CANONICAL_MAP[tu]
                        break

            if found_planet_name:
                pname = found_planet_name

                # Extract degree
                deg_val, deg_dms = self.extract_degree(line_str)
                nak_val, pada_val = self.extract_nakshatra_pada(line_str)

                # Extract sign name / number
                sign_name: str | None = None
                sign_num: int | None = None
                for t in tokens:
                    tu = t.upper().rstrip(".,:;")
                    if tu in SIGN_NAME_TO_NUMBER:
                        sign_num = SIGN_NAME_TO_NUMBER[tu]
                        sign_name = SIGN_NUMBER_TO_NAME[sign_num]
                        break
                    elif tu.isdigit() and 1 <= int(tu) <= 12 and sign_num is None:
                        sign_num = int(tu)
                        sign_name = SIGN_NUMBER_TO_NAME[sign_num]

                # Extract digits in line (excluding degree/time)
                standalone_digits = []
                for t in tokens:
                    clean_t = t.strip("()[]{},.:;")
                    if clean_t.isdigit() and 1 <= int(clean_t) <= 12:
                        standalone_digits.append(int(clean_t))

                house_num: int | None = None
                if len(standalone_digits) >= 2:
                    # e.g., [pada, house] -> [1, 6]
                    if standalone_digits[-2] in (1, 2, 3, 4) and pada_val is None:
                        pada_val = standalone_digits[-2]
                    house_num = standalone_digits[-1]
                elif len(standalone_digits) == 1:
                    if pada_val is not None:
                        house_num = standalone_digits[0]
                    else:
                        house_num = standalone_digits[0]

                if house_num is None:
                    house_num = sign_num if sign_num is not None else ((len(planets) % 12) + 1)

                is_retrograde = any(r in line_str.upper() for r in ["(R)", "RET", "वक्र", "RETROGRADE", "RX"])
                is_combust = any(c in line_str.upper() for c in ["(C)", "COM", "अस्त", "COMBUST"])

                if pname in ("Ascendant", "Lagna"):
                    ascendant = ExtractedAscendant(
                        sign=ExtractedField(
                            value=sign_name or "Aries",
                            confidence=0.95,
                            extraction_method="table_row_ascendant",
                        ),
                        sign_number=ExtractedField(
                            value=sign_num or 1,
                            confidence=0.95,
                            extraction_method="table_row_ascendant",
                        ) if sign_num else None,
                        degree=ExtractedField(
                            value=deg_val,
                            confidence=0.92,
                            extraction_method="table_degree_parser",
                        ) if deg_val is not None else None,
                        nakshatra=ExtractedField(
                            value=nak_val,
                            confidence=0.90,
                            extraction_method="table_nakshatra_parser",
                        ) if nak_val else None,
                        pada=ExtractedField(
                            value=pada_val,
                            confidence=0.90,
                            extraction_method="table_pada_parser",
                        ) if pada_val is not None else None,
                    )
                else:
                    planets.append(
                        ExtractedPlanetPlacement(
                            planet=ExtractedField(
                                value=pname,
                                confidence=0.95,
                                extraction_method="table_row_planet",
                            ),
                            sign=ExtractedField(
                                value=sign_name or "Aries",
                                confidence=0.92,
                                extraction_method="table_column_sign",
                            ),
                            sign_number=ExtractedField(
                                value=sign_num or 1,
                                confidence=0.92,
                                extraction_method="table_column_sign",
                            ),
                            house=ExtractedField(
                                value=house_num,
                                confidence=0.90,
                                extraction_method="table_column_house",
                            ),
                            degree=ExtractedField(
                                value=deg_val,
                                confidence=0.92,
                                extraction_method="table_degree_parser",
                            ) if deg_val is not None else None,
                            degree_dms=ExtractedField(
                                value=deg_dms,
                                confidence=0.92,
                                extraction_method="table_degree_parser",
                            ) if deg_dms is not None else None,
                            nakshatra=ExtractedField(
                                value=nak_val,
                                confidence=0.90,
                                extraction_method="table_nakshatra_parser",
                            ) if nak_val else None,
                            pada=ExtractedField(
                                value=pada_val,
                                confidence=0.90,
                                extraction_method="table_pada_parser",
                            ) if pada_val is not None else None,
                            is_retrograde=ExtractedField(
                                value=is_retrograde,
                                confidence=0.90,
                                extraction_method="table_retro_flag",
                            ) if is_retrograde else None,
                            is_combust=ExtractedField(
                                value=is_combust,
                                confidence=0.90,
                                extraction_method="table_combust_flag",
                            ) if is_combust else None,
                        )
                    )

        if dasha_periods and dasha_info:
            dasha_info.dasha_periods = dasha_periods

        # Build houses from planetary occupant references
        house_map: dict[int, list[str]] = {h: [] for h in range(1, 13)}
        for p in planets:
            if p.house and p.house.value:
                house_map[p.house.value].append(p.planet.value)

        for h_idx in range(1, 13):
            houses.append(
                ExtractedHousePlacement(
                    house_number=ExtractedField(
                        value=h_idx,
                        confidence=0.95,
                        extraction_method="table_house_enumeration",
                    ),
                    occupants=[
                        ExtractedField(
                            value=p_name,
                            confidence=0.92,
                            extraction_method="table_house_occupancy",
                        )
                        for p_name in house_map[h_idx]
                    ],
                )
            )

        return ascendant, planets, houses, dasha_info, metadata, chart_labels
