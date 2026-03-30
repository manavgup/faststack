from dataclasses import dataclass, field


@dataclass
class LogConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"  # "json" or "text"
    app_name: str = "faststack"
    # Fields that should always be masked in log output
    sensitive_patterns: list[str] = field(
        default_factory=lambda: [
            "password",
            "secret",
            "token",
            "api_key",
            "authorization",
            "credit_card",
        ]
    )
