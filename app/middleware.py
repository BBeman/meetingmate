import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging import correlation_id_var, get_logger


logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request/response details with timing and correlation IDs."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # prefer client-provided correlation ID, otherwise generate one
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        correlation_id_var.set(correlation_id)

        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        logger.info(f"Request started: {method} {path} from {client_ip}")

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"Request completed: {method} {path} status={response.status_code} "
            f"duration={duration_ms:.2f}ms"
        )

        # echo correlation ID back so clients can trace their requests
        response.headers["X-Correlation-ID"] = correlation_id
        return response
