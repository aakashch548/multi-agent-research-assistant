"""Health check endpoints for liveness and readiness probes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/",
    summary="Liveness probe",
    response_model=dict[str, str],
)
async def liveness() -> dict[str, str]:
    """Minimal liveness check confirming the service is running."""
    return {"status": "ok", "version": "1.0.0"}


@router.get(
    "/health",
    summary="Readiness probe with dependency checks",
)
async def readiness(request: Request) -> dict[str, Any]:
    """Detailed health check verifying connectivity to all backing services.

    Returns individual status for PostgreSQL, Redis, and ChromaDB along
    with an overall aggregated status.
    """
    checks: dict[str, dict[str, Any]] = {}

    # PostgreSQL
    checks["database"] = await _check_database(request)

    # Redis
    checks["redis"] = await _check_redis(request)

    # ChromaDB
    checks["chromadb"] = await _check_chromadb(request)

    overall = "healthy" if all(
        c["status"] == "healthy" for c in checks.values()
    ) else "degraded"

    return {
        "status": overall,
        "version": "1.0.0",
        "checks": checks,
    }


async def _check_database(request: Request) -> dict[str, Any]:
    """Verify PostgreSQL connectivity via a lightweight query."""
    try:
        engine = getattr(request.app.state, "db_engine", None)
        if engine is None:
            return {"status": "unhealthy", "reason": "engine not initialized"}

        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as exc:
        logger.warning("health_check_database_failed", error=str(exc))
        return {"status": "unhealthy", "reason": str(exc)}


async def _check_redis(request: Request) -> dict[str, Any]:
    """Verify Redis connectivity via PING."""
    try:
        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return {"status": "unhealthy", "reason": "redis not initialized"}

        pong = await redis.ping()
        if pong:
            return {"status": "healthy"}
        return {"status": "unhealthy", "reason": "ping returned falsy"}
    except Exception as exc:
        logger.warning("health_check_redis_failed", error=str(exc))
        return {"status": "unhealthy", "reason": str(exc)}


async def _check_chromadb(request: Request) -> dict[str, Any]:
    """Verify ChromaDB connectivity via heartbeat."""
    try:
        chroma_client = getattr(request.app.state, "chroma_client", None)
        if chroma_client is None:
            return {"status": "unhealthy", "reason": "chromadb not initialized"}

        heartbeat = chroma_client.heartbeat()
        if heartbeat:
            return {"status": "healthy"}
        return {"status": "unhealthy", "reason": "heartbeat returned falsy"}
    except Exception as exc:
        logger.warning("health_check_chromadb_failed", error=str(exc))
        return {"status": "unhealthy", "reason": str(exc)}
