import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.db.models import User, UserProfile
from app.db.session import get_db_session
from app.schemas.auth import Token, TokenRefresh, UserRegister, UserResponse

router = APIRouter()
logger = logging.getLogger("app.api.auth")


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_in: UserRegister, db: AsyncIOMotorDatabase = Depends(get_db_session)
) -> Any:
    logger.info(f"[AUTH REGISTRATION ATTEMPT] Email: '{user_in.email}'")

    # Check if user already exists
    existing_user_data = await db.users.find_one({"email": user_in.email})

    if existing_user_data:
        logger.warning(
            f"[AUTH REGISTRATION FAILED] User with email '{user_in.email}' already exists"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    # Hash the password and create the user
    hashed_password = get_password_hash(user_in.password)
    new_user = User(email=user_in.email, hashed_password=hashed_password)
    
    # Save user to 'users' collection (without nested profile)
    await db.users.insert_one(new_user.to_dict(include_nested=False))

    # Automatically create the profile for the user in 'user_profiles' collection
    new_profile = UserProfile(user_id=new_user.id)
    await db.user_profiles.insert_one(new_profile.to_dict(include_nested=False))
    
    new_user.profile = new_profile

    logger.info(f"[AUTH REGISTRATION SUCCESS] User ID: '{new_user.id}' | Email: '{new_user.email}'")
    return new_user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db_session),
) -> Any:
    content_type = request.headers.get("content-type", "")
    email = None
    password = None

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form_data = await request.form()
        email = form_data.get("username") or form_data.get("email")
        password = form_data.get("password")
    else:
        try:
            body = await request.json()
            if isinstance(body, dict):
                email = body.get("email") or body.get("username")
                password = body.get("password")
        except Exception:
            pass

    if not email or not password:
        logger.warning("[AUTH LOGIN FAILED] Missing email/username or password in request body")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email/username and password are required",
        )

    logger.info(f"[AUTH LOGIN ATTEMPT] Email: '{email}'")

    user_data = await db.users.find_one({"email": email})

    if not user_data:
        logger.warning(f"[AUTH LOGIN FAILED] User not found for email: '{email}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    if not verify_password(password, user_data.get("hashed_password")):
        logger.warning(f"[AUTH LOGIN FAILED] Invalid password for user email: '{email}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    user = User.from_dict(user_data)

    if not user.is_active:
        logger.warning(f"[AUTH LOGIN FAILED] Inactive user login attempt for ID: '{user.id}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # Create access and refresh tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    logger.info(f"[AUTH LOGIN SUCCESS] User ID: '{user.id}' | Email: '{user.email}'")
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh(refresh_in: TokenRefresh) -> Any:
    logger.info("[AUTH REFRESH ATTEMPT] Refreshing access token")

    user_id_str = verify_token(refresh_in.refresh_token, token_type="refresh")
    if not user_id_str:
        logger.warning("[AUTH REFRESH FAILED] Invalid or expired refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Generate new tokens
    access_token = create_access_token(subject=user_id_str)
    new_refresh_token = create_refresh_token(subject=user_id_str)

    logger.info(f"[AUTH REFRESH SUCCESS] Tokens refreshed for User ID: '{user_id_str}'")
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)) -> Any:
    logger.info(
        f"[AUTH LOGOUT SUCCESS] User ID: '{current_user.id}' | Email: '{current_user.email}' logged out successfully."
    )
    return {"message": "Successfully logged out"}
