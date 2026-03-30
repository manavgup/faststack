from fastapi import APIRouter


def create_health_router(app_version: str = "0.1.0") -> APIRouter:
    """Create a health check router.

    GET /health — simple liveness check
    GET /health/detailed — includes version (DB check requires session dependency override)
    """
    router = APIRouter(tags=["health"])

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/health/detailed")
    async def health_detailed() -> dict[str, str]:
        return {
            "status": "ok",
            "version": app_version,
        }

    return router
