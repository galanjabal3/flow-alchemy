"""Logging configuration using structlog.

Provides structured logging for the application.
"""

import logging
import structlog
from app.core.secure_logging import redact_processor


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structlog with JSON rendering for production."""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            redact_processor,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Get a bound logger instance."""
    return structlog.get_logger(name)
