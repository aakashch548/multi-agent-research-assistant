"""Main orchestration service for research sessions.

Ties together the LangGraph workflow, persistence repositories,
and the API-facing schema layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import markdown as md_lib
import structlog

from backend.core.exceptions import DatabaseError, WorkflowError
from backend.models.database import ResearchSession
from backend.schemas.research import (
    ResearchRequest,
    ResearchResponse,
    SessionListResponse,
    SessionSummary,
    StepDetail,
    StreamEvent,
)
from backend.repositories.session_repository import SessionRepository
from backend.repositories.step_repository import StepRepository
from backend.workflows.research_graph import ResearchWorkflow

logger = structlog.get_logger()


class ResearchService:
    """High-level service orchestrating research workflow execution and persistence.

    Args:
        workflow: A compiled :class:`ResearchWorkflow` instance.
        session_repo: Repository for ``ResearchSession`` records.
        step_repo: Repository for ``ResearchStep`` records.
    """

    def __init__(
        self,
        workflow: ResearchWorkflow,
        session_repo: SessionRepository,
        step_repo: StepRepository,
    ) -> None:
        self._workflow = workflow
        self._sessions = session_repo
        self._steps = step_repo

    # ── Research lifecycle ────────────────────────────────────────────

    async def start_research(
        self, request: ResearchRequest,
    ) -> ResearchResponse:
        """Create a session, execute the workflow, persist results.

        Args:
            request: Validated research request payload.

        Returns:
            A fully populated :class:`ResearchResponse`.

        Raises:
            WorkflowError: If the workflow fails unrecoverably.
            DatabaseError: If persistence fails.
        """
        session_id = str(uuid.uuid4())
        logger.info(
            "research_started",
            session_id=session_id,
            query=request.query[:120],
            depth=request.depth,
        )

        db_session = await self._sessions.create({
            "id": session_id,
            "query": request.query,
            "status": "started",
            "depth": request.depth,
            "metadata": {"depth": request.depth},
        })

        try:
            result = await self._workflow.execute(
                query=request.query,
                session_id=session_id,
                depth=request.depth,
            )

            await self._sessions.update(session_id, {
                "status": result.get("status", "completed"),
                "plan": result.get("plan", []),
                "research_results": result.get("research_results", []),
                "verified_facts": result.get("verified_facts", []),
                "citations": result.get("citations", []),
                "summary": result.get("summary", ""),
                "report": result.get("report", ""),
                "mermaid_diagram": result.get("mermaid_diagram", ""),
                "errors": result.get("errors", []),
            })

            await self._record_agent_steps(session_id, result)

            logger.info(
                "research_completed",
                session_id=session_id,
                status=result.get("status"),
            )
        except WorkflowError:
            await self._sessions.update(session_id, {"status": "failed"})
            raise
        except Exception as exc:
            await self._sessions.update(session_id, {
                "status": "failed",
                "errors": [str(exc)],
            })
            logger.exception("research_failed", session_id=session_id)
            raise WorkflowError(
                f"Research execution failed: {exc}",
                workflow_name="research",
            ) from exc

        return await self.get_session(session_id)

    async def get_session(self, session_id: str) -> ResearchResponse:
        """Retrieve a single session with its steps.

        Args:
            session_id: UUID of the session.

        Returns:
            A :class:`ResearchResponse` populated from the database.

        Raises:
            DatabaseError: If the session is not found.
        """
        db_session = await self._sessions.get_by_id(session_id)
        if db_session is None:
            raise DatabaseError(
                f"Session {session_id} not found",
                operation="get_session",
            )
        return self._to_response(db_session)

    async def list_sessions(
        self, skip: int = 0, limit: int = 20,
    ) -> SessionListResponse:
        """Return a paginated list of research sessions.

        Args:
            skip: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            A :class:`SessionListResponse` with totals for pagination.
        """
        sessions, total = await self._sessions.list_all(skip=skip, limit=limit)
        return SessionListResponse(
            sessions=[
                SessionSummary(
                    session_id=s.id,
                    query=s.query,
                    status=s.status,
                    summary=s.summary or "",
                    created_at=s.created_at,
                )
                for s in sessions
            ],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def stream_research(
        self, request: ResearchRequest,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream research execution, yielding an event per workflow step.

        Args:
            request: Validated research request payload.

        Yields:
            :class:`StreamEvent` instances as each agent produces output.
        """
        session_id = str(uuid.uuid4())
        logger.info(
            "research_stream_started",
            session_id=session_id,
            query=request.query[:120],
        )

        await self._sessions.create({
            "id": session_id,
            "query": request.query,
            "status": "started",
            "depth": request.depth,
            "metadata": {"depth": request.depth},
        })

        yield StreamEvent(
            event="session_created",
            data={"session_id": session_id},
        )

        accumulated: dict[str, Any] = {}
        try:
            async for event in self._workflow.stream(
                query=request.query,
                session_id=session_id,
                depth=request.depth,
            ):
                for node_name, node_output in event.items():
                    accumulated.update(node_output)

                    step = await self._steps.create({
                        "session_id": session_id,
                        "agent_name": node_name,
                        "status": "completed",
                        "output_data": self._safe_serialise(node_output),
                        "started_at": datetime.now(timezone.utc),
                        "completed_at": datetime.now(timezone.utc),
                    })

                    yield StreamEvent(
                        event="agent_completed",
                        agent=node_name,
                        data={
                            "session_id": session_id,
                            "step_id": step.id,
                            "status": node_output.get("status", "running"),
                            **{
                                k: v
                                for k, v in node_output.items()
                                if k not in ("current_agent", "retry_count")
                            },
                        },
                    )

            await self._sessions.update(session_id, {
                "status": accumulated.get("status", "completed"),
                "plan": accumulated.get("plan", []),
                "research_results": accumulated.get("research_results", []),
                "verified_facts": accumulated.get("verified_facts", []),
                "citations": accumulated.get("citations", []),
                "summary": accumulated.get("summary", ""),
                "report": accumulated.get("report", ""),
                "mermaid_diagram": accumulated.get("mermaid_diagram", ""),
                "errors": accumulated.get("errors", []),
            })

            yield StreamEvent(
                event="research_completed",
                data={"session_id": session_id, "status": "completed"},
            )
        except Exception as exc:
            await self._sessions.update(session_id, {
                "status": "failed",
                "errors": [str(exc)],
            })
            yield StreamEvent(
                event="research_failed",
                data={"session_id": session_id, "error": str(exc)},
            )
            logger.exception("research_stream_failed", session_id=session_id)

    async def export_report(
        self, session_id: str, fmt: str = "markdown",
    ) -> str | bytes:
        """Export a completed research report in the requested format.

        Supported formats:
            - ``"markdown"`` — raw Markdown string.
            - ``"html"`` — HTML string rendered from the Markdown report.

        Args:
            session_id: UUID of the session.
            fmt: Target format.

        Returns:
            The rendered report as ``str`` (markdown/html) or ``bytes`` (pdf).

        Raises:
            DatabaseError: If the session is not found.
            ValueError: If the format is unsupported.
        """
        db_session = await self._sessions.get_by_id(session_id)
        if db_session is None:
            raise DatabaseError(
                f"Session {session_id} not found",
                operation="export_report",
            )

        report_md = db_session.report or db_session.summary or ""

        if fmt == "markdown":
            return report_md

        if fmt == "html":
            html_body = md_lib.markdown(
                report_md,
                extensions=["extra", "codehilite", "toc"],
            )
            return self._wrap_html(db_session.query, html_body)

        raise ValueError(f"Unsupported export format: {fmt!r}")

    async def delete_session(self, session_id: str) -> None:
        """Delete a research session and all associated steps.

        Args:
            session_id: UUID of the session to remove.

        Raises:
            DatabaseError: If the session is not found or deletion fails.
        """
        await self._sessions.delete(session_id)
        logger.info("session_deleted_via_service", session_id=session_id)

    # ── Internal helpers ──────────────────────────────────────────────

    async def _record_agent_steps(
        self, session_id: str, result: dict[str, Any],
    ) -> None:
        """Persist a summary step for each agent that ran."""
        agent_order = ["planner", "researcher", "verifier", "summarizer", "writer"]
        now = datetime.now(timezone.utc)
        for agent_name in agent_order:
            output_key = {
                "planner": "plan",
                "researcher": "research_results",
                "verifier": "verified_facts",
                "summarizer": "summary",
                "writer": "report",
            }.get(agent_name)
            output_val = result.get(output_key) if output_key else None
            has_output = bool(output_val) if output_val is not None else False
            try:
                await self._steps.create({
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "status": "completed" if has_output else "skipped",
                    "output_data": self._safe_serialise(
                        {output_key: output_val} if output_key and has_output else {}
                    ),
                    "started_at": now,
                    "completed_at": now,
                })
            except Exception:
                logger.exception(
                    "step_record_failed",
                    session_id=session_id,
                    agent=agent_name,
                )

    @staticmethod
    def _to_response(session: ResearchSession) -> ResearchResponse:
        """Map an ORM session (with steps loaded) to the API schema."""
        steps = [
            StepDetail(
                id=s.id,
                agent_name=s.agent_name,
                status=s.status,
                started_at=s.started_at,
                completed_at=s.completed_at,
                output_data=s.output_data,
                error_message=s.error_message,
            )
            for s in (session.steps or [])
        ]
        return ResearchResponse(
            session_id=session.id,
            query=session.query,
            status=session.status,
            depth=session.depth,
            plan=session.plan or [],
            research_results=session.research_results or [],
            verified_facts=session.verified_facts or [],
            citations=session.citations or [],
            summary=session.summary or "",
            report=session.report or "",
            mermaid_diagram=session.mermaid_diagram or "",
            errors=session.errors or [],
            steps=steps,
            metadata=session.metadata_ or {},
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    @staticmethod
    def _safe_serialise(data: Any) -> dict[str, Any] | list | str | None:
        """Ensure data is JSON-serialisable before persisting."""
        if data is None:
            return None
        if isinstance(data, (dict, list, str, int, float, bool)):
            return data
        return str(data)

    @staticmethod
    def _wrap_html(title: str, body_html: str) -> str:
        """Wrap rendered HTML body in a minimal standalone document."""
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en"><head><meta charset="utf-8">'
            f"<title>{title}</title>"
            "<style>"
            "body{font-family:system-ui,sans-serif;max-width:800px;"
            "margin:2rem auto;padding:0 1rem;line-height:1.6;color:#222}"
            "h1,h2,h3{color:#1a1a2e}"
            "pre{background:#f4f4f4;padding:1rem;overflow-x:auto;border-radius:4px}"
            "code{background:#f4f4f4;padding:0.2em 0.4em;border-radius:3px}"
            "blockquote{border-left:4px solid #ccc;margin:1rem 0;padding:0.5rem 1rem;color:#555}"
            "a{color:#0366d6}"
            "</style></head><body>\n"
            f"{body_html}\n"
            "</body></html>"
        )
