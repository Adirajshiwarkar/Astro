import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from app.schemas.birth_data import BirthDataCreate


class PredictionRequest(BaseModel):
    system: str = Field(
        "Western", description="System filter: Western, Vedic, Numerology"
    )
    timeframe: str = Field("monthly", description="Timeframe partition (monthly, weekly)")
    birth_data: BirthDataCreate = Field(..., description="Birth parameters")


class PredictionResponse(BaseModel):
    prediction_id: uuid.UUID
    system: str
    timeframe: str
    timeline: dict[str, Any]
    scenarios: list[dict[str, Any]]
    created_at: datetime
