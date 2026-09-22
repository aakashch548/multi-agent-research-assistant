"""Structured JSON logging with structlog.

Configures processors, formatters, and correlation-ID propagation so
every log entry is machine-parseable and traceable back to a single
request or research session.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

_correlation_id_ctx: ContextVar[str | None] = ContextVar(
    "correlation_id", default=None
)


def get_correlation_id() -> str | None:
    """Return the correlation ID bound to the current async context."""
    return _correlation_id_ctx.get()


def set_correlation_id(cid: str | None = None) -> str:
    """Bind a correlation ID for the current async context.

    If *cid* is ``None`` a new UUID-4 is generated.  Returns the
    (possibly generated) correlation ID.
    """
    cid = cid or uuid.uuid4().hex
    _correlation_id_ctx.set(cid)
    return cid


def _add_correlation_id(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that injects the correlation ID."""
    cid = get_correlation_id()
    if cid is not None:
        event_dict["correlation_id"] = cid
    return event_dict


def _add_app_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Inject constant application-level fields."""
    event_dict.setdefault("service", "research-assistant")
    return event_dict


def setup_logging(
    log_level: str = "INFO",
    json_output: bool = True,
) -> None:
    """Configure structlog and the stdlib root logger.

    Args:
        log_level: Minimum severity (``DEBUG``, ``INFO``, etc.).
        json_output: When *True* (default) emit JSON lines; when
            *False* use coloured console output (useful during local
            development).
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_correlation_id,
        _add_app_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
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
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Suppress overly chatty third-party loggers
    for noisy in ("httpx", "httpcore", "chromadb", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None, **initial_bindings: Any) -> structlog.stdlib.BoundLogger:
    """Return a structured logger, optionally pre-bound with context fields.

    Args:
        name: Logger name (typically ``__name__`` of the calling module).
        **initial_bindings: Key/value pairs bound to every message
            emitted by the returned logger.

    Returns:
        A :class:`structlog.stdlib.BoundLogger` ready for use.
    """
    log: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    if initial_bindings:
        log = log.bind(**initial_bindings)
    return log
