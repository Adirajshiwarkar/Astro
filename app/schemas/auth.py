import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ..., min_length=8, description="User's password (min 8 chars)"
    )


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type, usually bearer")


class TokenRefresh(BaseModel):
    refresh_token: str = Field(..., description="Valid JWT refresh token")


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
