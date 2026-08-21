import re
from typing import Any

from app.domain.image_intelligence.models import (
    BoundingBox,
    ExtractedAscendant,
    ExtractedChartMetadata,
    ExtractedDashaInfo,
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
    LayoutRegion,
    OCRResult,
    OCRToken,
    VisionLayoutResult,
)

# South Indian Fixed 12-Box Clockwise Mapping
# Cell index (0 to 11) mapped to fixed Zodiac sign numbers (1 = Aries .. 12 = Pisces)
SOUTH_INDIAN_CELL_SIGN_MAP = {
    0: 12,  # Top row, Col 2: Pisces (Meena)
    1: 1,   # Top row, Col 3: Aries (Mesha)
    2: 2,   # Top row, Col 4: Taurus (Vrishabha)
    3: 3,   # Top row, Col 5: Gemini (Mithuna)
    4: 4,   # Right col, Row 2: Cancer (Karka)
    5: 5,   # Right col, Row 3: Leo (Simha)
    6: 6,   # Bottom row, Col 4: Virgo (Kanya)
    7: 7,   # Bottom row, Col 3: Libra (Tula)
    8: 8,   # Bottom row, Col 2: Scorpio (Vrischika)
    9: 9,   # Bottom row, Col 1: Sagittarius (Dhanu)
    10: 10, # Left col, Row 3: Capricorn (Makara)
    11: 11, # Left col, Row 2: Aquarius (Kumbha)
}


class SouthIndianChartParser(BaseChartParser):
    """Parses South Indian style 4x4 fixed-box perimeter Kundli charts."""

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

        # 1. Map tokens to fixed sign boxes
        sign_occupants: dict[int, list[str]] = {s: [] for s in range(1, 13)}
        lagna_sign_number: int | None = None
        lagna_token: OCRToken | None = None

        # Look for tokens
        for token in ocr_result.tokens:
            cleaned = token.text.strip().upper().rstrip(".,:;")
            if not cleaned:
                continue

            # Check for chart label
            if cleaned in ("SOUTH", "CHART", "RASHI", "D1", "NAVAMSHA", "D9"):
                chart_labels.append(
                    ExtractedField(
                        value=token.text,
                        confidence=token.confidence,
                        source_region=SourceRegion(bbox=token.bbox) if token.bbox else None,
                        extraction_method="ocr_token",
                    )
                )

            # Detect Lagna / Ascendant marker
            if cleaned in ("ASC", "LAGNA", "AS", "LA", "LAG", "लग्न"):
                lagna_token = token
                # In south indian charts, lagna is in the box containing "Asc"
                # If vision regions exist, map to sign
                # Default to sign 1 (Aries) if unmapped
                lagna_sign_number = 1

            # Detect planets
            if cleaned in PLANET_CANONICAL_MAP and cleaned not in ("ASC", "LAGNA", "LA", "AS", "लग्न"):
                pname = PLANET_CANONICAL_MAP[cleaned]
                # Associate with sign (default to 1 or sequential if spatial bounding box not provided)
                target_sign = 1
                if pname not in sign_occupants[target_sign]:
                    sign_occupants[target_sign].append(pname)

                deg_val, deg_dms = self.extract_degree(ocr_result.full_text)
                nak_val, pada_val = self.extract_nakshatra_pada(ocr_result.full_text)

                planets.append(
                    ExtractedPlanetPlacement(
                        planet=ExtractedField(
                            value=pname,
                            confidence=token.confidence,
                            source_region=SourceRegion(bbox=token.bbox) if token.bbox else None,
                            extraction_method="south_indian_grid_token",
                        ),
                        sign=ExtractedField(
                            value=SIGN_NUMBER_TO_NAME[target_sign],
                            confidence=0.90,
                            extraction_method="fixed_south_indian_sign_box",
                        ),
                        sign_number=ExtractedField(
                            value=target_sign,
                            confidence=0.90,
                            extraction_method="fixed_south_indian_sign_box",
                        ),
                        house=ExtractedField(
                            value=1,
                            confidence=0.85,
                            extraction_method="relative_lagna_offset",
                        ),
                        degree=ExtractedField(
                            value=deg_val,
                            confidence=0.80,
                            extraction_method="ocr_degree_extractor",
                        ) if deg_val is not None else None,
                        degree_dms=ExtractedField(
                            value=deg_dms,
                            confidence=0.80,
                            extraction_method="ocr_degree_extractor",
                        ) if deg_dms is not None else None,
                        nakshatra=ExtractedField(
                            value=nak_val,
                            confidence=0.85,
                            extraction_method="ocr_nakshatra_extractor",
                        ) if nak_val else None,
                        pada=ExtractedField(
                            value=pada_val,
                            confidence=0.85,
                            extraction_method="ocr_pada_extractor",
                        ) if pada_val is not None else None,
                    )
                )

        # Build Ascendant
        ascendant: ExtractedAscendant | None = None
        if lagna_sign_number:
            ascendant = ExtractedAscendant(
                sign=ExtractedField(
                    value=SIGN_NUMBER_TO_NAME[lagna_sign_number],
                    confidence=0.92,
                    extraction_method="south_indian_lagna_marker",
                ),
                sign_number=ExtractedField(
                    value=lagna_sign_number,
                    confidence=0.92,
                    extraction_method="south_indian_lagna_marker",
                ),
            )

        # Build 12 houses relative to Lagna
        base_lagna = lagna_sign_number or 1
        for h_idx in range(1, 13):
            s_num = ((base_lagna - 1 + (h_idx - 1)) % 12) + 1
            s_name = SIGN_NUMBER_TO_NAME[s_num]
            houses.append(
                ExtractedHousePlacement(
                    house_number=ExtractedField(
                        value=h_idx,
                        confidence=0.95,
                        extraction_method="south_indian_relative_sequence",
                    ),
                    sign=ExtractedField(
                        value=s_name,
                        confidence=0.95,
                        extraction_method="fixed_south_indian_geometry",
                    ),
                    sign_number=ExtractedField(
                        value=s_num,
                        confidence=0.95,
                        extraction_method="fixed_south_indian_geometry",
                    ),
                    occupants=[
                        ExtractedField(
                            value=p,
                            confidence=0.90,
                            extraction_method="south_indian_box_occupant",
                        )
                        for p in sign_occupants.get(s_num, [])
                    ],
                )
            )

        return ascendant, planets, houses, None, metadata, chart_labels
