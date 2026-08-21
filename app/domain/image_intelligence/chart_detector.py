import re
from app.domain.image_intelligence.models import ChartType, ExtractedField, SourceRegion
from app.domain.image_intelligence.preprocessing import PreprocessedImage
from app.domain.image_intelligence.providers.base import OCRResult, VisionLayoutResult


class ChartTypeDetector:
    """Detects astrological chart typology (North Indian, South Indian, East Indian,

    Western Circular, Table/Text report) using geometric cues and OCR tokens.
    """

    def detect(
        self,
        vision_result: VisionLayoutResult,
        ocr_result: OCRResult,
        image_info: PreprocessedImage,
    ) -> ExtractedField[ChartType]:
        # 1. Vision model explicit classification
        if vision_result.detected_chart_type != ChartType.UNKNOWN and vision_result.chart_confidence >= 0.70:
            return ExtractedField(
                value=vision_result.detected_chart_type,
                confidence=vision_result.chart_confidence,
                extraction_method="vision_geometry_classifier",
            )

        text_lower = ocr_result.full_text.lower()

        # 2. Text keyword detection
        if any(k in text_lower for k in ["south indian", "south chart", "mesha rashi fixed", "south style"]):
            return ExtractedField(
                value=ChartType.SOUTH_INDIAN,
                confidence=0.92,
                extraction_method="ocr_keyword_detector",
            )

        if any(k in text_lower for k in ["east indian", "bengali kundli", "odia kundli", "east style"]):
            return ExtractedField(
                value=ChartType.EAST_INDIAN,
                confidence=0.90,
                extraction_method="ocr_keyword_detector",
            )

        if any(k in text_lower for k in ["western chart", "natal wheel", "placidus", "koch", "tropical wheel"]):
            return ExtractedField(
                value=ChartType.WESTERN_CIRCULAR,
                confidence=0.92,
                extraction_method="ocr_keyword_detector",
            )

        # Tabular report detection (presence of columns like planet, rashi, deg, nakshatra, dasha)
        table_indicators = ["planet", "rashi", "degree", "nakshatra", "pada", "balance", "mahadasha"]
        matches = sum(1 for ind in table_indicators if ind in text_lower)
        if matches >= 3:
            return ExtractedField(
                value=ChartType.TABLE_REPORT,
                confidence=0.88,
                extraction_method="tabular_keyword_density",
            )

        # North Indian indicators (rhombus/diamond keywords or default Indian kundli)
        if any(k in text_lower for k in ["north indian", "lagna kundli", "d1 chart", "janma kundali", "kundli", "kundali", "rashi chart"]):
            return ExtractedField(
                value=ChartType.NORTH_INDIAN,
                confidence=0.85,
                extraction_method="ocr_keyword_detector",
            )

        # 3. Geometric heuristic
        if vision_result.geometry_detected.get("rhombus_detected"):
            return ExtractedField(
                value=ChartType.NORTH_INDIAN,
                confidence=0.80,
                extraction_method="geometric_rhombus_detection",
            )

        # Default fallback
        return ExtractedField(
            value=ChartType.NORTH_INDIAN,
            confidence=0.60,
            extraction_method="default_heuristic_fallback",
        )
