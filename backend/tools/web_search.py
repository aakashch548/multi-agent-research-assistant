"""Shared web search — Tavily when configured, DuckDuckGo otherwise."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from backend.schemas.search import SourceResult
from backend.tools.tavily_search import TavilySearchTool

if TYPE_CHECKING:
    from backend.core.config import Settings

logger = structlog.get_logger(__name__)

_PLACEHOLDER_TAVILY = frozenset({"demo-key", "tvly-your-key-here", ""})


def has_real_tavily_key(api_key: str | None) -> bool:
    key = (api_key or "").strip()
    return bool(key and key not in _PLACEHOLDER_TAVILY)


async def fetch_web_sources(
    query: str,
    *,
    max_results: int = 5,
    settings: Settings | None = None,
) -> list[SourceResult]:
    """Return web search hits using Tavily or DuckDuckGo."""
    from backend.core.config import get_settings

    cfg = settings or get_settings()
    if has_real_tavily_key(cfg.tavily_api_key):
        try:
            tool = TavilySearchTool(
                api_key=cfg.tavily_api_key,
                max_results=max_results,
            )
            results = await tool.search(query)
            return [
                SourceResult(
                    title=r.title,
                    url=r.url,
                    content=r.content or r.raw_content,
                    score=r.score,
                )
                for r in results[:max_results]
            ]
        except Exception as exc:
            logger.warning("tavily_search_failed_try_ddg", error=str(exc))

    try:
        return await search_duckduckgo(query, max_results)
    except Exception as exc:
        logger.warning("duckduckgo_search_failed", error=str(exc))
        return []


async def search_duckduckgo(query: str, max_results: int) -> list[SourceResult]:
    """Free web search via DuckDuckGo (no API key)."""

    def _run() -> list[SourceResult]:
        from ddgs import DDGS

        sources: list[SourceResult] = []
        for i, item in enumerate(DDGS().text(query, max_results=max_results)):
            sources.append(
                SourceResult(
                    title=item.get("title", f"Result {i + 1}"),
                    url=item.get("href", item.get("link", "")),
                    content=item.get("body", item.get("snippet", "")),
                    score=max(0.5, 1.0 - i * 0.08),
                )
            )
        return sources

    return await asyncio.to_thread(_run)


def sources_to_search_dicts(sources: list[SourceResult]) -> list[dict]:
    """Convert SourceResult list to researcher-friendly dicts."""
    return [
        {
            "title": s.title,
            "url": s.url,
            "content": s.content,
            "score": s.score,
        }
        for s in sources
    ]
