"""LangGraph-based multi-agent research workflow.

Defines a stateful graph where each node corresponds to a specialised agent.
Conditional edges implement retry logic, confidence gating, and error recovery.
"""

from __future__ import annotations

from typing import Any

import structlog
from langgraph.graph import END, START, StateGraph

from backend.agents.planner import PlannerAgent
from backend.agents.researcher import ResearcherAgent
from backend.agents.summarizer import SummarizerAgent
from backend.agents.verifier import VerifierAgent
from backend.agents.writer import WriterAgent
from backend.core.exceptions import AgentExecutionError, WorkflowError
from backend.models.state import ResearchState

logger = structlog.get_logger()

_VERIFICATION_CONFIDENCE_THRESHOLD = 0.4


class ResearchWorkflow:
    """LangGraph-based multi-agent research workflow.

    The graph follows the path::

        START -> planner -> researcher -> verifier -> summarizer -> writer -> END

    with conditional back-edges for retries on errors or low-confidence
    verification results.

    Args:
        planner: Optional custom PlannerAgent.
        researcher: Optional custom ResearcherAgent.
        verifier: Optional custom VerifierAgent.
        summarizer: Optional custom SummarizerAgent.
        writer: Optional custom WriterAgent.
    """

    def __init__(
        self,
        planner: PlannerAgent | None = None,
        researcher: ResearcherAgent | None = None,
        verifier: VerifierAgent | None = None,
        summarizer: SummarizerAgent | None = None,
        writer: WriterAgent | None = None,
    ) -> None:
        self.planner = planner or PlannerAgent()
        self.researcher = researcher or ResearcherAgent()
        self.verifier = verifier or VerifierAgent()
        self.summarizer = summarizer or SummarizerAgent()
        self.writer = writer or WriterAgent()
        self.graph = self._build_graph()

    # ── Graph construction ────────────────────────────────────────────

    def _build_graph(self) -> Any:
        """Build and compile the LangGraph workflow with conditional routing."""
        workflow = StateGraph(ResearchState)

        workflow.add_node("planner", self._run_planner)
        workflow.add_node("researcher", self._run_researcher)
        workflow.add_node("verifier", self._run_verifier)
        workflow.add_node("summarizer", self._run_summarizer)
        workflow.add_node("writer", self._run_writer)

        workflow.add_edge(START, "planner")
        workflow.add_conditional_edges("planner", self._route_after_planning)
        workflow.add_conditional_edges("researcher", self._route_after_research)
        workflow.add_conditional_edges("verifier", self._route_after_verification)
        workflow.add_edge("summarizer", "writer")
        workflow.add_edge("writer", END)

        return workflow.compile()

    # ── Node runners ──────────────────────────────────────────────────

    async def _run_planner(self, state: ResearchState) -> dict[str, Any]:
        """Execute the planner agent with error handling."""
        logger.info(
            "workflow_node_started",
            node="planner",
            session_id=state.get("session_id"),
        )
        try:
            result = await self.planner.run(state)
            if result.get("status") == "error":
                result["retry_count"] = state.get("retry_count", 0) + 1
            else:
                result["retry_count"] = 0
            return result
        except Exception as exc:
            logger.exception("planner_node_failed")
            errors = list(state.get("errors") or [])
            errors.append(f"Planner error: {exc}")
            return {
                "errors": errors,
                "current_agent": "planner",
                "status": "error",
                "retry_count": state.get("retry_count", 0) + 1,
            }

    async def _run_researcher(self, state: ResearchState) -> dict[str, Any]:
        """Execute the researcher agent with error handling."""
        logger.info(
            "workflow_node_started",
            node="researcher",
            session_id=state.get("session_id"),
        )
        try:
            result = await self.researcher.run(state)
            if result.get("status") == "error":
                result["retry_count"] = state.get("retry_count", 0) + 1
            else:
                result["retry_count"] = 0
            return result
        except Exception as exc:
            logger.exception("researcher_node_failed")
            errors = list(state.get("errors") or [])
            errors.append(f"Researcher error: {exc}")
            return {
                "errors": errors,
                "current_agent": "researcher",
                "status": "error",
                "retry_count": state.get("retry_count", 0) + 1,
            }

    async def _run_verifier(self, state: ResearchState) -> dict[str, Any]:
        """Execute the verifier agent with error handling."""
        logger.info(
            "workflow_node_started",
            node="verifier",
            session_id=state.get("session_id"),
        )
        try:
            result = await self.verifier.run(state)
            if result.get("status") == "error":
                result["retry_count"] = state.get("retry_count", 0) + 1
            else:
                result["retry_count"] = 0
            return result
        except Exception as exc:
            logger.exception("verifier_node_failed")
            errors = list(state.get("errors") or [])
            errors.append(f"Verifier error: {exc}")
            return {
                "errors": errors,
                "current_agent": "verifier",
                "status": "error",
                "retry_count": state.get("retry_count", 0) + 1,
            }

    async def _run_summarizer(self, state: ResearchState) -> dict[str, Any]:
        """Execute the summarizer agent with error handling."""
        logger.info(
            "workflow_node_started",
            node="summarizer",
            session_id=state.get("session_id"),
        )
        try:
            result = await self.summarizer.run(state)
            return result
        except Exception as exc:
            logger.exception("summarizer_node_failed")
            errors = list(state.get("errors") or [])
            errors.append(f"Summarizer error: {exc}")
            return {
                "errors": errors,
                "current_agent": "summarizer",
                "status": "error",
                "summary": "Summary generation failed due to an internal error.",
            }

    async def _run_writer(self, state: ResearchState) -> dict[str, Any]:
        """Execute the writer agent with error handling."""
        logger.info(
            "workflow_node_started",
            node="writer",
            session_id=state.get("session_id"),
        )
        try:
            result = await self.writer.run(state)
            return result
        except Exception as exc:
            logger.exception("writer_node_failed")
            errors = list(state.get("errors") or [])
            errors.append(f"Writer error: {exc}")
            return {
                "errors": errors,
                "current_agent": "writer",
                "status": "completed_with_errors",
                "report": state.get("summary", "Report generation failed."),
                "mermaid_diagram": "",
            }

    # ── Routing functions ─────────────────────────────────────────────

    def _route_after_planning(self, state: ResearchState) -> str:
        """Decide the next node after the planner.

        Retries the planner on error if retries remain, otherwise
        proceeds to the researcher.
        """
        if state.get("status") == "error":
            retry = state.get("retry_count", 0)
            max_r = state.get("max_retries", 3)
            if retry < max_r:
                logger.warning(
                    "retrying_planner",
                    retry_count=retry,
                    max_retries=max_r,
                )
                return "planner"
            logger.error("planner_max_retries_exceeded")
            raise WorkflowError(
                "Planner failed after maximum retries",
                workflow_name="research",
                step="planner",
            )

        plan = state.get("plan", [])
        if not plan:
            retry = state.get("retry_count", 0)
            max_r = state.get("max_retries", 3)
            if retry < max_r:
                logger.warning("planner_empty_plan_retrying", retry_count=retry)
                return "planner"

        return "researcher"

    def _route_after_research(self, state: ResearchState) -> str:
        """Decide the next node after the researcher.

        Retries the researcher if no results were found and retries
        remain, otherwise proceeds to the verifier.
        """
        results = state.get("research_results", [])
        if state.get("status") == "error" or not results:
            retry = state.get("retry_count", 0)
            max_r = state.get("max_retries", 3)
            if retry < max_r:
                logger.warning(
                    "retrying_researcher",
                    retry_count=retry,
                    max_retries=max_r,
                    has_results=bool(results),
                )
                return "researcher"
            if not results:
                logger.error("researcher_no_results_after_retries")

        return "verifier"

    def _route_after_verification(self, state: ResearchState) -> str:
        """Decide the next node after the verifier.

        Re-routes to the researcher if average verification confidence
        is below the threshold and retries remain.
        """
        if state.get("status") == "error":
            retry = state.get("retry_count", 0)
            max_r = state.get("max_retries", 3)
            if retry < max_r:
                logger.warning("retrying_verifier_on_error", retry_count=retry)
                return "researcher"

        verified = state.get("verified_facts", [])
        if verified:
            confidences = [
                f.get("confidence", 0.0)
                for f in verified
                if isinstance(f, dict)
            ]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            if avg_conf < _VERIFICATION_CONFIDENCE_THRESHOLD:
                retry = state.get("retry_count", 0)
                max_r = state.get("max_retries", 3)
                if retry < max_r:
                    logger.warning(
                        "low_confidence_rerouting_to_researcher",
                        avg_confidence=round(avg_conf, 3),
                        threshold=_VERIFICATION_CONFIDENCE_THRESHOLD,
                        retry_count=retry,
                    )
                    return "researcher"
                logger.warning(
                    "low_confidence_but_retries_exhausted",
                    avg_confidence=round(avg_conf, 3),
                )

        return "summarizer"

    # ── Public execution API ──────────────────────────────────────────

    async def execute(
        self,
        query: str,
        session_id: str,
        depth: str = "standard",
    ) -> ResearchState:
        """Execute the full research workflow synchronously (awaited).

        Args:
            query: The research question.
            session_id: Unique session identifier.
            depth: Research depth — ``"quick"``, ``"standard"``, or ``"deep"``.

        Returns:
            The final ``ResearchState`` after all nodes have run.

        Raises:
            WorkflowError: If the workflow fails unrecoverably.
        """
        initial_state: ResearchState = {
            "query": query,
            "plan": [],
            "research_results": [],
            "verified_facts": [],
            "citations": [],
            "summary": "",
            "report": "",
            "mermaid_diagram": "",
            "errors": [],
            "metadata": {"depth": depth},
            "current_agent": "",
            "retry_count": 0,
            "max_retries": 3,
            "session_id": session_id,
            "status": "started",
        }

        logger.info(
            "workflow_execution_started",
            session_id=session_id,
            query=query[:120],
            depth=depth,
        )

        try:
            result = await self.graph.ainvoke(initial_state)
            logger.info(
                "workflow_execution_completed",
                session_id=session_id,
                status=result.get("status"),
            )
            return result
        except WorkflowError:
            raise
        except Exception as exc:
            logger.exception("workflow_execution_failed", session_id=session_id)
            raise WorkflowError(
                f"Workflow execution failed: {exc}",
                workflow_name="research",
            ) from exc

    async def stream(
        self,
        query: str,
        session_id: str,
        depth: str = "standard",
    ):
        """Stream workflow execution, yielding state updates per node.

        Yields:
            Dicts keyed by node name with the state updates produced
            by that node.
        """
        initial_state: ResearchState = {
            "query": query,
            "plan": [],
            "research_results": [],
            "verified_facts": [],
            "citations": [],
            "summary": "",
            "report": "",
            "mermaid_diagram": "",
            "errors": [],
            "metadata": {"depth": depth},
            "current_agent": "",
            "retry_count": 0,
            "max_retries": 3,
            "session_id": session_id,
            "status": "started",
        }

        logger.info(
            "workflow_stream_started",
            session_id=session_id,
            query=query[:120],
            depth=depth,
        )

        try:
            async for event in self.graph.astream(
                initial_state, stream_mode="updates"
            ):
                yield event
        except WorkflowError:
            raise
        except Exception as exc:
            logger.exception("workflow_stream_failed", session_id=session_id)
            raise WorkflowError(
                f"Workflow streaming failed: {exc}",
                workflow_name="research",
            ) from exc
