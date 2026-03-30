"""Tests for middleware: correlation ID, request logging, security headers."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from faststack_core.middleware.correlation_id import CorrelationIdMiddleware
from faststack_core.middleware.request_logging import RequestLoggingMiddleware
from faststack_core.middleware.security_headers import SECURITY_HEADERS, SecurityHeadersMiddleware


def _make_app(*middleware_classes) -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"pong": True}

    for cls in middleware_classes:
        app.add_middleware(cls)
    return app


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# Correlation ID
# ---------------------------------------------------------------------------


async def test_correlation_id_generated():
    """When no header is sent, a UUID is generated and returned."""
    app = _make_app(CorrelationIdMiddleware)
    async with await _client(app) as client:
        resp = await client.get("/ping")
    assert resp.status_code == 200
    cid = resp.headers.get("X-Correlation-ID")
    assert cid is not None
    assert len(cid) == 36  # UUID format


async def test_correlation_id_propagated():
    """When X-Correlation-ID is sent, the same value is returned."""
    app = _make_app(CorrelationIdMiddleware)
    async with await _client(app) as client:
        resp = await client.get("/ping", headers={"X-Correlation-ID": "my-id-123"})
    assert resp.headers["X-Correlation-ID"] == "my-id-123"


# ---------------------------------------------------------------------------
# Request Logging
# ---------------------------------------------------------------------------


async def test_request_logging_does_not_break_response():
    """RequestLoggingMiddleware should not alter the response."""
    app = _make_app(RequestLoggingMiddleware)
    async with await _client(app) as client:
        resp = await client.get("/ping")
    assert resp.status_code == 200
    assert resp.json() == {"pong": True}


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------


async def test_security_headers_present():
    """All standard security headers are added to responses."""
    app = _make_app(SecurityHeadersMiddleware)
    async with await _client(app) as client:
        resp = await client.get("/ping")
    for header, value in SECURITY_HEADERS.items():
        assert resp.headers.get(header) == value, f"Missing or wrong: {header}"


async def test_security_headers_do_not_override_app_headers():
    """App-set headers take precedence over middleware defaults."""
    app = FastAPI()

    @app.get("/custom")
    async def custom():
        from starlette.responses import JSONResponse

        return JSONResponse({"ok": True}, headers={"X-Frame-Options": "SAMEORIGIN"})

    app.add_middleware(SecurityHeadersMiddleware)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/custom")
    assert resp.headers["X-Frame-Options"] == "SAMEORIGIN"
