"""SQLAlchemy ORM models for persisting research sessions and steps."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


class ResearchSession(Base):
    """Persisted record of a single research workflow execution."""

    __tablename__ = "research_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="started")
    depth: Mapped[str] = mapped_column(String(50), default="standard")
    plan: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    research_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    verified_facts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    report: Mapped[str] = mapped_column(Text, default="")
    mermaid_diagram: Mapped[str] = mapped_column(Text, default="")
    errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True,
    )

    steps: Mapped[list[ResearchStep]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        order_by="ResearchStep.created_at",
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary (no lazy-load of steps)."""
        return {
            "id": self.id,
            "query": self.query,
            "status": self.status,
            "depth": self.depth,
            "plan": self.plan or [],
            "research_results": self.research_results or [],
            "verified_facts": self.verified_facts or [],
            "citations": self.citations or [],
            "summary": self.summary or "",
            "report": self.report or "",
            "mermaid_diagram": self.mermaid_diagram or "",
            "errors": self.errors or [],
            "metadata": self.metadata_ or {},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ResearchStep(Base):
    """A single agent execution step within a research session."""

    __tablename__ = "research_steps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    session: Mapped[ResearchSession] = relationship(back_populates="steps")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "input_data": self.input_data or {},
            "output_data": self.output_data,
            "error_message": self.error_message,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
        }
