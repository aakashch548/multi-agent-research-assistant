"""FastAPI dependency-injection providers.

Each function is designed for use with ``Depends()`` in route
definitions.  Database sessions, cache clients, and application
services are created / torn down per-request via async generators.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

import chromadb
import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import Settings, get_settings

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

SettingsDep = Annotated[Settings, Depends(get_settings)]


# ---------------------------------------------------------------------------
# SQLAlchemy async engine / session
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _build_engine(database_url: str):
    """Create a singleton async engine (cached by URL)."""
    return create_async_engine(
        database_url,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


@lru_cache(maxsize=1)
def _build_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = _build_engine(database_url)
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db_session(
    settings: SettingsDep,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session scoped to a single request.

    The session is committed on success and rolled back on exception,
    then closed unconditionally.
    """
    factory = _build_session_factory(settings.database_url)
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

_redis_pool: aioredis.Redis | None = None


async def get_redis_client(
    settings: SettingsDep,
) -> AsyncGenerator[aioredis.Redis, None]:
    """Return a shared async Redis client.

    The client is lazily created on first request and re-used across
    the application lifetime.
    """
    global _redis_pool  # noqa: PLW0603
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
    yield _redis_pool


RedisDep = Annotated[aioredis.Redis, Depends(get_redis_client)]


# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------

_chroma_client: chromadb.HttpClient | None = None


async def get_chroma_client(
    settings: SettingsDep,
) -> AsyncGenerator[chromadb.HttpClient, None]:
    """Return a shared ChromaDB HTTP client."""
    global _chroma_client  # noqa: PLW0603
    if _chroma_client is None:
        _chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
    yield _chroma_client


ChromaDep = Annotated[chromadb.HttpClient, Depends(get_chroma_client)]


# ---------------------------------------------------------------------------
# Application services (thin wrappers assembled from dependencies above)
# ---------------------------------------------------------------------------

async def get_research_service(
    db: DBSessionDep,
    settings: SettingsDep,
):
    """Build and return the ``ResearchService`` with all its dependencies."""
    from backend.repositories.session_repository import SessionRepository
    from backend.repositories.step_repository import StepRepository
    from backend.services.research_service import ResearchService
    from backend.workflows.research_graph import ResearchWorkflow

    factory = _build_session_factory(settings.database_url)
    return ResearchService(
        workflow=ResearchWorkflow(),
        session_repo=SessionRepository(factory),
        step_repo=StepRepository(factory),
    )
