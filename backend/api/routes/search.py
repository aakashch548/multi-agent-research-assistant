"""Web search endpoints for querying external sources."""

from __future__ import annotations

from fastapi import APIRouter, Depends

import structlog

from backend.api.dependencies import get_search_service
from backend.core.config import get_settings
from backend.schemas.search import WebSearchRequest, WebSearchResponse
from backend.services.search_service import SearchService

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=WebSearchResponse,
    summary="Search external web sources",
)
async def web_search(
    request: WebSearchRequest,
    service: SearchService = Depends(get_search_service),
) -> WebSearchResponse:
    """Search the web via Tavily and return a synthesized answer with sources."""
    logger.info("web_search_requested", query=request.query[:120])
    return await service.search(request.query, max_results=request.max_results)


@router.get(
    "/status",
    summary="Check search mode and availability",
)
async def search_status() -> dict:
    """Return whether live external search is enabled."""
    settings = get_settings()
    return {
        "demo_mode": settings.demo_mode,
        "live_search": True,
        "message": (
            "Live web search enabled (DuckDuckGo + optional Tavily/OpenAI)"
        ),
    }
