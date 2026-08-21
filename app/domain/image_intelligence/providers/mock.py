from typing import Any

from app.domain.image_intelligence.models import BoundingBox, ChartType
from app.domain.image_intelligence.providers.base import (
    LayoutRegion,
    OCRProvider,
    OCRResult,
    OCRToken,
    VisionLayoutResult,
    VisionProvider,
)


class MockVisionProvider(VisionProvider):
    """Deterministic mock vision provider for testing chart topologies and visual regions."""

    def __init__(
        self,
        chart_type: ChartType = ChartType.NORTH_INDIAN,
        chart_confidence: float = 0.95,
        mock_regions: list[LayoutRegion] | None = None,
    ) -> None:
        self.chart_type = chart_type
        self.chart_confidence = chart_confidence
        self.mock_regions = mock_regions

    async def analyze_layout(
        self, image_bytes: bytes, dimensions: tuple[int, int]
    ) -> VisionLayoutResult:
        w, h = dimensions
        if self.mock_regions is not None:
            regions = self.mock_regions
        else:
            regions = [
                LayoutRegion(
                    region_type="house_cell",
                    identifier=1,
                    bbox=BoundingBox(x=w * 0.35, y=h * 0.15, width=w * 0.3, height=h * 0.25),
                    confidence=0.98,
                    contained_tokens=["1", "Su", "14°20'"],
                ),
                LayoutRegion(
                    region_type="house_cell",
                    identifier=2,
                    bbox=BoundingBox(x=w * 0.15, y=h * 0.15, width=w * 0.2, height=h * 0.2),
                    confidence=0.95,
                    contained_tokens=["2", "Mo", "05°10'"],
                ),
            ]

        return VisionLayoutResult(
            detected_chart_type=self.chart_type,
            chart_confidence=self.chart_confidence,
            regions=regions,
            geometry_detected={"line_count": 16, "symmetry_score": 0.94},
            provider_name="mock_vision",
        )


class MockOCRProvider(OCRProvider):
    """Deterministic mock OCR provider for testing astrological token extraction."""

    def __init__(
        self,
        mock_tokens: list[OCRToken] | None = None,
        mock_full_text: str | None = None,
    ) -> None:
        self.mock_tokens = mock_tokens
        self.mock_full_text = mock_full_text

    async def extract_text(
        self, image_bytes: bytes, dimensions: tuple[int, int]
    ) -> OCRResult:
        if self.mock_tokens is not None:
            tokens = self.mock_tokens
            full_text = self.mock_full_text or " ".join(t.text for t in tokens)
        else:
            tokens = [
                OCRToken(text="Lagna Kundli", bbox=BoundingBox(x=100, y=50, width=200, height=30), confidence=0.99),
                OCRToken(text="Asc", bbox=BoundingBox(x=360, y=180, width=40, height=20), confidence=0.98),
                OCRToken(text="1", bbox=BoundingBox(x=380, y=200, width=20, height=20), confidence=0.99),
                OCRToken(text="Sun", bbox=BoundingBox(x=360, y=230, width=40, height=20), confidence=0.97),
                OCRToken(text="14°20'", bbox=BoundingBox(x=360, y=250, width=50, height=20), confidence=0.95),
                OCRToken(text="Ashwini", bbox=BoundingBox(x=360, y=270, width=60, height=20), confidence=0.94),
                OCRToken(text="Pada 2", bbox=BoundingBox(x=360, y=290, width=50, height=20), confidence=0.94),
                OCRToken(text="Moon", bbox=BoundingBox(x=200, y=180, width=40, height=20), confidence=0.96),
                OCRToken(text="2", bbox=BoundingBox(x=200, y=200, width=20, height=20), confidence=0.98),
                OCRToken(text="05°10'", bbox=BoundingBox(x=200, y=220, width=50, height=20), confidence=0.95),
                OCRToken(text="Krittika", bbox=BoundingBox(x=200, y=240, width=60, height=20), confidence=0.93),
                OCRToken(text="Pada 1", bbox=BoundingBox(x=200, y=260, width=50, height=20), confidence=0.93),
            ]
            full_text = "Lagna Kundli Asc 1 Sun 14°20' Ashwini Pada 2 Moon 2 05°10' Krittika Pada 1"

        return OCRResult(
            full_text=full_text,
            tokens=tokens,
            lines=full_text.splitlines(),
            detected_language="en",
            provider_name="mock_ocr",
            overall_confidence=0.96,
        )
