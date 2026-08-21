import contextvars
import logging
import sys

from pythonjsonlogger import jsonlogger

from app.core.config import settings

correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


def setup_logging() -> None:
    root_logger = logging.getLogger()

    # Clear existing handlers
    root_logger.handlers.clear()

    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.addFilter(CorrelationIdFilter())

    # Create the JSON formatter
    log_format = (
        "%(asctime)s %(levelname)s %(name)s %(message)s "
        "%(correlation_id)s %(filename)s %(lineno)d"
    )
    formatter = jsonlogger.JsonFormatter(  # type: ignore[attr-defined]
        fmt=log_format,
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    log_handler.setFormatter(formatter)
    root_logger.addHandler(log_handler)

    # Set level
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Redirect uvicorn loggers to root logger so they use our JSON formatter
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
