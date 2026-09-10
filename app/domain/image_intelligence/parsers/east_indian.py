from app.domain.image_intelligence.models import (
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
    SIGN_NUMBER_TO_NAME,
    BaseChartParser,
)
from app.domain.image_intelligence.preprocessing import PreprocessedImage
from app.domain.image_intelligence.providers.base import (
    OCRResult,
    VisionLayoutResult,
)


class EastIndianChartParser(BaseChartParser):
    """Parses East Indian (Bengali/Odia) quadrant style Kundli charts."""

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
            if cleaned in PLANET_CANONICAL_MAP and cleaned not in ("ASC", "LAGNA", "LA", "AS", "लग्न"):
                pname = PLANET_CANONICAL_MAP[cleaned]
                h_num = (len(planets) % 12) + 1

                deg_val, deg_dms, nak_val, pada_val, is_rx, is_comb = self.find_nearby_attributes(
                    token, ocr_result.tokens
                )

                planets.append(
                    ExtractedPlanetPlacement(
                        planet=ExtractedField(
                            value=pname,
                            confidence=token.confidence,
                            source_region=SourceRegion(bbox=token.bbox) if token.bbox else None,
                            extraction_method="east_indian_token_parser",
                        ),
                        sign=ExtractedField(
                            value=SIGN_NUMBER_TO_NAME[h_num],
                            confidence=0.85,
                            extraction_method="east_indian_fixed_quadrant",
                        ),
                        sign_number=ExtractedField(
                            value=h_num,
                            confidence=0.85,
                            extraction_method="east_indian_fixed_quadrant",
                        ),
                        house=ExtractedField(
                            value=h_num,
                            confidence=0.85,
                            extraction_method="east_indian_house_derivation",
                        ),
                        degree=ExtractedField(
                            value=deg_val,
                            confidence=0.85,
                            extraction_method="east_indian_degree",
                        ) if deg_val is not None else None,
                        degree_dms=ExtractedField(
                            value=deg_dms,
                            confidence=0.85,
                            extraction_method="east_indian_degree",
                        ) if deg_dms is not None else None,
                        nakshatra=ExtractedField(
                            value=nak_val,
                            confidence=0.85,
                            extraction_method="east_indian_nakshatra",
                        ) if nak_val else None,
                        pada=ExtractedField(
                            value=pada_val,
                            confidence=0.85,
                            extraction_method="east_indian_pada",
                        ) if pada_val is not None else None,
                    )
                )

        # Standard 12 houses
        house_occupants_map: dict[int, list[str]] = {h: [] for h in range(1, 13)}
        for p in planets:
            if p.house and p.house.value:
                house_occupants_map[p.house.value].append(p.planet.value)

        for h_idx in range(1, 13):
            houses.append(
                ExtractedHousePlacement(
                    house_number=ExtractedField(
                        value=h_idx,
                        confidence=0.90,
                        extraction_method="east_indian_quadrant_sequence",
                    ),
                    sign=ExtractedField(
                        value=SIGN_NUMBER_TO_NAME[h_idx],
                        confidence=0.85,
                        extraction_method="east_indian_quadrant_sequence",
                    ),
                    sign_number=ExtractedField(
                        value=h_idx,
                        confidence=0.85,
                        extraction_method="east_indian_quadrant_sequence",
                    ),
                    occupants=[
                        ExtractedField(
                            value=p_name,
                            confidence=0.85,
                            extraction_method="east_indian_house_occupancy",
                        )
                        for p_name in house_occupants_map[h_idx]
                    ],
                )
            )

        ascendant = ExtractedAscendant(
            sign=ExtractedField(
                value="Aries",
                confidence=0.85,
                extraction_method="east_indian_lagna_marker",
            ),
            sign_number=ExtractedField(
                value=1,
                confidence=0.85,
                extraction_method="east_indian_lagna_marker",
            ),
        )

        return ascendant, planets, houses, None, metadata, chart_labels
