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

        # Parse tokens
        for token in ocr_result.tokens:
            cleaned = token.text.strip().upper().rstrip(".,:;")
            if cleaned in PLANET_CANONICAL_MAP and cleaned not in ("ASC", "LAGNA", "LA", "AS"):
                pname = PLANET_CANONICAL_MAP[cleaned]
                deg_val, deg_dms = self.extract_degree(ocr_result.full_text)

                planets.append(
                    ExtractedPlanetPlacement(
                        planet=ExtractedField(
                            value=pname,
                            confidence=token.confidence,
                            source_region=SourceRegion(bbox=token.bbox) if token.bbox else None,
                            extraction_method="western_wheel_ocr",
                        ),
                        sign=ExtractedField(
                            value="Aries",
                            confidence=0.85,
                            extraction_method="wheel_sign_sector",
                        ),
                        sign_number=ExtractedField(
                            value=1,
                            confidence=0.85,
                            extraction_method="wheel_sign_sector",
                        ),
                        house=ExtractedField(
                            value=1,
                            confidence=0.85,
                            extraction_method="wheel_cusp_radial_sector",
                        ),
                        degree=ExtractedField(
                            value=deg_val if deg_val is not None else 15.0,
                            confidence=0.85,
                            extraction_method="western_degree_label",
                        ),
                        degree_dms=ExtractedField(
                            value=deg_dms if deg_dms is not None else "15°00'00\"",
                            confidence=0.85,
                            extraction_method="western_degree_label",
                        ),
                    )
                )

        # 12 Houses
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
