import uuid
from datetime import date, datetime, time
from typing import Any
from pydantic import BaseModel, Field

from app.schemas.birth_data import BirthDataCreate


class ChartCalculationRequest(BaseModel):
    system: str = Field(
        ..., description="Astrological system (e.g., 'Western', 'Vedic', 'Numerology')"
    )
    birth_data: BirthDataCreate = Field(..., description="Birth parameters for calculation")


class ChartCalculationResponse(BaseModel):
    chart_id: uuid.UUID
    system: str
    calculation_datetime: datetime
    placements: dict[str, Any]
    validation_status: dict[str, Any]


class ChartValidationRequest(BaseModel):
    date_of_birth: date = Field(..., description="Date of birth")
    birth_time: time = Field(..., description="Local time of birth")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude")
    timezone: str = Field(..., description="IANA timezone name")


class ChartValidationResponse(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class ChartGetResponse(BaseModel):
    chart_id: uuid.UUID
    system: str
    birth_data: dict[str, Any]
    placements: dict[str, Any]
    created_at: datetime
