import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    conversation_id: uuid.UUID | None = Field(
        None, description="Conversation ID to append the message to"
    )
    message: str = Field(..., description="User message content")
    system_preference: str | None = Field(
        None, description="System preference: Western, Vedic, Numerology"
    )


class ChatMessageResponse(BaseModel):
    conversation_id: uuid.UUID
    response_message: str
    context_package: dict[str, Any] | None = Field(
        None, description="Assembled context package used for prompt"
    )
    created_at: datetime


class ConversationMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message text content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationResponse(BaseModel):
    conversation_id: uuid.UUID
    title: str
    created_at: datetime
    messages: list[ConversationMessage]


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
    limit: int
    offset: int
