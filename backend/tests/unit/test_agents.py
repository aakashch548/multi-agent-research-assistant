"""Unit tests for all research agents."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agents.planner import PlannerAgent
from backend.agents.researcher import ResearcherAgent
from backend.agents.summarizer import SummarizerAgent
from backend.agents.verifier import VerifierAgent
from backend.agents.writer import WriterAgent
from backend.models.state import ResearchState


def _make_mock_chain(return_value: str) -> MagicMock:
    """Create a mocked langchain chain that returns the given string."""
    chain = MagicMock()
    chain.ainvoke = AsyncMock(return_value=return_value)
    return chain


# ------------------------------------------------------------------
# PlannerAgent
# ------------------------------------------------------------------


class TestPlannerAgent:
    @pytest.mark.asyncio
    async def test_creates_plan(self) -> None:
        llm_response = json.dumps(
            {
                "plan": [
                    "What is quantum computing?",
                    "How does it differ from classical computing?",
                    "What are current applications?",
                ],
                "reasoning": "Decomposed into fundamentals, comparison, and applications.",
            }
        )

        agent = PlannerAgent(llm=MagicMock())
        agent._chain = _make_mock_chain(llm_response)

        state: ResearchState = {
            "query": "Explain quantum computing",
            "plan": [],
            "metadata": {},
            "errors": [],
            "retry_count": 0,
            "max_retries": 3,
            "session_id": "test",
            "status": "started",
        }

        result = await agent.run(state)

        assert result["status"] == "completed"
        assert len(result["plan"]) == 3
        assert "plan_reasoning" in result["metadata"]

    @pytest.mark.asyncio
    async def test_empty_query_raises(self) -> None:
        agent = PlannerAgent(llm=MagicMock())

        state: ResearchState = {"query": "", "errors": [], "status": "started"}
        result = await agent.run(state)

        assert result["status"] == "error"
        assert len(result["errors"]) > 0


# ------------------------------------------------------------------
# ResearcherAgent
# ------------------------------------------------------------------


class TestResearcherAgent:
    @pytest.mark.asyncio
    async def test_returns_results(self, mock_tavily: MagicMock) -> None:
        llm_response = json.dumps(
            {
                "findings": "AI is revolutionizing healthcare.",
                "sources": [
                    {"url": "https://example.com", "title": "AI Health", "relevance_score": 0.9}
                ],
            }
        )

        agent = ResearcherAgent(llm=MagicMock(), tavily_tool=mock_tavily)
        agent._chain = _make_mock_chain(llm_response)

        state: ResearchState = {
            "query": "AI in healthcare",
            "plan": ["How is AI used in diagnostics?"],
            "errors": [],
            "status": "started",
        }

        result = await agent.run(state)

        assert result["status"] == "completed"
        assert len(result["research_results"]) == 1
        assert len(result["citations"]) >= 1


# ------------------------------------------------------------------
# VerifierAgent
# ------------------------------------------------------------------


class TestVerifierAgent:
    @pytest.mark.asyncio
    async def test_checks_facts(self) -> None:
        llm_response = json.dumps(
            {
                "verified_facts": [
                    {
                        "claim": "AI improves diagnostic accuracy.",
                        "confidence": 0.92,
                        "supporting_sources": ["https://example.com"],
                        "contradicting_sources": [],
                        "verified": True,
                    }
                ],
                "summary": "Claims are well-supported.",
            }
        )

        agent = VerifierAgent(llm=MagicMock())
        agent._chain = _make_mock_chain(llm_response)

        state: ResearchState = {
            "query": "AI diagnostics",
            "research_results": [
                {"query": "q1", "findings": "AI improves diagnostics.", "sources": []}
            ],
            "errors": [],
            "metadata": {},
            "status": "started",
        }

        result = await agent.run(state)

        assert result["status"] == "completed"
        assert len(result["verified_facts"]) == 1
        assert result["verified_facts"][0]["verified"] is True


# ------------------------------------------------------------------
# SummarizerAgent
# ------------------------------------------------------------------


class TestSummarizerAgent:
    @pytest.mark.asyncio
    async def test_creates_summary(self) -> None:
        llm_response = json.dumps(
            {
                "summary": "AI significantly improves healthcare outcomes.",
                "key_findings": ["Better diagnostics", "Faster drug discovery"],
                "confidence_score": 0.88,
            }
        )

        agent = SummarizerAgent(llm=MagicMock())
        agent._chain = _make_mock_chain(llm_response)

        state: ResearchState = {
            "query": "AI in healthcare",
            "verified_facts": [
                {"claim": "AI improves diagnostics.", "confidence": 0.9, "verified": True}
            ],
            "errors": [],
            "metadata": {},
            "status": "started",
        }

        result = await agent.run(state)

        assert result["status"] == "completed"
        assert "summary" in result
        assert len(result["summary"]) > 0


# ------------------------------------------------------------------
# WriterAgent
# ------------------------------------------------------------------


class TestWriterAgent:
    @pytest.mark.asyncio
    async def test_generates_report(self) -> None:
        report_text = "# Research Report\n\n## Executive Summary\n\nAI transforms healthcare."
        llm_response = json.dumps(
            {"report": report_text, "mermaid_diagram": "graph TD\n  A-->B"}
        )

        agent = WriterAgent(llm=MagicMock())
        agent._chain = _make_mock_chain(llm_response)

        state: ResearchState = {
            "query": "AI in healthcare",
            "summary": "AI improves healthcare.",
            "verified_facts": [],
            "citations": [],
            "errors": [],
            "metadata": {},
            "status": "started",
        }

        result = await agent.run(state)

        assert result["status"] == "completed"
        assert "report" in result
        assert len(result["report"]) > 0


# ------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------


class TestAgentErrorHandling:
    @pytest.mark.asyncio
    async def test_agent_captures_error_in_state(self) -> None:
        agent = PlannerAgent(llm=MagicMock())
        agent._chain = _make_mock_chain("not valid json {{{")

        mock_settings = MagicMock()
        mock_settings.use_offline_mode = False

        state: ResearchState = {
            "query": "test query",
            "errors": [],
            "status": "started",
            "metadata": {"depth": "standard"},
        }

        with patch("backend.agents.planner.get_settings", return_value=mock_settings):
            result = await agent.run(state)

        assert result["status"] == "error"
        assert any("planner" in e.lower() for e in result["errors"])
