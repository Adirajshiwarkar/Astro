import uuid
from datetime import UTC, date, datetime, time
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.models import BirthData, User, UserProfile


@pytest.fixture
def authenticated_user() -> User:
    user = User(
        id=uuid.uuid4(),
        email="profileuser@example.com",
        hashed_password="hashed_pwd",
        is_active=True,
    )
    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        first_name="Jane",
        last_name="Doe",
        current_location="New York, NY",
    )
    user.profile = profile
    return user


@pytest.mark.asyncio
async def test_get_profile(
    app: FastAPI, mock_db: AsyncMock, authenticated_user: User
) -> None:
    # Setup mock DB query to return the user when fetched by get_current_user dependency
    mock_db.execute.return_value.scalar_one_or_none.return_value = authenticated_user

    # Generate a valid access token for the user
    token = create_access_token(subject=authenticated_user.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.get(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"
    assert data["current_location"] == "New York, NY"
    assert data["birth_data"] is None


@pytest.mark.asyncio
async def test_update_profile(
    app: FastAPI, mock_db: AsyncMock, authenticated_user: User
) -> None:
    mock_db.execute.return_value.scalar_one_or_none.return_value = authenticated_user
    token = create_access_token(subject=authenticated_user.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.put(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "first_name": "Janet",
                "last_name": "Smith",
                "current_location": "San Francisco, CA",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Janet"
    assert data["last_name"] == "Smith"
    assert data["current_location"] == "San Francisco, CA"


@pytest.mark.asyncio
async def test_create_birth_data(
    app: FastAPI, mock_db: AsyncMock, authenticated_user: User
) -> None:
    # User profile has no birth_data initially
    assert authenticated_user.profile.birth_data is None
    mock_db.execute.return_value.scalar_one_or_none.return_value = authenticated_user
    token = create_access_token(subject=authenticated_user.id)

    birth_payload = {
        "date_of_birth": "1990-05-15",
        "birth_time": "14:30:00",
        "birth_place": "Paris, France",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "timezone": "Europe/Paris",
        "dst_handling": True,
        "timezone_source": "manual",
        "coordinate_source": "manual",
        "calculation_metadata": {"method": "swiss_ephemeris"},
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.post(
            "/api/v1/profile/birth-data",
            headers={"Authorization": f"Bearer {token}"},
            json=birth_payload,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["birth_place"] == "Paris, France"
    assert data["latitude"] == 48.8566
    assert data["longitude"] == 2.3522
    assert data["timezone"] == "Europe/Paris"
    assert "normalized_birth_datetime" in data
    assert data["calculation_metadata"]["method"] == "swiss_ephemeris"


@pytest.mark.asyncio
async def test_update_birth_data(
    app: FastAPI, mock_db: AsyncMock, authenticated_user: User
) -> None:
    # Pre-populate birth_data
    birth_data = BirthData(
        id=uuid.uuid4(),
        profile_id=authenticated_user.profile.id,
        date_of_birth=date(1985, 10, 10),
        birth_time=time(8, 0, 0),
        birth_place="London, UK",
        latitude=51.5074,
        longitude=-0.1278,
        timezone="Europe/London",
        dst_handling=False,
        timezone_source="manual",
        coordinate_source="manual",
        normalized_birth_datetime=datetime.now(UTC),
        calculation_metadata={},
    )
    authenticated_user.profile.birth_data = birth_data

    mock_db.execute.return_value.scalar_one_or_none.return_value = authenticated_user
    token = create_access_token(subject=authenticated_user.id)

    update_payload = {
        "date_of_birth": "1985-10-10",
        "birth_time": "09:15:00",  # updated
        "birth_place": "London, UK",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "timezone": "Europe/London",
        "dst_handling": True,  # updated
        "timezone_source": "manual",
        "coordinate_source": "manual",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.post(
            "/api/v1/profile/birth-data",
            headers={"Authorization": f"Bearer {token}"},
            json=update_payload,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["birth_time"] == "09:15:00"
    assert data["dst_handling"] is True
