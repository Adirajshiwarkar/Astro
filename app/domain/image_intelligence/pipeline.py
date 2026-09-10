from app.domain.image_intelligence.chart_detector import ChartTypeDetector
from app.domain.image_intelligence.models import StructuredChartRepresentation
from app.domain.image_intelligence.parsers.dispatcher import ChartParser
from app.domain.image_intelligence.preprocessing import ImagePreprocessor
from app.domain.image_intelligence.providers.base import OCRProvider, VisionProvider
from app.domain.image_intelligence.providers.heuristic import (
    HeuristicOCRProvider,
    HeuristicVisionProvider,
)
from app.domain.image_intelligence.reasoning import ChartReasoningSynthesizer
from app.domain.image_intelligence.security import SecureImageValidator
from app.domain.image_intelligence.validator import ChartExtractionValidator


class ImageIntelligencePipeline:
    """End-to-end processing and reasoning pipeline for Kundli and astrological chart images."""

    def __init__(
        self,
        validator: SecureImageValidator | None = None,
        preprocessor: ImagePreprocessor | None = None,
        vision_provider: VisionProvider | None = None,
        ocr_provider: OCRProvider | None = None,
        detector: ChartTypeDetector | None = None,
        parser: ChartParser | None = None,
        extraction_validator: ChartExtractionValidator | None = None,
        reasoner: ChartReasoningSynthesizer | None = None,
    ) -> None:
        self.validator = validator or SecureImageValidator()
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.vision_provider = vision_provider or HeuristicVisionProvider()
        self.ocr_provider = ocr_provider or HeuristicOCRProvider()
        self.detector = detector or ChartTypeDetector()
        self.parser = parser or ChartParser()
        self.extraction_validator = extraction_validator or ChartExtractionValidator()
        self.reasoner = reasoner or ChartReasoningSynthesizer()

    async def process_image(
        self, file_bytes: bytes, declared_mime: str | None = None
    ) -> StructuredChartRepresentation:
        """Execute the full 8-stage image intelligence and reasoning pipeline."""
        # 1. Secure File Validation
        sanitized_bytes, detected_mime, dimensions = self.validator.validate_and_sanitize(
            file_bytes, declared_mime
        )

        # 2. Preprocessing & Contrast Enhancement
        preprocessed = self.preprocessor.preprocess(sanitized_bytes)
        enhanced_bytes = preprocessed.get_enhanced_bytes()

        # 3. Vision Layout Analysis
        vision_result = await self.vision_provider.analyze_layout(
            enhanced_bytes, preprocessed.dimensions
        )

        # 4. OCR Extraction
        ocr_result = await self.ocr_provider.extract_text(
            enhanced_bytes, preprocessed.dimensions
        )

        # 5. Chart-Type Detection
        chart_type_field = self.detector.detect(vision_result, ocr_result, preprocessed)

        # 6. Chart Parsing & Structured Representation
        chart_repr = self.parser.parse_chart(
            chart_type_field, vision_result, ocr_result, preprocessed
        )

        # 7. Astrological Consistency Validation
        validation_summary = self.extraction_validator.validate(chart_repr)
        chart_repr.validation_summary = validation_summary

        # 8. Astrological Reasoning & Synthesis
        reasoning_data = self.reasoner.synthesize(chart_repr)
        chart_repr.reasoning = reasoning_data
        chart_repr.insights = reasoning_data.get("insights", [])

        return chart_repr
