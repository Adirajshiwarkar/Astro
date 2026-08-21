from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.services.qdrant import qdrant_service
from app.services.redis import redis_service


@pytest.mark.asyncio
async def test_health_success(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert data["database"]["status"] == "healthy"
    assert data["redis"]["status"] == "healthy"
    assert data["qdrant"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_db_failure(client: AsyncClient, mock_db: AsyncMock) -> None:
    # Force the database query to fail
    mock_db.execute.side_effect = Exception("Database connection error")

    response = await client.get("/api/v1/health")
    assert response.status_code == 503

    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"]["status"] == "unhealthy"
    assert "Database connection error" in data["database"]["details"]
    assert data["redis"]["status"] == "healthy"
    assert data["qdrant"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_redis_failure(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force Redis to fail
    monkeypatch.setattr(redis_service, "ping", AsyncMock(return_value=False))

    response = await client.get("/api/v1/health")
    assert response.status_code == 503

    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"]["status"] == "healthy"
    assert data["redis"]["status"] == "unhealthy"
    assert data["redis"]["details"] == "Connection failed"
    assert data["qdrant"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_qdrant_failure(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force Qdrant to fail
    monkeypatch.setattr(qdrant_service, "ping", AsyncMock(return_value=False))

    response = await client.get("/api/v1/health")
    assert response.status_code == 503

    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"]["status"] == "healthy"
    assert data["redis"]["status"] == "healthy"
    assert data["qdrant"]["status"] == "unhealthy"
    assert data["qdrant"]["details"] == "Connection failed"
