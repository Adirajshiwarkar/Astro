from unittest.mock import AsyncMock, patch

import pytest
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceUnavailableError
from app.db.session import get_db_session
from app.services.qdrant import get_qdrant, qdrant_service
from app.services.redis import get_redis, redis_service


@pytest.mark.asyncio
async def test_get_db_session() -> None:
    from unittest.mock import MagicMock

    mock_session = AsyncMock(spec=AsyncSession)
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_session
    mock_session_maker = MagicMock(return_value=mock_context)

    with patch("app.db.session.async_session_maker", mock_session_maker):
        session_gen = get_db_session()
        session = await anext(session_gen)
        assert session == mock_session

        # Verify it closes when generator completes
        try:
            await anext(session_gen)
        except StopAsyncIteration:
            pass
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_redis() -> None:
    # 1. Uninitialized should raise ServiceUnavailableError
    with patch.object(redis_service, "client", None):
        with pytest.raises(ServiceUnavailableError) as exc_info:
            await get_redis()
        assert "Redis client is not initialized" in str(exc_info.value)

    # 2. Initialized should return the client
    mock_client = AsyncMock(spec=Redis)
    with patch.object(redis_service, "client", mock_client):
        client = await get_redis()
        assert client == mock_client


@pytest.mark.asyncio
async def test_get_qdrant() -> None:
    # 1. Uninitialized should raise ServiceUnavailableError
    with patch.object(qdrant_service, "client", None):
        with pytest.raises(ServiceUnavailableError) as exc_info:
            await get_qdrant()
        assert "Qdrant client is not initialized" in str(exc_info.value)

    # 2. Initialized should return the client
    mock_client = AsyncMock(spec=AsyncQdrantClient)
    with patch.object(qdrant_service, "client", mock_client):
        client = await get_qdrant()
        assert client == mock_client
