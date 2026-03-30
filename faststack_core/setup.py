from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from faststack_core.health.endpoints import create_health_router
from faststack_core.logging.structured_logger import StructuredLogger
from faststack_core.middleware.correlation_id import CorrelationIdMiddleware
from faststack_core.middleware.request_logging import RequestLoggingMiddleware
from faststack_core.middleware.security_headers import SecurityHeadersMiddleware
from faststack_core.settings.config import FastStackConfig


def setup_app(app: FastAPI, config: FastStackConfig | None = None) -> None:
    """One-call setup for all FastStack middleware, handlers, and health checks.

    Each component can be individually disabled via the config.

    Middleware order note: Starlette processes middleware in reverse order of
    registration. We register security_headers first (outermost = last to
    execute on request, first on response), then request_logging, then
    correlation_id (innermost = first to execute on request). This means
    correlation_id is set before request_logging runs, so logs have the ID.
    """
    if config is None:
        config = FastStackConfig()

    # Logging
    logger = StructuredLogger()
    logger.setup(log_level=config.log_level)

    # Middleware (order matters — outermost first)
    if config.security_headers:
        app.add_middleware(SecurityHeadersMiddleware)

    if config.request_logging:
        app.add_middleware(RequestLoggingMiddleware)

    if config.correlation_id:
        app.add_middleware(CorrelationIdMiddleware)

    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Exception handlers
    if config.exception_handlers:
        from faststack_core.exceptions.handlers import register_exception_handlers

        register_exception_handlers(app)

    # Health checks
    if config.health_check:
        health_router = create_health_router(app_version=config.app_version)
        app.include_router(health_router)
