import logging

logger = logging.getLogger("app.services.redis")


class RedisServiceStub:
    """Stub class for Redis as vector search and state management now exclusively use Qdrant."""

    def __init__(self) -> None:
        self.client = None

    async def connect(self) -> None:
        logger.info("Redis is disabled. System relies exclusively on Qdrant Vector DB.")

    async def disconnect(self) -> None:
        pass

    async def ping(self) -> bool:
        return True


redis_service = RedisServiceStub()


async def get_redis() -> RedisServiceStub:
    return redis_service
