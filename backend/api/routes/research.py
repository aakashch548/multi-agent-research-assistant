"""Research session endpoints for starting, monitoring, and exporting research."""

from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

import structlog

from backend.core.exceptions import DatabaseError
from backend.services.research_service import ResearchService
from backend.api.dependencies import get_research_service
from backend.schemas.research import (
    ResearchRequest,
    ResearchResponse,
    SessionListResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=ResearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new research session",
)
async def start_research(
    request: ResearchRequest,
    service: ResearchService = Depends(get_research_service),
) -> ResearchResponse:
    """Initiate a new autonomous research workflow.

    Accepts a research query and optional configuration parameters.
    Returns a session object with an ID that can be used to track progress
    and retrieve results.
    """
    logger.info("research_start_requested", query=request.query)
    result = await service.start_research(request)
    logger.info("research_started", session_id=result.session_id)
    return result


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List research sessions",
)
async def list_sessions(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return"),
    service: ResearchService = Depends(get_research_service),
) -> SessionListResponse:
    """Retrieve a paginated list of all research sessions.

    Results are ordered by creation time descending (most recent first).
    """
    return await service.list_sessions(skip=skip, limit=limit)


@router.get(
    "/{session_id}",
    response_model=ResearchResponse,
    summary="Get research session details",
)
async def get_session(
    session_id: str,
    service: ResearchService = Depends(get_research_service),
) -> ResearchResponse:
    """Retrieve full details and results for a specific research session."""
    try:
        return await service.get_session(session_id)
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session '{session_id}' not found.",
        ) from exc


@router.get(
    "/{session_id}/stream",
    summary="Stream research progress via SSE",
)
async def stream_research(
    session_id: str,
    service: ResearchService = Depends(get_research_service),
) -> StreamingResponse:
    """Server-Sent Events endpoint for live research progress updates.

    Streams structured JSON events as agents execute, providing
    real-time visibility into the multi-agent workflow.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event in service.stream_research(session_id):
                data = event.model_dump_json() if hasattr(event, "model_dump_json") else json.dumps(event)
                yield f"data: {data}\n\n"
        except Exception as exc:
            logger.error(
                "stream_error",
                session_id=session_id,
                error=str(exc),
            )
            error_payload = json.dumps({
                "event": "error",
                "message": str(exc),
            })
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{session_id}/export/{format}",
    summary="Export research report",
)
async def export_report(
    session_id: str,
    format: str,
    service: ResearchService = Depends(get_research_service),
) -> StreamingResponse:
    """Export a completed research session as a downloadable report.

    Supported formats: ``markdown``, ``pdf``.
    """
    if format not in ("markdown", "pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format '{format}'. Use 'markdown' or 'pdf'.",
        )

    content = await service.export_report(session_id, format)

    if format == "markdown":
        return StreamingResponse(
            iter([content]),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="research_{session_id}.md"',
            },
        )

    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="research_{session_id}.pdf"',
        },
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a research session",
)
async def delete_session(
    session_id: str,
    service: ResearchService = Depends(get_research_service),
) -> None:
    """Permanently delete a research session and all associated data."""
    try:
        await service.get_session(session_id)
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session '{session_id}' not found.",
        ) from exc
    await service.delete_session(session_id)
    logger.info("research_session_deleted", session_id=session_id)
