"""Repository for persisting and retrieving ``ResearchSession`` records."""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from backend.core.exceptions import DatabaseError
from backend.models.database import ResearchSession

logger = structlog.get_logger()


class SessionRepository:
    """Async repository wrapping all ``ResearchSession`` database operations.

    Args:
        session_factory: An ``async_sessionmaker`` that produces
            :class:`~sqlalchemy.ext.asyncio.AsyncSession` instances.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, session_data: dict[str, Any]) -> ResearchSession:
        """Insert a new research session.

        Args:
            session_data: Column values for the new row.  Must include
                at least ``"query"``.

        Returns:
            The newly created ``ResearchSession`` ORM instance.

        Raises:
            DatabaseError: On any database failure.
        """
        async with self._session_factory() as db:
            try:
                metadata_val = session_data.pop("metadata", None)
                session = ResearchSession(**session_data)
                if metadata_val is not None:
                    session.metadata_ = metadata_val
                db.add(session)
                await db.commit()
                await db.refresh(session)
                logger.info("session_created", session_id=session.id)
                return session
            except Exception as exc:
                await db.rollback()
                logger.exception("session_create_failed")
                raise DatabaseError(
                    f"Failed to create session: {exc}",
                    operation="create_session",
                ) from exc

    async def get_by_id(self, session_id: str) -> ResearchSession | None:
        """Fetch a single session by primary key, eagerly loading steps.

        Args:
            session_id: UUID string of the session.

        Returns:
            The matching ``ResearchSession`` or ``None``.

        Raises:
            DatabaseError: On any database failure.
        """
        async with self._session_factory() as db:
            try:
                stmt = (
                    select(ResearchSession)
                    .options(selectinload(ResearchSession.steps))
                    .where(ResearchSession.id == session_id)
                )
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                if session is None:
                    logger.debug("session_not_found", session_id=session_id)
                return session
            except Exception as exc:
                logger.exception("session_get_failed", session_id=session_id)
                raise DatabaseError(
                    f"Failed to fetch session {session_id}: {exc}",
                    operation="get_session",
                ) from exc

    async def update(
        self,
        session_id: str,
        data: dict[str, Any],
    ) -> ResearchSession:
        """Update an existing session with the provided fields.

        Args:
            session_id: UUID of the session to update.
            data: Mapping of column names to new values.

        Returns:
            The updated ``ResearchSession`` instance.

        Raises:
            DatabaseError: If the session is not found or the update fails.
        """
        async with self._session_factory() as db:
            try:
                stmt = (
                    select(ResearchSession)
                    .options(selectinload(ResearchSession.steps))
                    .where(ResearchSession.id == session_id)
                )
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                if session is None:
                    raise DatabaseError(
                        f"Session {session_id} not found",
                        operation="update_session",
                    )

                metadata_val = data.pop("metadata", None)
                for key, value in data.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                if metadata_val is not None:
                    session.metadata_ = metadata_val

                await db.commit()
                await db.refresh(session)
                logger.info("session_updated", session_id=session_id)
                return session
            except DatabaseError:
                await db.rollback()
                raise
            except Exception as exc:
                await db.rollback()
                logger.exception("session_update_failed", session_id=session_id)
                raise DatabaseError(
                    f"Failed to update session {session_id}: {exc}",
                    operation="update_session",
                ) from exc

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[ResearchSession], int]:
        """Return a paginated list of sessions ordered by creation date.

        Args:
            skip: Number of rows to skip.
            limit: Maximum rows to return.

        Returns:
            A tuple of (sessions_list, total_count).

        Raises:
            DatabaseError: On any database failure.
        """
        async with self._session_factory() as db:
            try:
                count_stmt = select(func.count()).select_from(ResearchSession)
                total = (await db.execute(count_stmt)).scalar_one()

                stmt = (
                    select(ResearchSession)
                    .options(selectinload(ResearchSession.steps))
                    .order_by(ResearchSession.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                )
                result = await db.execute(stmt)
                sessions = list(result.scalars().all())
                return sessions, total
            except Exception as exc:
                logger.exception("session_list_failed")
                raise DatabaseError(
                    f"Failed to list sessions: {exc}",
                    operation="list_sessions",
                ) from exc

    async def delete(self, session_id: str) -> None:
        """Delete a session and its associated steps (cascade).

        Args:
            session_id: UUID of the session to delete.

        Raises:
            DatabaseError: If the session is not found or deletion fails.
        """
        async with self._session_factory() as db:
            try:
                stmt = select(ResearchSession).where(
                    ResearchSession.id == session_id
                )
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                if session is None:
                    raise DatabaseError(
                        f"Session {session_id} not found",
                        operation="delete_session",
                    )
                await db.delete(session)
                await db.commit()
                logger.info("session_deleted", session_id=session_id)
            except DatabaseError:
                await db.rollback()
                raise
            except Exception as exc:
                await db.rollback()
                logger.exception("session_delete_failed", session_id=session_id)
                raise DatabaseError(
                    f"Failed to delete session {session_id}: {exc}",
                    operation="delete_session",
                ) from exc
