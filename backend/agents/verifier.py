"""VerifierAgent — fact-checks research findings for accuracy and reliability."""

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
You are a rigorous fact-checker and critical analyst. Given a set of research
findings, assess each claim for accuracy, reliability, and source quality.

For each finding you must:
1. Identify the core claim.
2. Check for internal contradictions across findings.
3. Assess source reliability.
4. Score your confidence in the claim (0.0-1.0).

Return your output as a JSON object with exactly two keys:
  "verified_facts" – a JSON array of objects, each with:
      "claim" (str), "confidence" (float 0.0-1.0),
      "supporting_sources" (list of URLs), "contradicting_sources" (list of URLs),
      "verified" (bool)
  "summary" – a one-sentence overview of verification results.

Return ONLY valid JSON. No markdown fences, no extra text."""

HUMAN_PROMPT = """\
Research query: {query}

Findings to verify:
{findings}

Sources available:
{sources}"""


class VerifierAgent(BaseAgent):
    """Cross-references research results to verify accuracy and flag issues.

    Produces a list of verified facts with confidence scores and
    verification statistics for downstream agents.
    """

    name: str = "verifier"

    def __init__(self, llm: Any | None = None) -> None:
        settings = get_settings()
        default_llm = llm or ChatOpenAI(
            model=settings.openai_model,
            temperature=0.1,
            api_key=settings.openai_api_key or "demo-key",
        )
        super().__init__(name="verifier", llm=default_llm)
        self._chain: Any | None = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _invoke_llm(
        self, query: str, findings: str, sources: str
    ) -> dict[str, Any]:
        """Call the LLM with retry logic and parse JSON response."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=HUMAN_PROMPT.format(
                    query=query, findings=findings, sources=sources
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
        """Verify research findings and return annotated facts."""
        query = state.get("query", "")
        results = state.get("research_results", [])
        settings = get_settings()

        if not results:
            self.logger.warning("no_findings_to_verify")
            return {
                "verified_facts": [],
                "metadata": {
                    **state.get("metadata", {}),
                    "verification_stats": {
                        "total": 0,
                        "verified": 0,
                        "average_confidence": 0.0,
                    },
                },
            }

        self.logger.info("verification_started", finding_count=len(results))

        findings_text = "\n\n".join(
            f"Finding {i}: {r.get('findings', str(r))}\n"
            f"  Sub-question: {r.get('query', 'N/A')}"
            for i, r in enumerate(results, 1)
        )

        sources_text = "\n".join(
            f"- {s.get('url', s.get('source_url', 'N/A'))}: {s.get('title', 'Untitled')}"
            for r in results
            for s in r.get("sources", [])
        )

        try:
            if settings.use_offline_mode:
                verified_facts = [
                    {
                        "claim": r.get("findings", str(r)),
                        "confidence": 0.85,
                        "supporting_sources": [
                            s.get("url", "") for s in r.get("sources", [])
                        ],
                        "contradicting_sources": [],
                        "verified": True,
                    }
                    for r in results
                ]
            elif self._chain is not None:
                raw = await self._chain.ainvoke(
                    {"query": query, "findings": findings_text, "sources": sources_text}
                )
                parsed = json.loads(raw)
                verified_facts = parsed.get("verified_facts", [])
            else:
                parsed = await self._invoke_llm(query, findings_text, sources_text)
                verified_facts = parsed.get("verified_facts", [])
        except Exception as exc:
            self.logger.warning("verification_parse_fallback", error=str(exc))
            verified_facts = [
                {
                    "claim": r.get("findings", str(r)),
                    "confidence": 0.5,
                    "supporting_sources": [
                        s.get("url", "") for s in r.get("sources", [])
                    ],
                    "contradicting_sources": [],
                    "verified": False,
                }
                for r in results
            ]

        total = len(verified_facts)
        num_verified = sum(1 for f in verified_facts if f.get("verified"))
        avg_confidence = (
            sum(f.get("confidence", 0.0) for f in verified_facts) / total
            if total
            else 0.0
        )

        metadata = dict(state.get("metadata", {}))
        metadata["verification_stats"] = {
            "total": total,
            "verified": num_verified,
            "unverified": total - num_verified,
            "average_confidence": round(avg_confidence, 3),
        }

        self.logger.info(
            "verification_completed",
            total=total,
            verified=num_verified,
            avg_confidence=round(avg_confidence, 3),
        )

        return {
            "verified_facts": verified_facts,
            "metadata": metadata,
        }
