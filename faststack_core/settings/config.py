from dataclasses import dataclass, field


@dataclass
class FastStackConfig:
    """Configuration for setup_app().

    Each boolean controls whether the corresponding middleware/feature
    is registered. All enabled by default.
    """

    # Middleware toggles
    correlation_id: bool = True
    request_logging: bool = True
    security_headers: bool = True

    # CORS (None = disabled, provide origins to enable)
    cors_origins: list[str] | None = None

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"
    sensitive_fields: list[str] = field(
        default_factory=lambda: [
            "password",
            "secret",
            "token",
            "api_key",
            "authorization",
        ]
    )

    # Health checks
    health_check: bool = True
    health_check_path: str = "/health"
    app_version: str = "0.1.0"

    # Exception handlers
    exception_handlers: bool = True
