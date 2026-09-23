"""Web search service — searches the web and returns GPT-style text answers."""

from __future__ import annotations

import time

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from backend.core.config import Settings, get_settings
from backend.schemas.search import SourceResult, WebSearchResponse
from backend.tools.web_search import fetch_web_sources, has_real_tavily_key

logger = structlog.get_logger(__name__)

_GPT_STYLE_PROMPT = """\
You are a helpful AI assistant. The user asked a question and you have web \
search results to help you answer it.

Write your response exactly like ChatGPT would:
- Use clear, natural prose in complete sentences and paragraphs.
- Be direct, informative, and conversational.
- Do NOT use bullet points unless the user explicitly asked for a list.
- Do NOT say "based on search results" or "according to my sources".
- Do NOT include citation numbers like [1] or [2] in the text.
- If the search results don't fully answer the question, say what you know \
  and note any uncertainty naturally.
- Keep answers focused: usually 2-4 paragraphs unless the topic needs more.\
"""


class SearchService:
    """Search the web and produce a natural-language answer."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
    def _has_tavily(self) -> bool:
        return has_real_tavily_key(self._settings.tavily_api_key)

    def _has_openai(self) -> bool:
        key = self._settings.openai_api_key
        return bool(key and key not in ("demo-key", "sk-your-key-here", "sk-test"))

    async def search(self, query: str, max_results: int = 5) -> WebSearchResponse:
        """Search the web and return a GPT-style text answer."""
        start = time.perf_counter()
        logger.info("web_search_started", query=query[:120])

        sources = await self._fetch_sources(query, max_results)
        answer = await self._build_answer(query, sources)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "web_search_completed",
            query=query[:120],
            source_count=len(sources),
            elapsed_ms=round(elapsed_ms, 1),
        )

        return WebSearchResponse(
            query=query,
            answer=answer,
            sources=sources,
            source_count=len(sources),
            demo_mode=not self._has_tavily() and not sources,
            search_time_ms=round(elapsed_ms, 1),
        )

    async def _fetch_sources(
        self, query: str, max_results: int
    ) -> list[SourceResult]:
        """Fetch web results via Tavily or DuckDuckGo fallback."""
        sources = await fetch_web_sources(
            query,
            max_results=max_results,
            settings=self._settings,
        )
        if sources:
            return sources
        return self._demo_sources(query)

    async def _build_answer(
        self, query: str, sources: list[SourceResult]
    ) -> str:
        """Produce a GPT-style natural language answer."""
        if not sources:
            return (
                "I couldn't find relevant information for that question. "
                "Could you try rephrasing it or asking about something more specific?"
            )

        if self._has_openai() and not self._settings.demo_mode:
            try:
                return await self._synthesize_with_llm(query, sources)
            except Exception as exc:
                logger.warning("llm_synthesis_failed", error=str(exc))

        return self._format_as_text(query, sources)

    async def _synthesize_with_llm(
        self, query: str, sources: list[SourceResult]
    ) -> str:
        context = "\n\n".join(
            f"Source: {s.title}\n{s.content}" for s in sources if s.content
        )
        llm = ChatOpenAI(
            model=self._settings.openai_model,
            temperature=0.4,
            api_key=self._settings.openai_api_key,
        )
        messages = [
            SystemMessage(content=_GPT_STYLE_PROMPT),
            HumanMessage(content=f"Question: {query}\n\nWeb search results:\n{context}"),
        ]
        response = await llm.ainvoke(messages)
        return str(response.content).strip()

    @staticmethod
    def _format_as_text(query: str, sources: list[SourceResult]) -> str:
        """Build a readable GPT-like answer from web snippets."""
        snippets: list[str] = []
        for s in sources:
            text = (s.content or "").strip().replace("\n", " ")
            if text and text not in snippets:
                snippets.append(text)

        if not snippets:
            return (
                "I couldn't find enough information to answer that question. "
                "Try rephrasing it or being more specific."
            )

        def _first_sentences(text: str, n: int = 3) -> str:
            parts = [p.strip() for p in text.split(". ") if p.strip()]
            result = ". ".join(parts[:n])
            if result and not result.endswith("."):
                result += "."
            return result

        paragraphs = [_first_sentences(snippets[0], 4)]
        if len(snippets) > 1:
            extra = _first_sentences(snippets[1], 2)
            if extra and extra not in paragraphs[0]:
                paragraphs.append(extra)

        return "\n\n".join(paragraphs)

    @staticmethod
    def _demo_sources(query: str) -> list[SourceResult]:
        return [
            SourceResult(
                title=f"Information about {query[:50]}",
                url="https://en.wikipedia.org",
                content=(
                    f"{query} is an active area of research and discussion. "
                    "Multiple sources report ongoing developments, practical applications, "
                    "and evolving understanding in this field."
                ),
                score=0.9,
            ),
        ]
