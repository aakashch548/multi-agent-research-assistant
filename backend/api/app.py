"""FastAPI application factory.

Creates and configures the ASGI application with middleware, routers,
exception handlers, and lifecycle management for all backing services.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import structlog

from backend.core.config import get_settings
from backend.core.exceptions import BaseAppException
from backend.core.logging import setup_logging
from backend.api.routes import research, documents, health, search
from backend.api.middleware import request_logging_middleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle.

    On startup: initializes logging, database engine, Redis pool,
    and ChromaDB client, storing them in app.state for shared access.
    On shutdown: gracefully closes all connections.
    """
    settings = get_settings()
    setup_logging(
        log_level=settings.log_level,
        json_output=settings.is_production,
    )
    logger.info(
        "application_starting",
        environment=settings.environment,
        api_host=settings.api_host,
        api_port=settings.api_port,
    )

    # Initialize database engine
    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            settings.database_url,
            echo=settings.is_development,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
        app.state.db_engine = engine
        logger.info("database_engine_initialized")

        from backend.models.database import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database_tables_initialized")
    except Exception as exc:
        logger.error("database_engine_init_failed", error=str(exc))
        app.state.db_engine = None

    # Initialize Redis
    try:
        from redis.asyncio import from_url as redis_from_url

        redis = redis_from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        app.state.redis = redis
        logger.info("redis_initialized")
    except Exception as exc:
        logger.error("redis_init_failed", error=str(exc))
        app.state.redis = None

    # Initialize ChromaDB
    try:
        import chromadb

        chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        app.state.chroma_client = chroma_client
        logger.info("chromadb_initialized")
    except Exception as exc:
        logger.error("chromadb_init_failed", error=str(exc))
        app.state.chroma_client = None

    yield

    # Shutdown: cleanup resources
    if getattr(app.state, "db_engine", None) is not None:
        await app.state.db_engine.dispose()
        logger.info("database_engine_disposed")

    if getattr(app.state, "redis", None) is not None:
        await app.state.redis.close()
        logger.info("redis_connection_closed")

    logger.info("application_shutting_down")


async def custom_exception_handler(
    request: Request,
    exc: BaseAppException,
) -> JSONResponse:
    """Convert domain exceptions into structured JSON error responses."""
    logger.warning(
        "application_error",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content=exc.to_dict(),
    )


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance.

    Returns:
        A fully configured FastAPI app ready to serve requests.
    """
    settings = get_settings()

    app = FastAPI(
        title="Multi-Agent Research Assistant",
        description="Autonomous AI research system with specialized agents",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
    )

    # Request logging (runs as outermost HTTP middleware)
    app.middleware("http")(request_logging_middleware)

    # Routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(
        research.router,
        prefix="/api/v1/research",
        tags=["Research"],
    )
    app.include_router(
        documents.router,
        prefix="/api/v1/documents",
        tags=["Documents"],
    )
    app.include_router(
        search.router,
        prefix="/api/v1/search",
        tags=["Search"],
    )

    # Exception handlers
    app.add_exception_handler(BaseAppException, custom_exception_handler)

    return app


app = create_app()
