import logging
import sys
from contextvars import ContextVar


# holds the correlation ID for the current request, accessible across async boundaries
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


class CorrelationIdFilter(logging.Filter):
    """Injects the current request's correlation ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging with correlation IDs for request tracing."""
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(correlation_id)s | %(name)s | %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    handler.addFilter(CorrelationIdFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with correlation ID support already configured."""
    return logging.getLogger(name)
