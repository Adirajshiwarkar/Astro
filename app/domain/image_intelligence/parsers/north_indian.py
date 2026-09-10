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
    map_point_to_north_indian_house,
)
from app.domain.image_intelligence.preprocessing import PreprocessedImage
from app.domain.image_intelligence.providers.base import (
    LayoutRegion,
    OCRResult,
    OCRToken,
    VisionLayoutResult,
)


class NorthIndianChartParser(BaseChartParser):
    """Parses North Indian Diamond/Rhombus style Kundli charts with high-precision polygon localization."""

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

        img_w, img_h = image_info.dimensions
        if img_w <= 0 or img_h <= 0:
            img_w, img_h = 800, 800

        # Determine chart bounding region in image pixels if localized, else full image
        chart_xmin, chart_ymin = 0.0, 0.0
        chart_w, chart_h = float(img_w), float(img_h)

        # 1. Token decomposition and planet recognition
        house_occupants: dict[int, list[str]] = {h: [] for h in range(1, 13)}
        house_signs: dict[int, int] = {}
        detected_planets: list[dict[str, Any]] = []

        for token in ocr_result.tokens:
            raw_text = token.text.strip()
            if not raw_text:
                continue

            cleaned_upper = raw_text.upper().rstrip(".,:;")

            # Check for chart label
            if cleaned_upper in ("LAGNA", "KUNDLI", "RASHI", "D1", "NAVAMSHA", "D9", "CHALIT", "KUNDALI", "लग्न"):
                chart_labels.append(
                    ExtractedField(
                        value=token.text,
                        confidence=token.confidence,
                        source_region=SourceRegion(bbox=token.bbox) if token.bbox else None,
                        extraction_method="ocr_token",
                    )
                )

            # Compute normalized coordinates (u, v) in [0, 1] x [0, 1]
            if token.bbox:
                tok_cx = token.bbox.x + (token.bbox.width / 2.0)
                tok_cy = token.bbox.y + (token.bbox.height / 2.0)
            else:
                tok_cx = float(img_w / 2)
                tok_cy = float(img_h / 2)

            u = max(0.0, min(1.0, (tok_cx - chart_xmin) / chart_w))
            v = max(0.0, min(1.0, (tok_cy - chart_ymin) / chart_h))
            assigned_house = map_point_to_north_indian_house(u, v)

            # Check for sign numbers (digits 1 to 12) inside house cell
            # Only match isolated digits that are not part of degrees or dates
            if re.match(r"^([1-9]|1[0-2])$", cleaned_upper):
                sign_num = int(cleaned_upper)
                if assigned_house not in house_signs:
                    house_signs[assigned_house] = sign_num

            # Extract all candidate words from the token (handles conjuncted planets like "Ju Mo", "Su Me", "4 Sa(R)")
            # Split by whitespace, slashes, hyphens, parentheses
            words = re.findall(r"[A-Za-z\u0900-\u097F]+", raw_text)
            for word in words:
                w_upper = word.upper()
                canonical_planet = None

                # 1. Exact match in canonical dictionary
                if w_upper in PLANET_CANONICAL_MAP:
                    canonical_planet = PLANET_CANONICAL_MAP[w_upper]
                elif word in PLANET_CANONICAL_MAP:
                    canonical_planet = PLANET_CANONICAL_MAP[word]
                else:
                    # 2. Check substring prefixes (e.g. "Saturn", "Jup", "Merc")
                    for p_key, p_val in PLANET_CANONICAL_MAP.items():
                        if len(p_key) >= 2 and (w_upper == p_key or w_upper.startswith(p_key)):
                            canonical_planet = p_val
                            break

                if canonical_planet and canonical_planet != "Ascendant":
                    # Avoid duplicate planet detection in the exact same house
                    already_found = any(
                        p["name"] == canonical_planet and p["house"] == assigned_house
                        for p in detected_planets
                    )
                    if not already_found:
                        # Extract localized degree, nakshatra, and status flags
                        deg_val, deg_dms, nak_val, pada_val, is_rx, is_comb = self.find_nearby_attributes(
                            token, ocr_result.tokens
                        )
                        detected_planets.append({
                            "name": canonical_planet,
                            "house": assigned_house,
                            "token": token,
                            "deg_val": deg_val,
                            "deg_dms": deg_dms,
                            "nak_val": nak_val,
                            "pada_val": pada_val,
                            "is_rx": is_rx,
                            "is_comb": is_comb,
                        })

        # 2. Propagate continuous zodiac signs across all 12 houses from any detected anchor sign
        if house_signs:
            # Pick first detected house sign as anchor (prefer House 1 if present)
            anchor_h = 1 if 1 in house_signs else next(iter(house_signs.keys()))
            anchor_sign = house_signs[anchor_h]
            # Lagna Sign (House 1 sign)
            lagna_sign_num = ((anchor_sign - 1 - (anchor_h - 1)) % 12) + 1
        else:
            lagna_sign_num = 1  # Default Aries Lagna if no sign numbers present

        for h_idx in range(1, 13):
            calculated_sign = ((lagna_sign_num - 1 + (h_idx - 1)) % 12) + 1
            house_signs[h_idx] = calculated_sign

        # 3. Build ExtractedPlanetPlacement records and synchronize occupants
        for p_info in detected_planets:
            pname = p_info["name"]
            h_num = p_info["house"]
            tok = p_info["token"]

            if pname not in house_occupants[h_num]:
                house_occupants[h_num].append(pname)

            sign_num = house_signs.get(h_num, 1)
            sign_name = SIGN_NUMBER_TO_NAME.get(sign_num, "Aries")

            planets.append(
                ExtractedPlanetPlacement(
                    planet=ExtractedField(
                        value=pname,
                        confidence=tok.confidence,
                        source_region=SourceRegion(bbox=tok.bbox) if tok.bbox else None,
                        extraction_method="polygon_spatial_containment",
                    ),
                    sign=ExtractedField(
                        value=sign_name,
                        confidence=0.92,
                        extraction_method="north_indian_zodiac_continuity",
                    ),
                    sign_number=ExtractedField(
                        value=sign_num,
                        confidence=0.92,
                        extraction_method="north_indian_zodiac_continuity",
                    ),
                    house=ExtractedField(
                        value=h_num,
                        confidence=0.95,
                        extraction_method="north_indian_polygon_grid",
                    ),
                    degree=ExtractedField(
                        value=p_info["deg_val"],
                        confidence=0.88,
                        extraction_method="ocr_degree_extractor",
                    ) if p_info["deg_val"] is not None else None,
                    degree_dms=ExtractedField(
                        value=p_info["deg_dms"],
                        confidence=0.88,
                        extraction_method="ocr_degree_extractor",
                    ) if p_info["deg_dms"] is not None else None,
                    nakshatra=ExtractedField(
                        value=p_info["nak_val"],
                        confidence=0.88,
                        extraction_method="ocr_nakshatra_extractor",
                    ) if p_info["nak_val"] else None,
                    pada=ExtractedField(
                        value=p_info["pada_val"],
                        confidence=0.88,
                        extraction_method="ocr_pada_extractor",
                    ) if p_info["pada_val"] is not None else None,
                    is_retrograde=ExtractedField(
                        value=p_info["is_rx"],
                        confidence=0.90,
                        extraction_method="ocr_retro_flag",
                    ) if p_info["is_rx"] else None,
                    is_combust=ExtractedField(
                        value=p_info["is_comb"],
                        confidence=0.90,
                        extraction_method="ocr_combust_flag",
                    ) if p_info["is_comb"] else None,
                )
            )

        # 4. Build 12 houses with calculated signs and synchronized occupants
        for h_idx in range(1, 13):
            s_num = house_signs.get(h_idx, ((h_idx - 1) % 12) + 1)
            s_name = SIGN_NUMBER_TO_NAME.get(s_num, "Aries")
            occs = [
                ExtractedField(
                    value=p,
                    confidence=0.92,
                    extraction_method="north_indian_polygon_parser",
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
                        confidence=0.92,
                        extraction_method="north_indian_zodiac_continuity",
                    ),
                    sign_number=ExtractedField(
                        value=s_num,
                        confidence=0.92,
                        extraction_method="north_indian_zodiac_continuity",
                    ),
                    occupants=occs,
                )
            )

        # 5. Ascendant / Lagna from House 1
        h1_sign_num = house_signs.get(1, 1)
        h1_sign_name = SIGN_NUMBER_TO_NAME.get(h1_sign_num, "Aries")

        lagna_deg = None
        lagna_nak = None
        lagna_pada = None
        for p in planets:
            if p.planet.value in ("Ascendant", "Lagna"):
                lagna_deg = p.degree.value if p.degree else None
                lagna_nak = p.nakshatra.value if p.nakshatra else None
                lagna_pada = p.pada.value if p.pada else None
                break

        ascendant = ExtractedAscendant(
            sign=ExtractedField(
                value=h1_sign_name,
                confidence=0.95,
                extraction_method="house_1_sign_mapping",
            ),
            sign_number=ExtractedField(
                value=h1_sign_num,
                confidence=0.95,
                extraction_method="house_1_sign_mapping",
            ),
            degree=ExtractedField(
                value=lagna_deg,
                confidence=0.88,
                extraction_method="house_1_degree",
            ) if lagna_deg is not None else None,
            nakshatra=ExtractedField(
                value=lagna_nak,
                confidence=0.88,
                extraction_method="house_1_nakshatra",
            ) if lagna_nak else None,
            pada=ExtractedField(
                value=lagna_pada,
                confidence=0.88,
                extraction_method="house_1_pada",
            ) if lagna_pada is not None else None,
        )

        return ascendant, planets, houses, None, metadata, chart_labels
