import logging

from fastapi import APIRouter, Depends, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.session import get_db_session
from app.schemas.health import ComponentHealth, HealthResponse
from app.services.qdrant import qdrant_service

logger = logging.getLogger("app.api.health")
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health and Readiness Check",
)
async def health_check(
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db_session),
) -> HealthResponse:
    # 1. DB health
    db_status = "healthy"
    db_details = None
    try:
        await db.command("ping")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
        db_details = str(e)

    # 2. Qdrant health
    qdrant_ok = await qdrant_service.ping()
    qdrant_status = "healthy" if qdrant_ok else "unhealthy"
    qdrant_details = None if qdrant_ok else "Connection failed"

    # Overall status
    overall_status = "healthy"
    if db_status == "unhealthy" or qdrant_status == "unhealthy":
        overall_status = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=overall_status,
        version="0.1.0",
        database=ComponentHealth(status=db_status, details=db_details),
        qdrant=ComponentHealth(status=qdrant_status, details=qdrant_details),
    )


@router.get(
    "/readiness",
    status_code=status.HTTP_200_OK,
    summary="Readiness check for external dependencies",
)
async def readiness_check(
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db_session),
) -> dict[str, str]:
    # Basic readiness verification: check DB connection
    try:
        await db.command("ping")
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "detail": str(e)}

    # Check Qdrant vector database
    qdrant_ok = await qdrant_service.ping()
    if not qdrant_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "detail": "Qdrant vector database is offline"}

    return {"status": "ready"}
