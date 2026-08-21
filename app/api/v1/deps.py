import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import verify_token
from app.db.models import User, UserProfile, BirthData
from app.db.session import get_db_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_db_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id_str = verify_token(token, token_type="access")
    if not user_id_str:
        raise credentials_exception

    user_data = await db.users.find_one({"_id": user_id_str})
    if user_data is None:
        user_data = await db.users.find_one({"id": user_id_str})

    user = User.from_dict(user_data) if user_data and isinstance(user_data, dict) else None
    if not user:
        raise credentials_exception

    # Fetch and attach profile from user_profiles collection
    profile_data = await db.user_profiles.find_one({"user_id": user_id_str})
    if profile_data and isinstance(profile_data, dict):
        profile = UserProfile.from_dict(profile_data)
        if profile and profile.id:
            # Fetch and attach birth data from birth_data collection
            birth_data_data = await db.birth_data.find_one({"profile_id": str(profile.id)})
            if birth_data_data and isinstance(birth_data_data, dict):
                profile.birth_data = BirthData.from_dict(birth_data_data)
            user.profile = profile

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    return user
