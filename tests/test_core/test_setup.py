"""Tests for setup_app() — the one-call integration point."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from faststack_core.exceptions.domain import NotFoundError
from faststack_core.settings.config import FastStackConfig
from faststack_core.setup import setup_app


def _make_app(config: FastStackConfig | None = None) -> FastAPI:
    app = FastAPI()
    setup_app(app, config)
    return app


# ---------------------------------------------------------------------------
# Default setup
# ---------------------------------------------------------------------------


async def test_setup_registers_health():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_setup_registers_exception_handlers():
    app = _make_app()

    @app.get("/fail")
    async def fail():
        raise NotFoundError("gone")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/fail")
    assert resp.status_code == 404
    assert resp.json()["type"] == "/errors/NotFoundError"


async def test_setup_registers_correlation_id():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert "X-Correlation-ID" in resp.headers


async def test_setup_registers_security_headers():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"


# ---------------------------------------------------------------------------
# Disabled features
# ---------------------------------------------------------------------------


async def test_disable_health_check():
    app = _make_app(FastStackConfig(health_check=False))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 404  # not registered


async def test_disable_exception_handlers():
    app = _make_app(FastStackConfig(exception_handlers=False))

    @app.get("/fail")
    async def fail():
        raise NotFoundError("gone")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/fail")
    assert resp.status_code == 500  # unhandled, FastAPI default


async def test_disable_correlation_id():
    app = _make_app(FastStackConfig(correlation_id=False))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert "X-Correlation-ID" not in resp.headers


async def test_disable_security_headers():
    app = _make_app(FastStackConfig(security_headers=False))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert "X-Content-Type-Options" not in resp.headers


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


async def test_cors_enabled():
    app = _make_app(FastStackConfig(cors_origins=["http://localhost:3000"]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


async def test_cors_disabled_by_default():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert "access-control-allow-origin" not in resp.headers
