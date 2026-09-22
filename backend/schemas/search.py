"""Pydantic schemas for web search API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WebSearchRequest(BaseModel):
    """Payload for a web search query."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(..., min_length=3, max_length=2000)
    max_results: int = Field(default=5, ge=1, le=10)


class SourceResult(BaseModel):
    """A single external search result."""

    title: str
    url: str
    content: str
    score: float = 0.0


class WebSearchResponse(BaseModel):
    """Answer synthesized from external web sources."""

    query: str
    answer: str
    sources: list[SourceResult] = Field(default_factory=list)
    source_count: int = 0
    demo_mode: bool = False
    search_time_ms: float = 0.0
