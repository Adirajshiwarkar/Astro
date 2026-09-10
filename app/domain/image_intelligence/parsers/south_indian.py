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

# South Indian Fixed 12-Box Perimeter Coordinates normalized (col 0..3, row 0..3)
# Box index to Sign Number (1 = Aries .. 12 = Pisces)
SOUTH_BOX_GRID = [
    {"sign": 12, "col": 0, "row": 0},  # Top-left: Pisces
    {"sign": 1, "col": 1, "row": 0},   # Top col 2: Aries
    {"sign": 2, "col": 2, "row": 0},   # Top col 3: Taurus
    {"sign": 3, "col": 3, "row": 0},   # Top-right: Gemini
    {"sign": 4, "col": 3, "row": 1},   # Right row 2: Cancer
    {"sign": 5, "col": 3, "row": 2},   # Right row 3: Leo
    {"sign": 6, "col": 3, "row": 3},   # Bottom-right: Virgo
    {"sign": 7, "col": 2, "row": 3},   # Bottom col 3: Libra
    {"sign": 8, "col": 1, "row": 3},   # Bottom col 2: Scorpio
    {"sign": 9, "col": 0, "row": 3},   # Bottom-left: Sagittarius
    {"sign": 10, "col": 0, "row": 2},  # Left row 3: Capricorn
    {"sign": 11, "col": 0, "row": 1},  # Left row 2: Aquarius
]


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

        w, h = image_info.dimensions
        if w <= 0 or h <= 0:
            w, h = 800, 800

        # Helper to map (x, y) coordinates to fixed 4x4 perimeter sign
        def get_sign_from_coords(x: float, y: float) -> int:
            norm_col = max(0, min(3, int((x / w) * 4)))
            norm_row = max(0, min(3, int((y / h) * 4)))

            min_dist = float("inf")
            best_sign = 1
            for item in SOUTH_BOX_GRID:
                d = (item["col"] - norm_col) ** 2 + (item["row"] - norm_row) ** 2
                if d < min_dist:
                    min_dist = d
                    best_sign = item["sign"]
            return best_sign

        sign_occupants: dict[int, list[str]] = {s: [] for s in range(1, 13)}
        lagna_sign_number: int | None = None
        lagna_token: OCRToken | None = None

        # 1. Scan tokens for Lagna and Planets
        planet_tokens: list[tuple[str, OCRToken]] = []

        for token in ocr_result.tokens:
            cleaned = token.text.strip().upper().rstrip(".,:;")
            if not cleaned:
                continue

            if cleaned in ("SOUTH", "CHART", "RASHI", "D1", "NAVAMSHA", "D9"):
                chart_labels.append(
                    ExtractedField(
                        value=token.text,
                        confidence=token.confidence,
                        source_region=SourceRegion(bbox=token.bbox) if token.bbox else None,
                        extraction_method="ocr_token",
                    )
                )

            # Check Lagna
            if cleaned in ("ASC", "LAGNA", "AS", "LA", "LAG", "लग्न"):
                lagna_token = token
                if token.bbox:
                    lagna_sign_number = get_sign_from_coords(
                        token.bbox.x + (token.bbox.width / 2.0),
                        token.bbox.y + (token.bbox.height / 2.0),
                    )
                else:
                    lagna_sign_number = 1

            # Check Planets
            matched_canonical = None
            if cleaned in PLANET_CANONICAL_MAP and cleaned not in ("ASC", "LAGNA", "LA", "AS", "LAG", "लग्न"):
                matched_canonical = PLANET_CANONICAL_MAP[cleaned]
            else:
                for p_key, p_val in PLANET_CANONICAL_MAP.items():
                    if p_key not in ("ASC", "LAGNA", "LA", "AS", "LAG", "लग्न") and re.search(rf"\b{re.escape(p_key)}\b", cleaned):
                        matched_canonical = p_val
                        break

            if matched_canonical:
                planet_tokens.append((matched_canonical, token))

        if lagna_sign_number is None:
            lagna_sign_number = 1

        # 2. Assign planets to signs & relative houses
        for pname, tok in planet_tokens:
            target_sign = 1
            if tok.bbox:
                target_sign = get_sign_from_coords(
                    tok.bbox.x + (tok.bbox.width / 2.0),
                    tok.bbox.y + (tok.bbox.height / 2.0),
                )
            else:
                target_sign = (len(planets) % 12) + 1

            if pname not in sign_occupants[target_sign]:
                sign_occupants[target_sign].append(pname)

            # Calculate relative house from Lagna
            rel_house = ((target_sign - lagna_sign_number) % 12) + 1

            deg_val, deg_dms, nak_val, pada_val, is_rx, is_comb = self.find_nearby_attributes(
                tok, ocr_result.tokens
            )

            planets.append(
                ExtractedPlanetPlacement(
                    planet=ExtractedField(
                        value=pname,
                        confidence=tok.confidence,
                        source_region=SourceRegion(bbox=tok.bbox) if tok.bbox else None,
                        extraction_method="south_indian_grid_token",
                    ),
                    sign=ExtractedField(
                        value=SIGN_NUMBER_TO_NAME[target_sign],
                        confidence=0.92,
                        extraction_method="fixed_south_indian_sign_box",
                    ),
                    sign_number=ExtractedField(
                        value=target_sign,
                        confidence=0.92,
                        extraction_method="fixed_south_indian_sign_box",
                    ),
                    house=ExtractedField(
                        value=rel_house,
                        confidence=0.90,
                        extraction_method="relative_lagna_offset",
                    ),
                    degree=ExtractedField(
                        value=deg_val,
                        confidence=0.88,
                        extraction_method="ocr_degree_extractor",
                    ) if deg_val is not None else None,
                    degree_dms=ExtractedField(
                        value=deg_dms,
                        confidence=0.88,
                        extraction_method="ocr_degree_extractor",
                    ) if deg_dms is not None else None,
                    nakshatra=ExtractedField(
                        value=nak_val,
                        confidence=0.88,
                        extraction_method="ocr_nakshatra_extractor",
                    ) if nak_val else None,
                    pada=ExtractedField(
                        value=pada_val,
                        confidence=0.88,
                        extraction_method="ocr_pada_extractor",
                    ) if pada_val is not None else None,
                    is_retrograde=ExtractedField(
                        value=is_rx,
                        confidence=0.90,
                        extraction_method="ocr_retro_flag",
                    ) if is_rx else None,
                    is_combust=ExtractedField(
                        value=is_comb,
                        confidence=0.90,
                        extraction_method="ocr_combust_flag",
                    ) if is_comb else None,
                )
            )

        # 3. Build Ascendant
        asc_sign_name = SIGN_NUMBER_TO_NAME[lagna_sign_number]
        ascendant = ExtractedAscendant(
            sign=ExtractedField(
                value=asc_sign_name,
                confidence=0.95,
                extraction_method="south_indian_lagna_marker",
            ),
            sign_number=ExtractedField(
                value=lagna_sign_number,
                confidence=0.95,
                extraction_method="south_indian_lagna_marker",
            ),
        )

        # 4. Build 12 houses relative to Lagna
        for h_idx in range(1, 13):
            s_num = ((lagna_sign_number - 1 + (h_idx - 1)) % 12) + 1
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
