import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import correlation_id_var

logger = logging.getLogger("app.exceptions")


def make_serializable(obj: Any) -> Any:
    """Recursively convert bytes, exceptions, and non-serializable objects into JSON-friendly types."""
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, Exception):
        return str(obj)
    return obj


class AppError(Exception):
    def __init__(
        self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ServiceUnavailableError(AppError):
    def __init__(self, message: str = "Service unavailable"):
        super().__init__(message, status.HTTP_503_SERVICE_UNAVAILABLE)


class DatabaseError(AppError):
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)


async def app_exception_handler(_request: Request, exc: AppError) -> JSONResponse:
    correlation_id = correlation_id_var.get()
    logger.error(
        f"Application exception: {exc.message} status_code={exc.status_code}",
        extra={"status_code": exc.status_code, "correlation_id": correlation_id},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "message": exc.message,
                "code": exc.__class__.__name__,
            },
            "correlation_id": correlation_id,
        },
    )


async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    correlation_id = correlation_id_var.get()
    raw_errors = exc.errors()
    safe_errors = make_serializable(raw_errors)
    logger.warning(
        f"Validation exception: {safe_errors}",
        extra={"correlation_id": correlation_id},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "message": "Validation failed",
                "code": "RequestValidationError",
                "details": safe_errors,
            },
            "correlation_id": correlation_id,
        },
    )


async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    correlation_id = correlation_id_var.get()
    logger.exception(
        f"Unhandled exception: {exc}",
        extra={"correlation_id": correlation_id},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "message": "An unexpected error occurred",
                "code": "InternalServerError",
            },
            "correlation_id": correlation_id,
        },
    )


def setup_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, global_exception_handler)
