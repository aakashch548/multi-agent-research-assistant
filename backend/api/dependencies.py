"""FastAPI dependency injection re-exports for API routes.

Bridges the core dependency providers to the API layer, adding any
route-specific dependencies not covered by core/dependencies.py.
"""

from __future__ import annotations

from backend.core.dependencies import (
    get_research_service,
    get_db_session,
    get_redis_client,
    get_chroma_client,
    DBSessionDep,
    RedisDep,
    ChromaDep,
    SettingsDep,
)
from backend.core.config import Settings, get_settings

from fastapi import Depends


async def get_document_service(
    chroma: ChromaDep,
    settings: SettingsDep,
):
    """Build and return the DocumentService with its dependencies."""
    from backend.services.document_service import DocumentService

    return DocumentService(
        chroma_client=chroma,
        settings=settings,
    )


async def get_search_service(settings: SettingsDep):
    """Build and return the SearchService."""
    from backend.services.search_service import SearchService

    return SearchService(settings=settings)


__all__ = [
    "get_research_service",
    "get_document_service",
    "get_search_service",
    "get_db_session",
    "get_redis_client",
    "get_chroma_client",
    "DBSessionDep",
    "RedisDep",
    "ChromaDep",
    "SettingsDep",
]
