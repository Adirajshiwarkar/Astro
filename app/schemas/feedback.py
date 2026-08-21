import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    item_type: str = Field(
        ..., description="Type of item being rated: prediction, chat_message, chart"
    )
    item_id: uuid.UUID = Field(..., description="ID of the item")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: str | None = Field(None, description="Optional textual feedback")


class FeedbackResponse(BaseModel):
    feedback_id: uuid.UUID
    item_type: str
    item_id: uuid.UUID
    rating: int
    comment: str | None
    created_at: datetime
