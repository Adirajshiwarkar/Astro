import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.security import get_password_hash
from app.db.models import User


@pytest.fixture
def test_user() -> User:
    hashed = get_password_hash("password123")
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password=hashed,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_register_success(app: FastAPI, mock_db: AsyncMock) -> None:
    # Mock database flow for registration:
    # 1. Select user by email returns None (doesn't exist yet)
    # 2. Add, flush, commit, refresh
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.post(
            "/api/v1/auth/register",
            json={"email": "newuser@example.com", "password": "securepassword123"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate(
    app: FastAPI, mock_db: AsyncMock, test_user: User
) -> None:
    mock_db.execute.return_value.scalar_one_or_none.return_value = test_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "A user with this email already exists"


@pytest.mark.asyncio
async def test_login_success(app: FastAPI, mock_db: AsyncMock, test_user: User) -> None:
    mock_db.execute.return_value.scalar_one_or_none.return_value = test_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(
    app: FastAPI, mock_db: AsyncMock, test_user: User
) -> None:
    mock_db.execute.return_value.scalar_one_or_none.return_value = test_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_refresh_token_success(app: FastAPI, test_user: User) -> None:
    from app.core.security import create_refresh_token

    ref_token = create_refresh_token(subject=test_user.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": ref_token},
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid(app: FastAPI) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalidtokenvalue"},
        )

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid refresh token"
