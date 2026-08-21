from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field

from app.domain.image_intelligence.models import BoundingBox, ChartType


class LayoutRegion(BaseModel):
    region_type: str = Field(..., description="E.g., house_cell, table_row, wheel_sector, chart_title")
    identifier: str | int | None = Field(default=None, description="House index, sign number, or section tag")
    bbox: BoundingBox
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    contained_tokens: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisionLayoutResult(BaseModel):
    detected_chart_type: ChartType = ChartType.UNKNOWN
    chart_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    regions: list[LayoutRegion] = Field(default_factory=list)
    geometry_detected: dict[str, Any] = Field(default_factory=dict)
    provider_name: str = "base"


class OCRToken(BaseModel):
    text: str
    bbox: BoundingBox | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    line_number: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OCRResult(BaseModel):
    full_text: str
    tokens: list[OCRToken] = Field(default_factory=list)
    lines: list[str] = Field(default_factory=list)
    detected_language: str = "en"
    provider_name: str = "base"
    overall_confidence: float = 1.0


class VisionProvider(ABC):
    """Abstract interface for astrological chart layout and visual geometry detectors."""

    @abstractmethod
    async def analyze_layout(
        self, image_bytes: bytes, dimensions: tuple[int, int]
    ) -> VisionLayoutResult:
        """Analyze image geometry, detect chart topologies, house cells, and visual regions."""
        pass


class OCRProvider(ABC):
    """Abstract interface for optical character recognition providers."""

    @abstractmethod
    async def extract_text(
        self, image_bytes: bytes, dimensions: tuple[int, int]
    ) -> OCRResult:
        """Extract textual content, individual word/symbol tokens, and bounding boxes."""
        pass
