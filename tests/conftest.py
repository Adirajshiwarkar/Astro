from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db_session
from app.services.qdrant import qdrant_service
from app.services.redis import redis_service


@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock RedisService connect, disconnect, ping
    monkeypatch.setattr(redis_service, "connect", AsyncMock())
    monkeypatch.setattr(redis_service, "disconnect", AsyncMock())
    monkeypatch.setattr(redis_service, "ping", AsyncMock(return_value=True))

    # Mock QdrantService connect, disconnect, ping
    monkeypatch.setattr(qdrant_service, "connect", AsyncMock())
    monkeypatch.setattr(qdrant_service, "disconnect", AsyncMock())
    monkeypatch.setattr(qdrant_service, "ping", AsyncMock(return_value=True))


@pytest.fixture
def mock_db() -> AsyncMock:
    import datetime
    import uuid
    from typing import Any
    from unittest.mock import AsyncMock, MagicMock

    async def refresh_side_effect(instance: Any, *_args: Any, **_kwargs: Any) -> None:
        if hasattr(instance, "id") and instance.id is None:
            instance.id = uuid.uuid4()
        if hasattr(instance, "is_active") and instance.is_active is None:
            instance.is_active = True
        if hasattr(instance, "created_at") and instance.created_at is None:
            instance.created_at = datetime.datetime.now(datetime.UTC)
        if hasattr(instance, "updated_at") and instance.updated_at is None:
            instance.updated_at = datetime.datetime.now(datetime.UTC)

    db = AsyncMock()
    db.execute = AsyncMock()
    db.execute.return_value = MagicMock()
    db.refresh = AsyncMock(side_effect=refresh_side_effect)
    return db


@pytest.fixture
def app() -> FastAPI:
    from app.main import app as main_app

    return main_app


@pytest.fixture(autouse=True)
def override_db_dependency(
    app: FastAPI, mock_db: AsyncMock
) -> Generator[None, None, None]:
    app.dependency_overrides[get_db_session] = lambda: mock_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac
