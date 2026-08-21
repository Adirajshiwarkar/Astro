import uuid
from datetime import date, datetime, time
from typing import Any, Optional

from pydantic import BaseModel, Field


class BirthDataCreate(BaseModel):
    date_of_birth: date = Field(..., description="Date of birth (YYYY-MM-DD)")
    birth_time: time = Field(..., description="Exact local time of birth (HH:MM:SS)")
    birth_place: str = Field(..., description="City or location of birth")
    latitude: Optional[float] = Field(
        None, ge=-90.0, le=90.0, description="Latitude of birth location (auto-calculated if omitted)"
    )
    longitude: Optional[float] = Field(
        None, ge=-180.0, le=180.0, description="Longitude of birth location (auto-calculated if omitted)"
    )
    timezone: str = Field("UTC", description="Timezone name (e.g., 'Asia/Kolkata', 'America/New_York')")
    dst_handling: bool = Field(
        False, description="Whether Daylight Saving Time was in effect"
    )
    timezone_source: str = Field("manual", description="Source of timezone information")
    coordinate_source: str = Field(
        "manual", description="Source of coordinates information"
    )
    calculation_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional extra calculation metadata"
    )


class BirthDataResponse(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    date_of_birth: date
    birth_time: time
    birth_place: str
    latitude: float
    longitude: float
    timezone: str
    dst_handling: bool
    timezone_source: str
    coordinate_source: str
    normalized_birth_datetime: datetime
    calculation_metadata: dict[str, Any]

    class Config:
        from_attributes = True
