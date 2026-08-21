import logging

from qdrant_client import AsyncQdrantClient

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError

logger = logging.getLogger("app.services.qdrant")


class QdrantService:
    def __init__(self) -> None:
        self.client: AsyncQdrantClient | None = None

    async def connect(self) -> None:
        logger.info("Connecting to Qdrant...")
        try:
            client = AsyncQdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                api_key=settings.QDRANT_API_KEY,
                https=settings.QDRANT_USE_SSL,
                check_compatibility=False,
            )
            await client.get_collections()
            self.client = client
            logger.info(f"Connected to Qdrant vector database at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        except Exception as err:
            logger.warning(f"Could not connect to Qdrant host ({err}). Initializing in-memory Qdrant Vector DB...")
            self.client = AsyncQdrantClient(location=":memory:")
            logger.info("Initialized in-memory Qdrant Vector DB instance.")

    async def disconnect(self) -> None:
        if self.client:
            logger.info("Closing Qdrant connection...")
            if hasattr(self.client, "close"):
                try:
                    await self.client.close()
                except Exception as e:
                    logger.error(f"Failed to close Qdrant client: {e}")
            self.client = None

    async def ping(self) -> bool:
        if not self.client:
            return False
        try:
            await self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant ping failed: {str(e)}")
            return False


qdrant_service = QdrantService()


async def get_qdrant() -> AsyncQdrantClient:
    if qdrant_service.client is None:
        raise ServiceUnavailableError("Qdrant client is not initialized")
    return qdrant_service.client
