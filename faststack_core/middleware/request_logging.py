import logging
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from faststack_core.logging.structured_logger import get_correlation_id

logger = logging.getLogger("faststack.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs HTTP request completion with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "correlation_id": get_correlation_id(),
            },
        )
        return response
