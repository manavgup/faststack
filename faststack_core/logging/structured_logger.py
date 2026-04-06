import logging
import sys
from contextvars import ContextVar

from faststack_core.logging.masking import SensitiveDataFilter

# This will be set by the correlation ID middleware
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return correlation_id_var.get()


TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


class StructuredLogger:
    """Production-grade logger with dual output format.

    - ``"text"``: human-readable console output for development
    - ``"json"``: structured JSON for log aggregation (uses python-json-logger)

    Sensitive data masking is applied when ``sensitive_fields`` is provided.
    """

    def setup(
        self,
        app_name: str = "faststack",
        log_level: str = "INFO",
        log_format: str = "text",
        sensitive_fields: list[str] | None = None,
    ) -> logging.Logger:
        """Configure and return a logger with the appropriate handlers."""
        logger = logging.getLogger(app_name)
        logger.setLevel(getattr(logging, log_level.upper()))
        logger.handlers.clear()

        if log_format == "json":
            from pythonjsonlogger import json as jsonlogger

            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        else:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(TEXT_FORMAT))

        if sensitive_fields:
            handler.addFilter(SensitiveDataFilter(sensitive_fields))

        logger.addHandler(handler)
        return logger
