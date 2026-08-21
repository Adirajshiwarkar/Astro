from enum import Enum
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ProvenanceMetadata(BaseModel):
    source: str = Field(
        ...,
        description="Source identifier (e.g., 'image_extraction', 'ephemeris_calculation', 'vedic_engine', 'western_engine', 'user_input')",
    )
    method: str = Field(
        ...,
        description="Calculation or extraction method (e.g., 'swiss_ephemeris', 'ocr_vision', 'lahiri_ayanamsa', 'table_cell_parser')",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (1.0 for mathematical ephemeris, dynamic for OCR/vision)",
    )
    engine_version: str = Field(
        default="1.0.0", description="Version of the engine that produced this value"
    )
    calculation_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Astrological configuration (ayanamsa, house_system, zodiac_type, etc.)",
    )
    source_region: dict[str, Any] | None = Field(
        default=None, description="Spatial coordinates if extracted from image"
    )


class CanonicalField(BaseModel, Generic[T]):
    value: T = Field(..., description="The typed field value")
    provenance: ProvenanceMetadata = Field(..., description="Field-level provenance metadata")


class CanonicalPointPlacement(BaseModel):
    name: CanonicalField[str] = Field(..., description="Point name (e.g., 'Ascendant', 'MC')")
    sign: CanonicalField[str] = Field(..., description="Zodiac sign name")
    sign_number: CanonicalField[int] = Field(..., description="Zodiac sign number (1-12)")
    degree: CanonicalField[float] | None = None
    total_longitude: CanonicalField[float] | None = None
    nakshatra: CanonicalField[str] | None = None
    pada: CanonicalField[int] | None = None


class CanonicalPlanetPlacement(BaseModel):
    planet: CanonicalField[str] = Field(..., description="Standardized canonical planet name")
    sign: CanonicalField[str] | None = None
    sign_number: CanonicalField[int] | None = None
    degree: CanonicalField[float] | None = None
    total_longitude: CanonicalField[float] | None = None
    house: CanonicalField[int] | None = None
    nakshatra: CanonicalField[str] | None = None
    pada: CanonicalField[int] | None = None
    is_retrograde: CanonicalField[bool] | None = None
    is_combust: CanonicalField[bool] | None = None
    speed: CanonicalField[float] | None = None


class CanonicalHousePlacement(BaseModel):
    house_number: CanonicalField[int] = Field(..., description="House number 1-12")
    sign: CanonicalField[str] | None = None
    sign_number: CanonicalField[int] | None = None
    cusp_degree: CanonicalField[float] | None = None
    cusp_longitude: CanonicalField[float] | None = None
    occupants: list[CanonicalField[str]] = Field(default_factory=list)


class CanonicalDashaPeriod(BaseModel):
    lord: CanonicalField[str]
    start_date: CanonicalField[str] | None = None
    end_date: CanonicalField[str] | None = None


class CanonicalDashaInfo(BaseModel):
    current_mahadasha: CanonicalField[str] | None = None
    current_antardasha: CanonicalField[str] | None = None
    balance_at_birth: CanonicalField[str] | None = None
    dasha_periods: list[CanonicalDashaPeriod] = Field(default_factory=list)


class CanonicalChartMetadata(BaseModel):
    native_name: CanonicalField[str] | None = None
    birth_date: CanonicalField[str] | None = None
    birth_time: CanonicalField[str] | None = None
    birth_place: CanonicalField[str] | None = None
    chart_title: CanonicalField[str] | None = None
    ayanamsa: CanonicalField[str] | None = None
    latitude: CanonicalField[float] | None = None
    longitude: CanonicalField[float] | None = None


class CanonicalChartRepresentation(BaseModel):
    zodiac_system: str = Field(
        default="sidereal", description="Zodiac system: 'sidereal' or 'tropical'"
    )
    ascendant: CanonicalPointPlacement | None = None
    midheaven: CanonicalPointPlacement | None = None
    planets: dict[str, CanonicalPlanetPlacement] = Field(
        default_factory=dict, description="Planetary placements keyed by canonical name"
    )
    houses: list[CanonicalHousePlacement] = Field(
        default_factory=list, description="12 house placements"
    )
    dasha: CanonicalDashaInfo | None = None
    metadata: CanonicalChartMetadata = Field(default_factory=CanonicalChartMetadata)
    provenance: ProvenanceMetadata = Field(..., description="Overall chart provenance")


class ComparisonStatus(str, Enum):
    MATCH = "MATCH"
    CONFLICT = "CONFLICT"
    MISSING_IN_A = "MISSING_IN_A"
    MISSING_IN_B = "MISSING_IN_B"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class FieldComparison(BaseModel):
    field_name: str
    status: ComparisonStatus
    value_a: Any = None
    provenance_a: ProvenanceMetadata | None = None
    value_b: Any = None
    provenance_b: ProvenanceMetadata | None = None
    diff_details: str | None = None


class ComparisonResult(BaseModel):
    total_compared: int
    matches: int
    conflicts: int
    missing_in_a: int
    missing_in_b: int
    low_confidence_count: int
    match_percentage: float
    field_comparisons: list[FieldComparison] = Field(default_factory=list)


class ValidationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    DISCREPANCIES_FOUND = "DISCREPANCIES_FOUND"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    HIGH_UNCERTAINTY = "HIGH_UNCERTAINTY"


class ValidationReport(BaseModel):
    status: ValidationStatus
    match_percentage: float
    summary: str
    source_a_summary: dict[str, Any]
    source_b_summary: dict[str, Any]
    matching_fields: list[FieldComparison] = Field(default_factory=list)
    conflicts: list[FieldComparison] = Field(default_factory=list)
    missing_fields: list[FieldComparison] = Field(default_factory=list)
    low_confidence_fields: list[FieldComparison] = Field(default_factory=list)
    comparison_result: ComparisonResult
    chart_a: CanonicalChartRepresentation
    chart_b: CanonicalChartRepresentation
