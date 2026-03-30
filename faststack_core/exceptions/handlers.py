"""RFC 7807 Problem Details exception handlers for FastAPI.

Call ``register_exception_handlers(app)`` during application startup to
install a single handler that converts any ``DomainError`` (or subclass)
into a JSON response that conforms to RFC 7807.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .domain import EXCEPTION_STATUS_MAP, DomainError


def register_exception_handlers(app: FastAPI) -> None:
    """Register domain-error handlers that produce RFC 7807 responses."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        status = EXCEPTION_STATUS_MAP.get(type(exc), 500)
        return JSONResponse(
            status_code=status,
            content={
                "type": f"/errors/{type(exc).__name__}",
                "title": type(exc).__name__,
                "status": status,
                "detail": exc.message,
                "instance": str(request.url),
                **({"details": exc.details} if exc.details else {}),
            },
        )
