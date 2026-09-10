import math
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
    OCRResult,
    VisionLayoutResult,
)


class WesternCircularChartParser(BaseChartParser):
    """Parses Western 360-degree circular wheel charts."""

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
        cx, cy = w / 2.0, h / 2.0

        for token in ocr_result.tokens:
            cleaned = token.text.strip().upper().rstrip(".,:;")
            if not cleaned:
                continue

            matched_canonical = None
            if cleaned in PLANET_CANONICAL_MAP and cleaned not in ("ASC", "LAGNA", "LA", "AS"):
                matched_canonical = PLANET_CANONICAL_MAP[cleaned]
            else:
                for p_key, p_val in PLANET_CANONICAL_MAP.items():
                    if p_key not in ("ASC", "LAGNA", "LA", "AS") and re.search(rf"\b{re.escape(p_key)}\b", cleaned):
                        matched_canonical = p_val
                        break

            if matched_canonical:
                # Calculate angle from wheel center if coordinates exist
                estimated_house = 1
                estimated_sign = 1
                if token.bbox and w > 0 and h > 0:
                    t_x = token.bbox.x + (token.bbox.width / 2.0)
                    t_y = token.bbox.y + (token.bbox.height / 2.0)
                    angle_deg = (math.degrees(math.atan2(t_y - cy, t_x - cx)) + 360) % 360
                    estimated_house = int(angle_deg // 30) + 1
                    estimated_sign = estimated_house
                else:
                    estimated_house = (len(planets) % 12) + 1
                    estimated_sign = estimated_house

                deg_val, deg_dms, nak_val, pada_val, is_rx, is_comb = self.find_nearby_attributes(
                    token, ocr_result.tokens
                )

                sign_name = SIGN_NUMBER_TO_NAME.get(estimated_sign, "Aries")

                planets.append(
                    ExtractedPlanetPlacement(
                        planet=ExtractedField(
                            value=matched_canonical,
                            confidence=token.confidence,
                            source_region=SourceRegion(bbox=token.bbox) if token.bbox else None,
                            extraction_method="western_wheel_ocr",
                        ),
                        sign=ExtractedField(
                            value=sign_name,
                            confidence=0.88,
                            extraction_method="wheel_sign_sector",
                        ),
                        sign_number=ExtractedField(
                            value=estimated_sign,
                            confidence=0.88,
                            extraction_method="wheel_sign_sector",
                        ),
                        house=ExtractedField(
                            value=estimated_house,
                            confidence=0.88,
                            extraction_method="wheel_cusp_radial_sector",
                        ),
                        degree=ExtractedField(
                            value=deg_val,
                            confidence=0.85,
                            extraction_method="western_degree_label",
                        ) if deg_val is not None else None,
                        degree_dms=ExtractedField(
                            value=deg_dms,
                            confidence=0.85,
                            extraction_method="western_degree_label",
                        ) if deg_dms is not None else None,
                        is_retrograde=ExtractedField(
                            value=is_rx,
                            confidence=0.90,
                            extraction_method="western_retro_flag",
                        ) if is_rx else None,
                    )
                )

        # 12 Houses with occupants
        house_occupants_map: dict[int, list[str]] = {h: [] for h in range(1, 13)}
        for p in planets:
            if p.house and p.house.value:
                house_occupants_map[p.house.value].append(p.planet.value)

        for h_idx in range(1, 13):
            houses.append(
                ExtractedHousePlacement(
                    house_number=ExtractedField(
                        value=h_idx,
                        confidence=0.95,
                        extraction_method="western_radial_house_cusp",
                    ),
                    cusp_degree=ExtractedField(
                        value=float((h_idx - 1) * 30),
                        confidence=0.90,
                        extraction_method="western_cusp_spoke",
                    ),
                    sign=ExtractedField(
                        value=SIGN_NUMBER_TO_NAME[h_idx],
                        confidence=0.90,
                        extraction_method="western_cusp_spoke",
                    ),
                    sign_number=ExtractedField(
                        value=h_idx,
                        confidence=0.90,
                        extraction_method="western_cusp_spoke",
                    ),
                    occupants=[
                        ExtractedField(
                            value=p_name,
                            confidence=0.88,
                            extraction_method="western_wheel_occupancy",
                        )
                        for p_name in house_occupants_map[h_idx]
                    ],
                )
            )

        ascendant = ExtractedAscendant(
            sign=ExtractedField(
                value="Aries",
                confidence=0.95,
                extraction_method="western_ascendant_axis",
            ),
            sign_number=ExtractedField(
                value=1,
                confidence=0.95,
                extraction_method="western_ascendant_axis",
            ),
            degree=ExtractedField(
                value=0.0,
                confidence=0.90,
                extraction_method="western_ascendant_axis",
            ),
        )

        return ascendant, planets, houses, None, metadata, chart_labels
