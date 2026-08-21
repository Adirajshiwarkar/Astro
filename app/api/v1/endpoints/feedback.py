import datetime
import logging
import uuid
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.deps import get_current_user
from app.db.session import get_db_session
from app.db.models import User
from app.schemas.feedback import FeedbackRequest, FeedbackResponse

router = APIRouter()
logger = logging.getLogger("app.api.feedback")


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_session),
) -> FeedbackResponse:
    """Submit user rating and textual feedback for predictions, chat messages, or charts."""
    logger.info(
        f"Feedback submitted by user {current_user.id} for item {request.item_id} "
        f"({request.item_type}): rating={request.rating}"
    )

    # In a full production system, we would insert this into a feedbacks table.
    # Here we mock the DB insertion and return the generated record.
    return FeedbackResponse(
        feedback_id=uuid.uuid4(),
        item_type=request.item_type,
        item_id=request.item_id,
        rating=request.rating,
        comment=request.comment,
        created_at=datetime.datetime.now(datetime.UTC),
    )
