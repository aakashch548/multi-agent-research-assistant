"""HTTP middleware for request logging, correlation-ID propagation, and error handling.

Provides production-grade request tracing via X-Request-ID headers and
structured logging of every request/response cycle with timing data.
"""

from __future__ import annotations

import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

import structlog

from backend.core.logging import set_correlation_id, get_correlation_id

logger = structlog.get_logger(__name__)


async def request_logging_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Log every HTTP request with method, path, status, and duration.

    Also propagates a correlation ID (X-Request-ID) through the request
    lifecycle. If the client sends an X-Request-ID header it is reused;
    otherwise a new UUID-4 is generated.
    """
    correlation_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    set_correlation_id(correlation_id)

    start_time = time.perf_counter()

    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        query=str(request.url.query) if request.url.query else None,
        client_ip=request.client.host if request.client else None,
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "request_failed",
            method=request.method,
            path=request.url.path,
            duration_ms=round(duration_ms, 2),
        )
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )

    response.headers["X-Request-ID"] = correlation_id
    response.headers["X-Response-Time-Ms"] = str(round(duration_ms, 2))

    return response


async def error_handler_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Catch unhandled exceptions and return a generic 500 JSON response.

    This acts as a safety net for anything that slips past specific
    exception handlers registered on the app.
    """
    from fastapi.responses import JSONResponse

    try:
        return await call_next(request)
    except Exception as exc:
        correlation_id = get_correlation_id()
        logger.exception(
            "unhandled_exception",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected internal error occurred.",
                "correlation_id": correlation_id,
            },
        )
