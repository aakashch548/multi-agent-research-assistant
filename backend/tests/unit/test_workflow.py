"""Unit tests for the LangGraph research workflow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.workflows.research_graph import ResearchWorkflow


def _mock_agent(name: str, output: dict) -> MagicMock:
    """Create a mocked agent that returns the given output dict."""
    agent = MagicMock()
    agent.name = name
    agent.run = AsyncMock(
        return_value={**output, "current_agent": name, "status": "completed"}
    )
    return agent


class TestResearchWorkflow:
    @pytest.mark.asyncio
    async def test_full_execution(self) -> None:
        planner = _mock_agent("PlannerAgent", {"plan": ["sub-q1", "sub-q2"]})
        researcher = _mock_agent(
            "ResearcherAgent",
            {
                "research_results": [{"query": "sub-q1", "findings": "f1", "sources": []}],
                "citations": [{"text": "f1", "source_url": "https://a.com"}],
            },
        )
        verifier = _mock_agent(
            "VerifierAgent",
            {
                "verified_facts": [{"claim": "f1", "confidence": 0.9, "verified": True}],
                "metadata": {"verification_stats": {"average_confidence": 0.9}},
            },
        )
        summarizer = _mock_agent(
            "SummarizerAgent",
            {"summary": "AI improves healthcare."},
        )
        writer = _mock_agent(
            "WriterAgent",
            {"report": "# Report", "mermaid_diagram": "graph TD\n  A-->B"},
        )

        wf = ResearchWorkflow(
            planner=planner,
            researcher=researcher,
            verifier=verifier,
            summarizer=summarizer,
            writer=writer,
        )

        result = await wf.execute(
            query="AI in healthcare",
            session_id="test-001",
        )

        assert result.get("report") == "# Report"
        assert result.get("summary") == "AI improves healthcare."
        planner.run.assert_called_once()
        researcher.run.assert_called_once()
        verifier.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_agent_error(self) -> None:
        from backend.core.exceptions import WorkflowError

        planner = _mock_agent("PlannerAgent", {"plan": []})
        planner.run = AsyncMock(
            return_value={
                "plan": [],
                "errors": ["PlannerAgent: LLM failed"],
                "current_agent": "PlannerAgent",
                "status": "error",
            }
        )

        wf = ResearchWorkflow(planner=planner)
        with pytest.raises(WorkflowError, match="Planner failed after maximum retries"):
            await wf.execute(query="test", session_id="test-err")

    @pytest.mark.asyncio
    async def test_routing_after_planning_with_plan(self) -> None:
        wf = ResearchWorkflow()
        state = {
            "status": "completed",
            "plan": ["q1"],
            "retry_count": 0,
            "max_retries": 3,
        }
        route = wf._route_after_planning(state)
        assert route == "researcher"

    @pytest.mark.asyncio
    async def test_routing_after_planning_error_no_retries(self) -> None:
        from backend.core.exceptions import WorkflowError

        wf = ResearchWorkflow()
        state = {
            "status": "error",
            "plan": [],
            "retry_count": 3,
            "max_retries": 3,
        }
        with pytest.raises(WorkflowError):
            wf._route_after_planning(state)
