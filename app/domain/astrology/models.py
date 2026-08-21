from pydantic import BaseModel, Field


class DerivedFactor(BaseModel):
    source: str = Field(
        ..., description="Source type, e.g., 'natal_placement', 'aspect', etc."
    )
    calculation: str = Field(..., description="Raw mathematical/positional details")
    methodology: str = Field(..., description="The astrological rule or method applied")
    strength: float = Field(
        ..., ge=0.0, le=1.0, description="Aspect or placement strength, 0.0 to 1.0"
    )
    timeframe: str = Field(
        ..., description="Applicability window, e.g., 'natal', or transit bounds"
    )
    engine_version: str = Field(
        ..., description="Version of the engine used to derive this factor"
    )


class PlanetPlacement(BaseModel):
    name: str
    longitude: float
    latitude: float
    speed: float
    is_retrograde: bool
    sign: str
    sign_degree: float
    house: int


class HousePlacement(BaseModel):
    number: int
    cusp: float
    sign: str
    sign_degree: float


class Aspect(BaseModel):
    point1: str
    point2: str
    aspect_type: str  # conjunction, sextile, square, trine, opposition
    angle: float
    exact_angle: float
    orb: float
    strength: float  # 1.0 (exact) down to 0.0 (at maximum orb limit)


class WesternChart(BaseModel):
    placements: list[PlanetPlacement]
    houses: list[HousePlacement]
    ascendant: float
    mc: float
    aspects: list[Aspect]
    derived_factors: list[DerivedFactor]
