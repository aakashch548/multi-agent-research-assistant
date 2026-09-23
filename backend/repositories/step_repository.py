"""Repository for persisting and retrieving ``ResearchStep`` records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.exceptions import DatabaseError
from backend.models.database import ResearchStep

logger = structlog.get_logger()


class StepRepository:
    """Async repository wrapping all ``ResearchStep`` database operations.

    Args:
        session_factory: An ``async_sessionmaker`` that produces
            :class:`~sqlalchemy.ext.asyncio.AsyncSession` instances.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, step_data: dict[str, Any]) -> ResearchStep:
        """Insert a new research step.

        Args:
            step_data: Column values.  Must include ``"session_id"`` and
                ``"agent_name"``.

        Returns:
            The newly created ``ResearchStep`` ORM instance.

        Raises:
            DatabaseError: On any database failure.
        """
        async with self._session_factory() as db:
            try:
                step = ResearchStep(**step_data)
                db.add(step)
                await db.commit()
                await db.refresh(step)
                logger.info(
                    "step_created",
                    step_id=step.id,
                    session_id=step.session_id,
                    agent=step.agent_name,
                )
                return step
            except Exception as exc:
                await db.rollback()
                logger.exception("step_create_failed")
                raise DatabaseError(
                    f"Failed to create step: {exc}",
                    operation="create_step",
                ) from exc

    async def get_by_session(self, session_id: str) -> list[ResearchStep]:
        """Fetch all steps belonging to a session, ordered by creation time.

        Args:
            session_id: UUID of the parent research session.

        Returns:
            A list of ``ResearchStep`` instances (may be empty).

        Raises:
            DatabaseError: On any database failure.
        """
        async with self._session_factory() as db:
            try:
                stmt = (
                    select(ResearchStep)
                    .where(ResearchStep.session_id == session_id)
                    .order_by(ResearchStep.created_at.asc())
                )
                result = await db.execute(stmt)
                steps = list(result.scalars().all())
                logger.debug(
                    "steps_fetched",
                    session_id=session_id,
                    count=len(steps),
                )
                return steps
            except Exception as exc:
                logger.exception(
                    "step_get_by_session_failed", session_id=session_id,
                )
                raise DatabaseError(
                    f"Failed to fetch steps for session {session_id}: {exc}",
                    operation="get_steps",
                ) from exc

    async def update_status(
        self,
        step_id: str,
        status: str,
        output: dict[str, Any] | None = None,
    ) -> ResearchStep:
        """Update the status (and optionally output) of a step.

        Automatically sets ``completed_at`` when the status transitions
        to ``"completed"`` or ``"failed"``.

        Args:
            step_id: UUID of the step.
            status: New status value (e.g. ``"running"``, ``"completed"``,
                ``"failed"``).
            output: Optional output data dict to persist.

        Returns:
            The updated ``ResearchStep`` instance.

        Raises:
            DatabaseError: If the step is not found or the update fails.
        """
        async with self._session_factory() as db:
            try:
                stmt = select(ResearchStep).where(ResearchStep.id == step_id)
                result = await db.execute(stmt)
                step = result.scalar_one_or_none()
                if step is None:
                    raise DatabaseError(
                        f"Step {step_id} not found",
                        operation="update_step_status",
                    )

                step.status = status
                if output is not None:
                    step.output_data = output

                now = datetime.now(timezone.utc)
                if status == "running" and step.started_at is None:
                    step.started_at = now
                if status in ("completed", "failed"):
                    step.completed_at = now
                if status == "failed" and output and "error" in output:
                    step.error_message = str(output["error"])

                await db.commit()
                await db.refresh(step)
                logger.info(
                    "step_status_updated",
                    step_id=step_id,
                    status=status,
                )
                return step
            except DatabaseError:
                await db.rollback()
                raise
            except Exception as exc:
                await db.rollback()
                logger.exception("step_status_update_failed", step_id=step_id)
                raise DatabaseError(
                    f"Failed to update step {step_id}: {exc}",
                    operation="update_step_status",
                ) from exc
