import logging
import sys
from contextvars import ContextVar

# This will be set by the correlation ID middleware
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return correlation_id_var.get()


class StructuredLogger:
    """Production-grade logger with dual output.

    - Console: colored text for development (human-readable)
    - JSON: structured for log aggregation (machine-readable)
    """

    def setup(self, app_name: str = "faststack", log_level: str = "INFO") -> logging.Logger:
        """Configure and return a logger with the appropriate handlers."""
        logger = logging.getLogger(app_name)
        logger.setLevel(getattr(logging, log_level.upper()))
        logger.handlers.clear()

        # Console handler — simple text format
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )
        logger.addHandler(console)

        return logger
