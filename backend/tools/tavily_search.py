"""Tavily web search integration with retry logic and structured results.

Provides both simple search and context-aware search that incorporates
prior conversation state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog
from tavily import AsyncTavilyClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single web search result."""

    title: str
    url: str
    content: str
    score: float
    raw_content: str = ""


class TavilySearchTool:
    """Async wrapper around the Tavily search API.

    Args:
        api_key: Tavily API key.
        max_results: Default number of results per search.
    """

    def __init__(self, api_key: str, max_results: int = 5) -> None:
        if not api_key:
            raise ValueError("Tavily API key must not be empty")

        self.max_results = max_results
        self._client = AsyncTavilyClient(api_key=api_key)
        logger.info(
            "tavily_search_tool_initialized",
            max_results=self.max_results,
        )

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    async def search(
        self,
        query: str,
        search_depth: str = "advanced",
    ) -> list[SearchResult]:
        """Execute a Tavily web search.

        Args:
            query: The search query string.
            search_depth: ``"basic"`` or ``"advanced"`` – advanced uses
                          Tavily's deeper extraction.

        Returns:
            Formatted list of SearchResult objects.
        """
        if not query or not query.strip():
            logger.warning("search_called_with_empty_query")
            return []

        if search_depth not in {"basic", "advanced"}:
            search_depth = "advanced"

        logger.info(
            "tavily_search_started",
            query=query[:120],
            depth=search_depth,
        )

        try:
            raw_response: dict[str, Any] = await self._client.search(
                query=query,
                search_depth=search_depth,
                max_results=self.max_results,
                include_raw_content=True,
            )
            raw_results: list[dict[str, Any]] = raw_response.get("results", [])
            results = self._format_results(raw_results)

            logger.info(
                "tavily_search_completed",
                query=query[:120],
                results_count=len(results),
            )
            return results
        except Exception:
            logger.exception("tavily_search_failed", query=query[:120])
            raise

    async def search_with_context(
        self,
        query: str,
        context: str,
    ) -> list[SearchResult]:
        """Search with additional context folded into the query.

        The context is prepended to sharpen the search intent (e.g.
        previous conversation turns or a research topic description).

        Args:
            query: The core search query.
            context: Supporting context text.

        Returns:
            Formatted list of SearchResult objects.
        """
        if not context or not context.strip():
            return await self.search(query)

        context_snippet = context[:500].strip()
        augmented_query = f"{context_snippet}\n\n{query}"
        logger.debug(
            "context_augmented_search",
            original_query=query[:80],
            context_length=len(context),
        )
        return await self.search(augmented_query)

    @staticmethod
    def _format_results(raw_results: list[dict[str, Any]]) -> list[SearchResult]:
        """Convert raw Tavily response dicts into SearchResult objects.

        Args:
            raw_results: List of result dicts from the Tavily API.

        Returns:
            Cleaned list of SearchResult instances.
        """
        formatted: list[SearchResult] = []
        for item in raw_results:
            title = (item.get("title") or "Untitled").strip()
            url = (item.get("url") or "").strip()
            content = (item.get("content") or "").strip()
            raw_content = (item.get("raw_content") or "").strip()
            score = float(item.get("score", 0.0))

            if not content and not raw_content:
                continue

            formatted.append(
                SearchResult(
                    title=title,
                    url=url,
                    content=content,
                    score=score,
                    raw_content=raw_content,
                )
            )

        formatted.sort(key=lambda r: r.score, reverse=True)
        return formatted
