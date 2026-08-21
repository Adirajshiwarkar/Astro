import datetime
import logging
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.deps import get_current_user
from app.db.models import BirthData, User
from app.db.session import get_db_session
from app.schemas.birth_data import BirthDataCreate, BirthDataResponse
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.astrology.geocoder import geocode_location, resolve_timezone_name

router = APIRouter()
logger = logging.getLogger("app.api.profile")


@router.get("", response_model=ProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)) -> Any:
    logger.info(f"Fetching profile for user: {current_user.id}")
    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found for this user",
        )
    return current_user.profile


@router.put("", response_model=ProfileResponse)
async def update_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_session),
) -> Any:
    logger.info(f"Updating profile for user: {current_user.id}")
    profile = current_user.profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found for this user",
        )

    # Update profile fields
    if profile_in.first_name is not None:
        profile.first_name = profile_in.first_name
    if profile_in.last_name is not None:
        profile.last_name = profile_in.last_name
    if profile_in.current_location is not None:
        profile.current_location = profile_in.current_location

    # Save to 'user_profiles' collection
    await db.user_profiles.replace_one(
        {"_id": str(profile.id)},
        profile.to_dict(include_nested=False)
    )

    return profile


@router.post("/birth-data", response_model=BirthDataResponse)
@router.put("/birth-data", response_model=BirthDataResponse)
async def create_or_update_birth_data(
    birth_data_in: BirthDataCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_session),
) -> Any:
    logger.info(f"Setting birth data for user ID: '{current_user.id}' | Place: '{birth_data_in.birth_place}'")
    profile = current_user.profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found for this user",
        )

    # Automatically resolve latitude and longitude based on the birth place if not provided
    final_lat = birth_data_in.latitude
    final_lon = birth_data_in.longitude

    if final_lat is None or final_lon is None or (final_lat == 0.0 and final_lon == 0.0):
        geo_lat, geo_lon = geocode_location(birth_data_in.birth_place)
        if geo_lat is not None and geo_lon is not None:
            final_lat = geo_lat
            final_lon = geo_lon
        else:
            final_lat = final_lat or 0.0
            final_lon = final_lon or 0.0

    logger.info(f"Resolved coordinates for '{birth_data_in.birth_place}': Latitude={final_lat}, Longitude={final_lon}")

    local_dt = datetime.datetime.combine(
        birth_data_in.date_of_birth, birth_data_in.birth_time
    )
    # Resolve valid IANA timezone dynamically
    resolved_tz = resolve_timezone_name(birth_data_in.timezone or birth_data_in.birth_place)
    try:
        aware_dt = local_dt.replace(tzinfo=ZoneInfo(resolved_tz))
        normalized_dt = aware_dt.astimezone(datetime.UTC)
    except Exception as e:
        logger.warning(
            f"Timezone normalization fallback to UTC for '{birth_data_in.timezone}': {e}"
        )
        normalized_dt = local_dt.replace(tzinfo=datetime.UTC)

    # Prepare calculation metadata
    calc_meta = {
        "original_local_datetime": local_dt.isoformat(),
        "input_timezone": birth_data_in.timezone,
        "input_dst_handling": birth_data_in.dst_handling,
        "timezone_source": birth_data_in.timezone_source,
        "coordinate_source": birth_data_in.coordinate_source if (birth_data_in.latitude and birth_data_in.longitude) else "geocoder",
        "calculation_timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    if birth_data_in.calculation_metadata:
        calc_meta.update(birth_data_in.calculation_metadata)

    birth_data = profile.birth_data
    if birth_data:
        # Update existing birth data
        birth_data.date_of_birth = birth_data_in.date_of_birth
        birth_data.birth_time = birth_data_in.birth_time
        birth_data.birth_place = birth_data_in.birth_place
        birth_data.latitude = final_lat
        birth_data.longitude = final_lon
        birth_data.timezone = birth_data_in.timezone
        birth_data.dst_handling = birth_data_in.dst_handling
        birth_data.timezone_source = birth_data_in.timezone_source
        birth_data.coordinate_source = calc_meta["coordinate_source"]
        birth_data.normalized_birth_datetime = normalized_dt
        birth_data.calculation_metadata = calc_meta
    else:
        # Create new birth data
        birth_data = BirthData(
            profile_id=profile.id,
            date_of_birth=birth_data_in.date_of_birth,
            birth_time=birth_data_in.birth_time,
            birth_place=birth_data_in.birth_place,
            latitude=final_lat,
            longitude=final_lon,
            timezone=birth_data_in.timezone,
            dst_handling=birth_data_in.dst_handling,
            timezone_source=birth_data_in.timezone_source,
            coordinate_source=calc_meta["coordinate_source"],
            normalized_birth_datetime=normalized_dt,
            calculation_metadata=calc_meta,
        )
        profile.birth_data = birth_data

    # Save to 'birth_data' collection
    await db.birth_data.replace_one(
        {"_id": str(birth_data.id)},
        birth_data.to_dict(),
        upsert=True
    )

    return birth_data
