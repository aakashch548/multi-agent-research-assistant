"""Abstract base class for all research-pipeline agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

from backend.models.state import ResearchState

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Every agent in the pipeline inherits from this class.

    Subclasses implement :meth:`execute`, which receives the current
    workflow state and returns a partial dict of state updates.
    :meth:`run` wraps ``execute`` with uniform status and error handling.
    """

    name: str = "base"

    def __init__(self, name: str | None = None, llm: Any | None = None) -> None:
        self.name = name or self.__class__.name
        self.llm = llm
        self.logger = structlog.get_logger(self.name)

    async def __call__(self, state: ResearchState) -> dict[str, Any]:
        """Allow agents to be called directly by LangGraph nodes."""
        return await self.run(state)

    async def run(self, state: ResearchState) -> dict[str, Any]:
        """Execute the agent logic and return state updates with status."""
        try:
            result = await self.execute(state)
            return {
                **result,
                "current_agent": self.name,
                "status": result.get("status", "completed"),
            }
        except Exception as exc:
            self.logger.exception("agent_execution_failed", agent=self.name)
            errors = list(state.get("errors") or [])
            errors.append(f"{self.name}: {exc}")
            return {
                "errors": errors,
                "current_agent": self.name,
                "status": "error",
            }

    @abstractmethod
    async def execute(self, state: ResearchState) -> dict[str, Any]:
        """Execute the agent logic and return state updates.

        Args:
            state: Current workflow state.

        Returns:
            A dict whose keys are valid ``ResearchState`` fields.
        """
        ...
