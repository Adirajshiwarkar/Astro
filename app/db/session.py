import logging
from collections.abc import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger("app.db.session")


class MongoDBService:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        logger.info("Connecting to MongoDB...")
        self.client = AsyncIOMotorClient(settings.MONGO_URI)
        self._db = self.client[settings.MONGO_DB]
        logger.info(f"Connected to MongoDB database: {settings.MONGO_DB}")

    async def disconnect(self) -> None:
        if self.client:
            logger.info("Closing MongoDB connection...")
            self.client.close()
            self.client = None
            self._db = None

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._db is None:
            raise RuntimeError("MongoDB is not connected. Call connect() first.")
        return self._db


mongodb_service = MongoDBService()


async def get_db_session() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    yield mongodb_service.db
