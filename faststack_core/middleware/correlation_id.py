import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from faststack_core.logging.structured_logger import correlation_id_var


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assigns a unique correlation ID to every request.

    - Reads X-Correlation-ID from request header if present, otherwise generates UUID
    - Sets the correlation_id_var contextvar so all logs include it
    - Returns the correlation ID in the X-Correlation-ID response header
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        token = correlation_id_var.set(correlation_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            correlation_id_var.reset(token)
