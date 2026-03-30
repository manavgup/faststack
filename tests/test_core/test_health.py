"""Tests for health check endpoints."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from faststack_core.health.endpoints import create_health_router


def _make_app(version: str = "1.0.0") -> FastAPI:
    app = FastAPI()
    app.include_router(create_health_router(app_version=version))
    return app


async def test_health_returns_ok():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_health_detailed_includes_version():
    app = _make_app(version="2.5.0")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health/detailed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.5.0"
