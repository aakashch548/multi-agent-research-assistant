"""Shared workflow state schema for the multi-agent research pipeline.

``ResearchState`` is a :class:`~typing.TypedDict` consumed by every agent
node in the LangGraph workflow.  All fields use ``total=False`` so that
individual agent nodes can return *partial* updates.
"""

from __future__ import annotations

from typing import Any, TypedDict


class ResearchState(TypedDict, total=False):
    """State flowing through the LangGraph research workflow."""

    query: str
    plan: list[dict[str, Any]]
    research_results: list[dict[str, Any]]
    verified_facts: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    summary: str
    report: str
    mermaid_diagram: str
    errors: list[str]
    metadata: dict[str, Any]
    current_agent: str
    retry_count: int
    max_retries: int
    session_id: str
    status: str
