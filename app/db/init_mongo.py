import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_mongo")


async def main():
    logger.info(f"Connecting to MongoDB at: {settings.MONGO_URI}")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]

    logger.info(f"Creating collections and indexes in database: {settings.MONGO_DB}")
    
    # 1. Create a unique index on 'email' in the 'users' collection
    await db.users.create_index("email", unique=True)
    logger.info("Unique index on 'email' created successfully on 'users' collection.")

    # 2. Create an index on 'user_id' in the 'user_profiles' collection
    await db.user_profiles.create_index("user_id")
    logger.info("Index on 'user_id' created successfully on 'user_profiles' collection.")

    # 3. Create an index on 'profile_id' in the 'birth_data' collection
    await db.birth_data.create_index("profile_id")
    logger.info("Index on 'profile_id' created successfully on 'birth_data' collection.")

    logger.info("MongoDB database successfully initialized!")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
