"""SummarizerAgent — distills verified facts into a concise executive summary."""

from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.agents.base import BaseAgent
from backend.core.config import get_settings
from backend.models.state import ResearchState

SYSTEM_PROMPT = """\
You are an expert research summarizer. Given a collection of verified facts,
their confidence scores, and the original research query, produce a
structured summary.

Return your output as a JSON object with exactly three keys:
  "summary" – a 2-3 sentence executive overview of the research findings.
  "key_findings" – a JSON array of 3-7 key finding strings (bullet points).
  "confidence_score" – an overall confidence score (float 0.0-1.0) reflecting
      the aggregate reliability of the findings.

Be concise, accurate, and professional. Cite source quality where relevant.
Return ONLY valid JSON. No markdown fences, no extra text."""

HUMAN_PROMPT = """\
Research query: {query}

Verified facts:
{facts}

Citations:
{citations}

Produce the structured summary now."""


class SummarizerAgent(BaseAgent):
    """Produces an executive summary with key findings and confidence score."""

    name: str = "summarizer"

    def __init__(self, llm: Any | None = None) -> None:
        settings = get_settings()
        default_llm = llm or ChatOpenAI(
            model=settings.openai_model,
            temperature=0.2,
            api_key=settings.openai_api_key or "demo-key",
        )
        super().__init__(name="summarizer", llm=default_llm)
        self._chain: Any | None = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _invoke_llm(
        self, query: str, facts: str, citations: str
    ) -> dict[str, Any]:
        """Call the LLM with retry logic and parse JSON response."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=HUMAN_PROMPT.format(
                    query=query, facts=facts, citations=citations
                )
            ),
        ]
        response = await self.llm.ainvoke(messages)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw.strip())

    async def execute(self, state: ResearchState) -> dict[str, Any]:
        """Summarize verified facts into an executive overview.

        Returns
        -------
        dict
            ``summary`` – executive summary string.
            ``metadata`` – updated with ``key_findings`` and ``confidence_score``.
        """
        query = state.get("query", "")
        verified_facts = state.get("verified_facts", [])
        citations = state.get("citations", [])

        if not verified_facts:
            self.logger.warning("no_facts_to_summarize")
            return {
                "summary": "No verified facts available for summarization.",
                "metadata": {
                    **state.get("metadata", {}),
                    "key_findings": [],
                    "confidence_score": 0.0,
                },
            }

        self.logger.info(
            "summarization_started",
            facts_count=len(verified_facts),
            citations_count=len(citations),
        )

        facts_text = "\n\n".join(
            f"Fact {i}: {f.get('claim', str(f))}\n"
            f"  Confidence: {f.get('confidence', 'N/A')}\n"
            f"  Verified: {f.get('verified', 'N/A')}"
            for i, f in enumerate(verified_facts, 1)
        )

        citations_text = "\n".join(
            f"- [{i}] {c.get('title', 'Untitled')} — {c.get('source_url', 'N/A')}"
            for i, c in enumerate(citations, 1)
        )

        settings = get_settings()
        try:
            if settings.use_offline_mode:
                key_findings = [
                    f.get("claim", str(f))[:280] for f in verified_facts[:7]
                ]
                preview = key_findings[0] if key_findings else query
                summary = (
                    f"Web research on '{query}' surfaced {len(verified_facts)} "
                    f"verified theme(s). In brief: {preview[:400]}"
                )
                confidence_score = sum(
                    f.get("confidence", 0.7) for f in verified_facts
                ) / len(verified_facts)
            elif self._chain is not None:
                raw = await self._chain.ainvoke(
                    {"query": query, "facts": facts_text, "citations": citations_text}
                )
                parsed = json.loads(raw)
                summary = parsed.get("summary", "")
                key_findings = parsed.get("key_findings", [])
                confidence_score = float(parsed.get("confidence_score", 0.0))
            else:
                parsed = await self._invoke_llm(query, facts_text, citations_text)
                summary = parsed.get("summary", "")
                key_findings = parsed.get("key_findings", [])
                confidence_score = float(parsed.get("confidence_score", 0.0))
        except Exception as exc:
            self.logger.warning("summarization_parse_fallback", error=str(exc))
            summary = "; ".join(
                f.get("claim", str(f)) for f in verified_facts[:5]
            )
            key_findings = [f.get("claim", str(f)) for f in verified_facts[:5]]
            confidence_score = sum(
                f.get("confidence", 0.5) for f in verified_facts
            ) / len(verified_facts)

        metadata = dict(state.get("metadata", {}))
        metadata["key_findings"] = key_findings
        metadata["confidence_score"] = round(confidence_score, 3)

        self.logger.info(
            "summarization_completed",
            summary_length=len(summary),
            key_findings_count=len(key_findings),
        )

        return {
            "summary": summary,
            "metadata": metadata,
        }
