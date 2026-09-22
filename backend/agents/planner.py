"""Planner agent — decomposes a research query into actionable sub-tasks."""

from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from backend.agents.base import BaseAgent
from backend.core.config import get_settings
from backend.models.state import ResearchState

logger = structlog.get_logger()

_SYSTEM_PROMPT = """\
You are a research planning specialist. Given a research query, decompose it
into a list of concrete, actionable sub-tasks that a research team can execute
in sequence.

Return ONLY a JSON object with:
- "plan": array of sub-question strings
- "reasoning": brief explanation of the decomposition strategy

Example:
{
  "plan": [
    "What are recent developments in topic X?",
    "What are the main benefits and risks?"
  ],
  "reasoning": "Split into developments and impact analysis."
}
"""


class PlannerAgent(BaseAgent):
    """Uses an LLM to break down the research query into sub-tasks."""

    name: str = "planner"

    def __init__(self, llm: Any | None = None, model: str | None = None) -> None:
        super().__init__(name="planner", llm=llm)
        if llm is None:
            settings = get_settings()
            self._llm = ChatOpenAI(
                model=model or settings.openai_model,
                temperature=0.2,
                api_key=settings.openai_api_key or "demo-key",
            )
        self._chain: Any | None = None

    async def execute(self, state: ResearchState) -> dict[str, Any]:
        """Produce a structured research plan from the user query."""
        query = state.get("query", "")
        if not query or not query.strip():
            raise ValueError("Research query must not be empty")

        depth = (state.get("metadata") or {}).get("depth", "standard")
        settings = get_settings()

        logger.info("planner_started", query=query[:120], depth=depth)

        if settings.use_offline_mode:
            plan = self._demo_plan(query, depth)
            metadata = dict(state.get("metadata") or {})
            metadata["plan_reasoning"] = (
                "Demo mode: generated a sample research plan without API calls."
            )
            logger.info("planner_completed", task_count=len(plan), demo=True)
            return {"plan": plan, "metadata": metadata}

        depth_instruction = {
            "quick": "Create 2-3 focused sub-tasks.",
            "standard": "Create 3-5 thorough sub-tasks.",
            "deep": "Create 5-8 comprehensive sub-tasks covering every angle.",
        }.get(depth, "Create 3-5 thorough sub-tasks.")

        if self._chain is not None:
            raw = await self._chain.ainvoke(
                {"query": query, "depth_instruction": depth_instruction}
            )
            parsed = self._parse_response(raw, strict=True)
        else:
            messages = [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(
                    content=f"Research query: {query}\n\nInstruction: {depth_instruction}"
                ),
            ]
            response = await self._llm.ainvoke(messages)
            raw = response.content.strip()
            parsed = self._parse_response(raw, strict=False)
        plan = parsed["plan"]
        metadata = dict(state.get("metadata") or {})
        if parsed.get("reasoning"):
            metadata["plan_reasoning"] = parsed["reasoning"]

        logger.info("planner_completed", task_count=len(plan))
        return {"plan": plan, "metadata": metadata}

    @staticmethod
    def _demo_plan(query: str, depth: str) -> list[str]:
        """Return a canned plan for offline demos."""
        base = [
            f"What is the current state of research on: {query[:80]}?",
            f"What are the key benefits and applications related to {query[:60]}?",
            f"What challenges or limitations exist around {query[:60]}?",
        ]
        if depth == "quick":
            return base[:2]
        if depth == "deep":
            return base + [
                f"What recent breakthroughs have occurred in {query[:50]}?",
                f"How might {query[:50]} evolve over the next 5 years?",
            ]
        return base

    @staticmethod
    def _parse_response(raw: str, *, strict: bool = False) -> dict[str, Any]:
        """Parse LLM output into plan and reasoning."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        try:
            data = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            if strict:
                raise
            logger.warning("planner_json_parse_failed", raw=raw[:200])
            return {"plan": [raw[:200]], "reasoning": ""}

        if isinstance(data, list):
            return {"plan": data, "reasoning": ""}

        plan = data.get("plan", [])
        if not isinstance(plan, list):
            plan = [str(plan)]
        return {"plan": plan, "reasoning": data.get("reasoning", "")}
