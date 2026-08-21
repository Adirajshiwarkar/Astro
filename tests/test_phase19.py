import uuid
from datetime import UTC, date, datetime, time
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.models import BirthData, User, UserProfile


@pytest.fixture
def test_user() -> User:
    user = User(
        id=uuid.UUID("2d3cea6d-59ea-4275-b1d8-be17fcad0c2d"),
        email="phase19@example.com",
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
    # Add birth data so calculation engine has coordinates
    birth_data = BirthData(
        id=uuid.uuid4(),
        profile_id=profile.id,
        date_of_birth=date(1990, 1, 1),
        birth_time=time(12, 0, 0),
        birth_place="New York, NY",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
        dst_handling=False,
        timezone_source="manual",
        coordinate_source="manual",
        normalized_birth_datetime=datetime(1990, 1, 1, 17, 0, 0, tzinfo=UTC),
        calculation_metadata={},
        created_at=datetime.now(UTC),
    )
    profile.birth_data = birth_data
    user.profile = profile
    return user


@pytest.mark.asyncio
async def test_health_and_readiness_endpoints(app: FastAPI) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        res_health = await ac.get("/api/v1/health")
        assert res_health.status_code in [200, 503]

        res_readiness = await ac.get("/api/v1/readiness")
        assert res_readiness.status_code in [200, 503]


@pytest.mark.asyncio
async def test_profile_birth_data_put(
    app: FastAPI, mock_db: AsyncMock, test_user: User
) -> None:
    mock_db.execute.return_value.scalar_one_or_none.return_value = test_user
    token = create_access_token(subject=test_user.id)

    payload = {
        "date_of_birth": "1990-01-01",
        "birth_time": "12:00:00",
        "birth_place": "New York, NY",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone": "America/New_York",
        "dst_handling": False,
        "timezone_source": "manual",
        "coordinate_source": "manual",
        "calculation_metadata": {},
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.put(
            "/api/v1/profile/birth-data",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["birth_place"] == "New York, NY"
    assert data["latitude"] == 40.7128
    assert data["longitude"] == -74.0060


@pytest.mark.asyncio
async def test_charts_endpoints(
    app: FastAPI, mock_db: AsyncMock, test_user: User
) -> None:
    mock_db.execute.return_value.scalar_one_or_none.return_value = test_user
    token = create_access_token(subject=test_user.id)

    # 1. Calculate Chart
    calc_payload = {
        "system": "Western",
        "birth_data": {
            "date_of_birth": "1990-01-01",
            "birth_time": "12:00:00",
            "birth_place": "New York, NY",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "timezone": "America/New_York",
            "dst_handling": False,
            "timezone_source": "manual",
            "coordinate_source": "manual",
            "calculation_metadata": {},
        },
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        res_calc = await ac.post(
            "/api/v1/charts/calculate",
            headers={"Authorization": f"Bearer {token}"},
            json=calc_payload,
        )
        assert res_calc.status_code == 200
        data_calc = res_calc.json()
        assert data_calc["system"] == "Western"
        assert "placements" in data_calc
        assert "sun" in data_calc["placements"]

        # 2. Validate Input
        val_payload = {
            "date_of_birth": "1990-01-01",
            "birth_time": "12:00:00",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "timezone": "America/New_York",
        }
        res_val = await ac.post(
            "/api/v1/charts/validate",
            headers={"Authorization": f"Bearer {token}"},
            json=val_payload,
        )
        assert res_val.status_code == 200
        data_val = res_val.json()
        assert data_val["is_valid"] is True
        assert len(data_val["errors"]) == 0

        # 3. Get Chart by ID
        chart_id = uuid.uuid4()
        res_get = await ac.get(
            f"/api/v1/charts/{chart_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_get.status_code == 200
        data_get = res_get.json()
        assert str(data_get["chart_id"]) == str(chart_id)
        assert "placements" in data_get


@pytest.mark.asyncio
async def test_predictions_endpoints(
    app: FastAPI, mock_db: AsyncMock, test_user: User
) -> None:
    mock_db.execute.return_value.scalar_one_or_none.return_value = test_user
    token = create_access_token(subject=test_user.id)

    pred_payload = {
        "system": "Western",
        "timeframe": "monthly",
        "birth_data": {
            "date_of_birth": "1990-01-01",
            "birth_time": "12:00:00",
            "birth_place": "New York, NY",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "timezone": "America/New_York",
            "dst_handling": False,
            "timezone_source": "manual",
            "coordinate_source": "manual",
            "calculation_metadata": {},
        },
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        # POST predictions
        res_post = await ac.post(
            "/api/v1/predictions",
            headers={"Authorization": f"Bearer {token}"},
            json=pred_payload,
        )
        assert res_post.status_code == 200
        data_post = res_post.json()
        assert data_post["system"] == "Western"
        assert "timeline" in data_post
        assert "scenarios" in data_post

        # GET predictions/{id}
        pred_id = uuid.uuid4()
        res_get = await ac.get(
            f"/api/v1/predictions/{pred_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_get.status_code == 200
        data_get = res_get.json()
        assert str(data_get["prediction_id"]) == str(pred_id)


@pytest.mark.asyncio
async def test_chat_and_conversations_endpoints(
    app: FastAPI, mock_db: AsyncMock, test_user: User
) -> None:
    mock_db.execute.return_value.scalar_one_or_none.return_value = test_user
    token = create_access_token(subject=test_user.id)

    chat_payload = {
        "conversation_id": None,
        "message": "What is my Sun transit career impact?",
        "system_preference": "Western",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        # 1. Chat
        res_chat = await ac.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json=chat_payload,
        )
        assert res_chat.status_code == 200
        data_chat = res_chat.json()
        assert "response_message" in data_chat
        assert "conversation_id" in data_chat

        # 2. Conversations
        res_convs = await ac.get(
            "/api/v1/conversations?limit=5&offset=0",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_convs.status_code == 200
        data_convs = res_convs.json()
        assert "conversations" in data_convs
        assert data_convs["limit"] == 5
        assert data_convs["offset"] == 0
        assert data_convs["total"] >= 1


@pytest.mark.asyncio
async def test_feedback_endpoint(
    app: FastAPI, mock_db: AsyncMock, test_user: User
) -> None:
    mock_db.execute.return_value.scalar_one_or_none.return_value = test_user
    token = create_access_token(subject=test_user.id)

    feedback_payload = {
        "item_type": "prediction",
        "item_id": str(uuid.uuid4()),
        "rating": 5,
        "comment": "Incredibly accurate prediction!",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.post(
            "/api/v1/feedback",
            headers={"Authorization": f"Bearer {token}"},
            json=feedback_payload,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["item_type"] == "prediction"
    assert data["rating"] == 5
    assert data["comment"] == "Incredibly accurate prediction!"
