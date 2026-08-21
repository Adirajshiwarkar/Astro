import uuid

from pydantic import BaseModel, Field

from app.schemas.birth_data import BirthDataResponse


class ProfileUpdate(BaseModel):
    first_name: str | None = Field(
        None, max_length=100, description="User's first name"
    )
    last_name: str | None = Field(None, max_length=100, description="User's last name")
    current_location: str | None = Field(
        None, max_length=255, description="Separate current location of the user"
    )


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    first_name: str | None
    last_name: str | None
    current_location: str | None
    birth_data: BirthDataResponse | None

    class Config:
        from_attributes = True
