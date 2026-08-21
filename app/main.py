import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import CorrelationIdMiddleware
from app.services.qdrant import qdrant_service
from app.db.session import mongodb_service

setup_logging()
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Startup: Connect services (MongoDB and Qdrant Vector DB)
    logger.info("Initializing external services...")
    try:
        await mongodb_service.connect()
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB during startup: {e}")

    try:
        await qdrant_service.connect()
        # Seed pretrained astrology & HuggingFace compatibility vector embeddings into Qdrant
        from app.domain.rag.seed_astrology_kb import seed_pretrained_astrology_knowledge
        from app.domain.rag.seed_hf_dataset import seed_hf_astrology_compatibility_dataset
        try:
            await seed_pretrained_astrology_knowledge()
            await seed_hf_astrology_compatibility_dataset(limit=200)
        except Exception as kb_err:
            logger.warning(f"Pretrained astrology KB seeding warning: {kb_err}")
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant during startup: {e}")

    yield

    # Shutdown: Disconnect services
    logger.info("Cleaning up external services...")
    try:
        await mongodb_service.disconnect()
    except Exception as e:
        logger.error(f"Failed to disconnect MongoDB: {e}")

    try:
        await qdrant_service.disconnect()
    except Exception as e:
        logger.error(f"Failed to disconnect Qdrant: {e}")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Set up CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Set up Correlation ID middleware
app.add_middleware(CorrelationIdMiddleware)

# Set up Centralized Exception Handlers
setup_exception_handlers(app)

# Include versioned API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": f"Welcome to {settings.APP_NAME}", "version": "0.1.0"}
