"""Structured logging setup for the application.

Configures structlog with JSON output in production and pretty-printed
console output in development. Ensures PII and credential fields are
never emitted.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from core.config import get_settings

# Fields that must never appear in log output.
_REDACTED_FIELDS: frozenset[str] = frozenset(
    {
        "access_token",
        "refresh_token",
        "encrypted_access_token",
        "encrypted_refresh_token",
        "token",
        "password",
        "secret",
        "api_key",
        "body_text",
        "body_html",
        "body",
        "email_content",
    }
)

_REDACTED_PLACEHOLDER = "[REDACTED]"


def _redact_sensitive_fields(
    _logger: WrappedLogger,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Structlog processor that removes sensitive fields from log events.

    Args:
        _logger: The wrapped logger instance (unused).
        _method_name: The logging method name (unused).
        event_dict: The mutable event dictionary to sanitize.

    Returns:
        The sanitized event dictionary.
    """
    for field in _REDACTED_FIELDS:
        if field in event_dict:
            event_dict[field] = _REDACTED_PLACEHOLDER
    return event_dict


def configure_logging() -> None:
    """Initialize structlog and the standard library logging bridge.

    Must be called once during application startup before any loggers
    are used.
    """
    settings = get_settings()

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _redact_sensitive_fields,
    ]

    if settings.log_format == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(settings.log_level)

    # Suppress noisy third-party loggers.
    for noisy_logger in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for the given module name.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A pre-configured structlog BoundLogger.
    """
    return structlog.get_logger(name)
