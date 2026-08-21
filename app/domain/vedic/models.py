import datetime
from typing import Any

from pydantic import BaseModel, Field


class VedicCalculationMetadata(BaseModel):
    methodology: str = Field(
        ..., description="Explanation of Vedic calculation system and formulas used"
    )
    ayanamsa: str = Field(
        ..., description="The ayanamsa used for astronomical correction"
    )
    calculation_timestamp: str = Field(
        ..., description="ISO timestamp of when this calculation was run"
    )
    engine_version: str = Field(
        ..., description="Version of the Vedic calculation engine"
    )
    source_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata about the source system/provider"
    )


class GrahaPlacement(BaseModel):
    vedic_name: str
    western_name: str
    longitude: float
    latitude: float
    speed: float
    is_retrograde: bool
    rashi: str  # e.g., Mesha, Vrishabha
    rashi_degree: float
    bhava: int  # House 1 to 12
    nakshatra: str  # e.g., Ashwini, Bharani
    nakshatra_pada: int  # Pada 1 to 4


class BhavaPlacement(BaseModel):
    number: int
    cusp: float
    rashi: str
    rashi_degree: float


class VedicAspect(BaseModel):
    aspecting_graha: str
    aspected_point: str  # Graha name or Bhava number
    house_distance: int
    aspect_type: str  # e.g. "7th house aspect", "special Mars aspect"


class AntardashaPeriod(BaseModel):
    lord: str
    duration_years: float
    start_date: str
    end_date: str


class MahadashaPeriod(BaseModel):
    lord: str
    duration_years: float
    start_date: str
    end_date: str
    antardashas: list[AntardashaPeriod]


class VedicTransitPlacement(BaseModel):
    graha_name: str
    transit_sign: str
    house_from_chandra: int
    transit_longitude: float


class VedicChart(BaseModel):
    lagna: str  # Lagna Sign
    lagna_degree: float
    grahas: list[GrahaPlacement]
    bhavas: list[BhavaPlacement]
    aspects: list[VedicAspect]
    vimshottari_dasha: list[MahadashaPeriod]
    metadata: VedicCalculationMetadata
