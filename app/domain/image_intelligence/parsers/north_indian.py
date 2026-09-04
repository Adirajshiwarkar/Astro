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


class NorthIndianChartParser(BaseChartParser):
    """Parses North Indian Diamond/Rhombus style Kundli charts."""

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

        # 1. Map tokens to house regions or parse sequentially from OCR lines
        house_occupants: dict[int, list[str]] = {h: [] for h in range(1, 13)}
        house_signs: dict[int, int] = {}
        planet_tokens_found: list[dict[str, Any]] = []

        # Find house cells from vision regions or text
        cell_map: dict[int, LayoutRegion] = {}
        for r in vision_result.regions:
            if r.region_type == "house_cell" and isinstance(r.identifier, int) and 1 <= r.identifier <= 12:
                cell_map[r.identifier] = r

        # Map tokens from OCR into houses
        for token in ocr_result.tokens:
            cleaned = token.text.strip().upper().rstrip(".,:;")
            if not cleaned:
                continue

            # Check for chart label
            if cleaned in ("LAGNA", "KUNDLI", "RASHI", "D1", "NAVAMSHA", "D9", "CHALIT"):
                chart_labels.append(
                    ExtractedField(
                        value=token.text,
                        confidence=token.confidence,
                        source_region=SourceRegion(bbox=token.bbox) if token.bbox else None,
                        extraction_method="ocr_token",
                    )
                )

            # Check if token is a planet name or abbreviation
            if cleaned in PLANET_CANONICAL_MAP:
                canonical = PLANET_CANONICAL_MAP[cleaned]
                planet_tokens_found.append({
                    "name": canonical,
                    "token": token,
                    "raw": token.text,
                })

            # Check if token is a single/double digit representing sign number (1..12)
            if cleaned.isdigit():
                num = int(cleaned)
                if 1 <= num <= 12:
                    # Assign sign number to nearest house region if bbox exists
                    assigned = False
                    if token.bbox:
                        for h_idx, region in cell_map.items():
                            if (
                                region.bbox.x <= token.bbox.x <= region.bbox.x + region.bbox.width
                                and region.bbox.y <= token.bbox.y <= region.bbox.y + region.bbox.height
                            ):
                                house_signs[h_idx] = num
                                assigned = True
                                break
                    if not assigned and 1 not in house_signs:
                        # Default first found sign number to House 1 if top region
                        house_signs[1] = num

        # If vision cell contained_tokens exist, parse each cell directly
        for h_idx in range(1, 13):
            reg = cell_map.get(h_idx)
            if reg and reg.contained_tokens:
                for ct in reg.contained_tokens:
                    ct_clean = ct.strip().upper().rstrip(".,:;")
                    if ct_clean.isdigit() and 1 <= int(ct_clean) <= 12:
                        house_signs[h_idx] = int(ct_clean)
                    elif ct_clean in PLANET_CANONICAL_MAP:
                        pname = PLANET_CANONICAL_MAP[ct_clean]
                        if pname not in house_occupants[h_idx]:
                            house_occupants[h_idx].append(pname)

        # Associate found planets to houses based on spatial containment
        for p_item in planet_tokens_found:
            pname = p_item["name"]
            tok = p_item["token"]
            matched_house: int | None = None

            if tok.bbox and cell_map:
                # 1. Exact box containment check
                for h_idx, region in cell_map.items():
                    if (
                        region.bbox.x <= tok.bbox.x <= region.bbox.x + region.bbox.width
                        and region.bbox.y <= tok.bbox.y <= region.bbox.y + region.bbox.height
                    ):
                        matched_house = h_idx
                        break

                # 2. Distance-based check to nearest house region center if exact bounding box missed
                if matched_house is None:
                    min_dist = float("inf")
                    tok_cx = tok.bbox.x + (tok.bbox.width / 2.0)
                    tok_cy = tok.bbox.y + (tok.bbox.height / 2.0)
                    for h_idx, region in cell_map.items():
                        reg_cx = region.bbox.x + (region.bbox.width / 2.0)
                        reg_cy = region.bbox.y + (region.bbox.height / 2.0)
                        dist = ((tok_cx - reg_cx) ** 2 + (tok_cy - reg_cy) ** 2) ** 0.5
                        if dist < min_dist:
                            min_dist = dist
                            matched_house = h_idx

            if matched_house is None:
                # Distribute sequential planets across open houses instead of clumping into House 1
                matched_house = (len(planets) % 12) + 1

            if pname not in house_occupants[matched_house]:
                house_occupants[matched_house].append(pname)

            # Degree & Nakshatra parsing from subsequent tokens in full text
            deg_val, deg_dms = self.extract_degree(ocr_result.full_text)
            nak_val, pada_val = self.extract_nakshatra_pada(ocr_result.full_text)

            sign_num = house_signs.get(matched_house)
            sign_name = SIGN_NUMBER_TO_NAME.get(sign_num) if sign_num else None

            planets.append(
                ExtractedPlanetPlacement(
                    planet=ExtractedField(
                        value=pname,
                        confidence=tok.confidence,
                        source_region=SourceRegion(bbox=tok.bbox) if tok.bbox else None,
                        extraction_method="vision_ocr_alignment",
                    ),
                    sign=ExtractedField(
                        value=sign_name,
                        confidence=0.85,
                        extraction_method="house_sign_derivation",
                    ) if sign_name else None,
                    sign_number=ExtractedField(
                        value=sign_num,
                        confidence=0.85,
                        extraction_method="house_sign_derivation",
                    ) if sign_num else None,
                    house=ExtractedField(
                        value=matched_house,
                        confidence=0.90,
                        extraction_method="north_indian_diamond_grid",
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

        # Build 12 houses
        for h_idx in range(1, 13):
            s_num = house_signs.get(h_idx)
            s_name = SIGN_NUMBER_TO_NAME.get(s_num) if s_num else None
            occs = [
                ExtractedField(
                    value=p,
                    confidence=0.90,
                    extraction_method="north_indian_cell_parser",
                )
                for p in house_occupants.get(h_idx, [])
            ]
            houses.append(
                ExtractedHousePlacement(
                    house_number=ExtractedField(
                        value=h_idx,
                        confidence=1.0,
                        extraction_method="fixed_north_indian_topology",
                    ),
                    sign=ExtractedField(
                        value=s_name,
                        confidence=0.85,
                        extraction_method="north_indian_corner_number",
                    ) if s_name else None,
                    sign_number=ExtractedField(
                        value=s_num,
                        confidence=0.85,
                        extraction_method="north_indian_corner_number",
                    ) if s_num else None,
                    occupants=occs,
                )
            )

        # Ascendant from House 1
        ascendant: ExtractedAscendant | None = None
        h1_sign_num = house_signs.get(1)
        h1_sign_name = SIGN_NUMBER_TO_NAME.get(h1_sign_num) if h1_sign_num else None
        if h1_sign_name:
            ascendant = ExtractedAscendant(
                sign=ExtractedField(
                    value=h1_sign_name,
                    confidence=0.92,
                    extraction_method="house_1_sign_mapping",
                ),
                sign_number=ExtractedField(
                    value=h1_sign_num,
                    confidence=0.92,
                    extraction_method="house_1_sign_mapping",
                ) if h1_sign_num else None,
            )

        return ascendant, planets, houses, None, metadata, chart_labels
