import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import correlation_id_var

logger = logging.getLogger("app.middleware")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get(
            "X-Request-ID"
        )
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        token = correlation_id_var.set(correlation_id)
        start_time = time.perf_counter()

        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            f" [API HIT] --> {request.method} '{request.url.path}' | Client IP: {client_ip} | ID: {correlation_id[:8]}"
        )

        try:
            response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000  # ms
            response.headers["X-Correlation-ID"] = correlation_id

            logger.info(
                f" [API ACTION COMPLETED] <-- {request.method} '{request.url.path}' | Status: {response.status_code} | Latency: {process_time:.2f}ms"
            )
            return response
        except Exception as e:
            process_time = (time.perf_counter() - start_time) * 1000
            logger.exception(
                f" [API HIT ERROR] <-- {request.method} '{request.url.path}' | Error: {str(e)} | Latency: {process_time:.2f}ms"
            )
            from fastapi import status
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": {
                        "message": f"Error processing request: {str(e)}",
                        "code": "InternalServerError",
                    },
                    "correlation_id": correlation_id,
                },
            )
        finally:
            correlation_id_var.reset(token)
