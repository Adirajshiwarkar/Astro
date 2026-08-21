from enum import Enum
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ChartType(str, Enum):
    NORTH_INDIAN = "north_indian"  # Diamond / Rhombus style
    SOUTH_INDIAN = "south_indian"  # Fixed 12-box square perimeter
    EAST_INDIAN = "east_indian"    # Bengali / Odia quadrant format
    WESTERN_CIRCULAR = "western_circular"  # 360-degree radial wheel
    TABLE_REPORT = "table_report"  # Tabular text Kundli printout
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    x: float = Field(..., description="Top-left X coordinate (pixels or normalized 0.0-1.0)")
    y: float = Field(..., description="Top-left Y coordinate (pixels or normalized 0.0-1.0)")
    width: float = Field(..., description="Box width")
    height: float = Field(..., description="Box height")


class SourceRegion(BaseModel):
    bbox: BoundingBox | None = None
    polygon: list[list[float]] | None = None
    page_number: int = 1
    section_name: str | None = None


class ExtractedField(BaseModel, Generic[T]):
    value: T = Field(..., description="Extracted typed value")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0"
    )
    source_region: SourceRegion | None = Field(
        default=None, description="Spatial coordinates where field was extracted"
    )
    extraction_method: str = Field(
        ..., description="Method used: ocr_text, vision_geometry, table_cell_parser, rule_inference, etc."
    )


class ExtractedPlanetPlacement(BaseModel):
    planet: ExtractedField[str] = Field(..., description="Standardized planet name")
    sign: ExtractedField[str] | None = None
    sign_number: ExtractedField[int] | None = None
    house: ExtractedField[int] | None = None
    degree: ExtractedField[float] | None = None
    degree_dms: ExtractedField[str] | None = None
    nakshatra: ExtractedField[str] | None = None
    pada: ExtractedField[int] | None = None
    is_retrograde: ExtractedField[bool] | None = None
    is_combust: ExtractedField[bool] | None = None


class ExtractedHousePlacement(BaseModel):
    house_number: ExtractedField[int] = Field(..., description="House index 1 to 12")
    sign: ExtractedField[str] | None = None
    sign_number: ExtractedField[int] | None = None
    occupants: list[ExtractedField[str]] = Field(
        default_factory=list, description="Planets situated within this house"
    )
    cusp_degree: ExtractedField[float] | None = None


class ExtractedAscendant(BaseModel):
    sign: ExtractedField[str] = Field(..., description="Ascendant / Lagna sign name")
    sign_number: ExtractedField[int] | None = None
    degree: ExtractedField[float] | None = None
    nakshatra: ExtractedField[str] | None = None
    pada: ExtractedField[int] | None = None


class ExtractedDashaPeriod(BaseModel):
    lord: ExtractedField[str]
    start_date: ExtractedField[str] | None = None
    end_date: ExtractedField[str] | None = None
    duration_years: ExtractedField[float] | None = None


class ExtractedDashaInfo(BaseModel):
    current_mahadasha: ExtractedField[str] | None = None
    current_antardasha: ExtractedField[str] | None = None
    balance_at_birth: ExtractedField[str] | None = None
    dasha_periods: list[ExtractedDashaPeriod] = Field(default_factory=list)


class ExtractedChartMetadata(BaseModel):
    chart_title: ExtractedField[str] | None = None
    native_name: ExtractedField[str] | None = None
    birth_date: ExtractedField[str] | None = None
    birth_time: ExtractedField[str] | None = None
    birth_place: ExtractedField[str] | None = None
    ayanamsa: ExtractedField[str] | None = None
    latitude: ExtractedField[str] | None = None
    longitude: ExtractedField[str] | None = None
    timezone: ExtractedField[str] | None = None


class StructuredChartRepresentation(BaseModel):
    chart_type: ExtractedField[ChartType] = Field(
        ..., description="Detected astrological chart typology"
    )
    ascendant: ExtractedAscendant | None = None
    planets: list[ExtractedPlanetPlacement] = Field(default_factory=list)
    houses: list[ExtractedHousePlacement] = Field(default_factory=list)
    dasha: ExtractedDashaInfo | None = None
    metadata: ExtractedChartMetadata = Field(default_factory=ExtractedChartMetadata)
    chart_labels: list[ExtractedField[str]] = Field(default_factory=list)
    raw_ocr_tokens: list[dict[str, Any]] = Field(default_factory=list)
    overall_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregated confidence metric"
    )
    validation_summary: dict[str, Any] = Field(
        default_factory=dict, description="Astrological consistency checks output"
    )
    engine_version: str = Field(
        default="1.0.0", description="Image intelligence subsystem version"
    )
