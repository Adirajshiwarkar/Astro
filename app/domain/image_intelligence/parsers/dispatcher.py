from typing import Any

from app.domain.image_intelligence.models import (
    ChartType,
    ExtractedField,
    StructuredChartRepresentation,
)
from app.domain.image_intelligence.parsers.base import BaseChartParser
from app.domain.image_intelligence.parsers.east_indian import EastIndianChartParser
from app.domain.image_intelligence.parsers.north_indian import NorthIndianChartParser
from app.domain.image_intelligence.parsers.south_indian import SouthIndianChartParser
from app.domain.image_intelligence.parsers.table_report import TableReportParser
from app.domain.image_intelligence.parsers.western_circular import (
    WesternCircularChartParser,
)
from app.domain.image_intelligence.preprocessing import PreprocessedImage
from app.domain.image_intelligence.providers.base import (
    OCRResult,
    VisionLayoutResult,
)


class ChartParser:
    """Unified parser that delegates to topology-specific parsers based on detected chart type."""

    def __init__(self) -> None:
        self.parsers: dict[ChartType, BaseChartParser] = {
            ChartType.NORTH_INDIAN: NorthIndianChartParser(),
            ChartType.SOUTH_INDIAN: SouthIndianChartParser(),
            ChartType.EAST_INDIAN: EastIndianChartParser(),
            ChartType.WESTERN_CIRCULAR: WesternCircularChartParser(),
            ChartType.TABLE_REPORT: TableReportParser(),
            ChartType.UNKNOWN: NorthIndianChartParser(),  # Fallback to North Indian parser
        }

    def parse_chart(
        self,
        chart_type_field: ExtractedField[ChartType],
        vision_result: VisionLayoutResult,
        ocr_result: OCRResult,
        image_info: PreprocessedImage,
    ) -> StructuredChartRepresentation:
        """Parse vision and OCR results into a complete StructuredChartRepresentation."""
        chart_type = chart_type_field.value
        parser = self.parsers.get(chart_type, self.parsers[ChartType.UNKNOWN])

        ascendant, planets, houses, dasha, metadata, chart_labels = parser.parse(
            vision_result, ocr_result, image_info
        )

        # Compute overall confidence
        confidence_scores: list[float] = [chart_type_field.confidence]
        if ascendant:
            confidence_scores.append(ascendant.sign.confidence)
        for p in planets:
            confidence_scores.append(p.planet.confidence)
            if p.degree:
                confidence_scores.append(p.degree.confidence)
            if p.sign:
                confidence_scores.append(p.sign.confidence)
        for h in houses:
            confidence_scores.append(h.house_number.confidence)

        overall_conf = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.50
        )

        raw_tokens_serializable = [
            {
                "text": t.text,
                "confidence": t.confidence,
                "bbox": t.bbox.model_dump() if t.bbox else None,
                "line_number": t.line_number,
            }
            for t in ocr_result.tokens
        ]

        return StructuredChartRepresentation(
            chart_type=chart_type_field,
            ascendant=ascendant,
            planets=planets,
            houses=houses,
            dasha=dasha,
            metadata=metadata,
            chart_labels=chart_labels,
            raw_ocr_tokens=raw_tokens_serializable,
            overall_confidence=round(overall_conf, 4),
            engine_version="1.0.0",
        )
