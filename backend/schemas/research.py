"""Pydantic v2 request / response schemas for the research API.

All schemas use ``model_config`` with ``from_attributes=True`` so they
can be constructed directly from SQLAlchemy model instances.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------
# Enumerations
# ------------------------------------------------------------------

class ResearchDepth(StrEnum):
    """Controls how thorough the research pipeline should be."""

    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class OutputFormat(StrEnum):
    """Desired output file format for the final report."""

    MARKDOWN = "markdown"
    PDF = "pdf"
    BOTH = "both"


class SessionStatus(StrEnum):
    """Mirror of the database session status enum."""

    PENDING = "pending"
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


# ------------------------------------------------------------------
# Request schemas
# ------------------------------------------------------------------

class ResearchRequest(BaseModel):
    """Payload for creating a new research session."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The research question or topic to investigate.",
    )
    depth: ResearchDepth = Field(
        default=ResearchDepth.STANDARD,
        description="Depth of the research process.",
    )
    include_citations: bool = Field(
        default=True,
        description="Whether to collect and verify citations.",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.MARKDOWN,
        description="Format of the generated report.",
    )


# ------------------------------------------------------------------
# Response schemas
# ------------------------------------------------------------------

class StepDetail(BaseModel):
    """A single agent step within a research session."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_name: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output_data: dict[str, Any] | None = None
    error_message: str | None = None


class ResearchResponse(BaseModel):
    """Full research session response returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    query: str
    status: str
    depth: str = "standard"
    plan: list[Any] = Field(default_factory=list)
    research_results: list[Any] = Field(default_factory=list)
    verified_facts: list[Any] = Field(default_factory=list)
    citations: list[Any] = Field(default_factory=list)
    summary: str = ""
    report: str = ""
    mermaid_diagram: str = ""
    errors: list[str] = Field(default_factory=list)
    steps: list[StepDetail] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SessionSummary(BaseModel):
    """Abbreviated view of a session used in list responses."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    query: str
    status: str
    summary: str = ""
    created_at: datetime | None = None


class SessionListResponse(BaseModel):
    """Paginated list of research sessions."""

    sessions: list[SessionSummary]
    total: int
    skip: int = 0
    limit: int = 20


# ------------------------------------------------------------------
# Streaming / real-time
# ------------------------------------------------------------------

class StreamEvent(BaseModel):
    """Server-Sent Event payload pushed during live research runs."""

    event: str = Field(..., description="Event name (e.g. agent_completed).")
    agent: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Simple health-check response."""

    status: str = "ok"
    version: str = "1.0.0"
    uptime: float = Field(
        default=0.0,
        description="Uptime in seconds since server start.",
    )
