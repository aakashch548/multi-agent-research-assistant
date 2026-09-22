"""WriterAgent – generates a structured research report and Mermaid diagram."""

from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.agents.base import BaseAgent
from backend.core.config import get_settings
from backend.models.state import ResearchState
from backend.tools.citation_extractor import CitationExtractor, Citation
from backend.tools.diagram_generator import DiagramGenerator

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

REPORT_SYSTEM_PROMPT = """\
You are a professional research analyst writing a formal research report. \
Write in clear, authoritative prose. Use inline citations in [n] format \
where n corresponds to the source number.

The report MUST follow this exact structure:

# {title}

## Executive Summary
(2–3 sentence overview)

## Introduction
(Context and scope of the research)

## Methodology
(Brief description of the research process)

## Findings
(Detailed findings organised by theme, with inline citations)

## Analysis
(Critical analysis, patterns, implications)

## Conclusions
(Key takeaways and recommendations)

Guidelines:
- Be specific; avoid vague generalisations.
- Prioritise high-confidence verified facts.
- Flag any caveats or limitations.
- Maintain neutral, analytical tone throughout.
- Target 800–1500 words."""

REPORT_HUMAN_PROMPT = """\
Research query: {query}

Executive summary: {summary}

Verified facts:
{verified_facts}

Available citations:
{citations}

Write the complete research report now."""

DIAGRAM_SYSTEM_PROMPT = """\
You are a diagramming expert. Given a research query, sub-tasks, and key \
findings, generate a Mermaid diagram that visualises the relationships \
between concepts discovered during research.

The diagram should be a flowchart (graph TD) or mind-map showing how the \
research query branches into themes and findings.

Return ONLY the raw Mermaid code. No markdown fences, no explanation."""

DIAGRAM_HUMAN_PROMPT = """\
Query: {query}

Research sub-tasks:
{plan}

Key findings:
{findings}

Generate the Mermaid diagram."""


class WriterAgent(BaseAgent):
    """Generates a full structured research report and a Mermaid diagram."""

    name: str = "writer"

    def __init__(self, llm: Any | None = None) -> None:
        settings = get_settings()
        default_llm = llm or ChatOpenAI(
            model=settings.openai_model,
            temperature=0.3,
            api_key=settings.openai_api_key or "demo-key",
        )
        super().__init__(name="writer", llm=default_llm)
        self._chain: Any | None = None

        self._report_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(REPORT_SYSTEM_PROMPT),
                HumanMessagePromptTemplate.from_template(REPORT_HUMAN_PROMPT),
            ]
        )
        self._report_chain = (
            self._report_prompt | self.llm | StrOutputParser()
        )

        self._diagram_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(DIAGRAM_SYSTEM_PROMPT),
                HumanMessagePromptTemplate.from_template(DIAGRAM_HUMAN_PROMPT),
            ]
        )
        self._diagram_chain = (
            self._diagram_prompt | self.llm | StrOutputParser()
        )

        self._citation_extractor = CitationExtractor()
        self._diagram_generator = DiagramGenerator()

    # ---- formatting helpers ------------------------------------------------

    @staticmethod
    def _offline_report(
        query: str,
        summary: str,
        verified_facts: list[dict],
        citations: list[dict],
        plan: list[Any],
    ) -> str:
        """Structured markdown report from web-backed findings (no LLM)."""
        intro = (
            f"This report synthesizes **{len(verified_facts)}** verified finding(s) "
            f"from live web search across **{len(plan)}** research sub-questions."
        )
        findings_sections: list[str] = []
        for i, fact in enumerate(verified_facts, 1):
            claim = fact.get("claim", str(fact))
            conf = fact.get("confidence", 0.0)
            srcs = fact.get("supporting_sources") or []
            src_line = ""
            if srcs:
                links = ", ".join(f"<{u}>" for u in srcs[:3] if u)
                src_line = f"\n\n*Sources:* {links}"
            findings_sections.append(
                f"### Finding {i}\n\n{claim}\n\n"
                f"*Confidence: {conf:.0%}*{src_line}"
            )

        bib_lines: list[str] = []
        seen: set[str] = set()
        for cit in citations:
            url = cit.get("source_url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            title = cit.get("title", url)
            bib_lines.append(f"- [{title}]({url})")

        bibliography = (
            "\n".join(bib_lines) if bib_lines else "- (No external URLs captured)"
        )

        return f"""# Research Report: {query}

## Executive Summary

{summary}

## Introduction

{intro}

## Methodology

The system decomposed your question into focused sub-queries, searched the web
for each (Tavily when configured, otherwise DuckDuckGo), verified findings,
and assembled this narrative report.

## Detailed Findings

{chr(10).join(findings_sections) if findings_sections else "No findings were produced."}

## Analysis

The findings above reflect what current public web sources emphasize about
"{query}". Cross-check critical claims against primary sources before
high-stakes decisions.

## Conclusions

{summary}

## References

{bibliography}
"""

    def _format_verified_facts(self, verified_facts: list[dict]) -> str:
        """Render verified facts for the LLM context window."""
        if not verified_facts:
            return "(no verified facts)"
        lines: list[str] = []
        for idx, fact in enumerate(verified_facts, 1):
            claim = fact.get("claim", "N/A")
            confidence = fact.get("confidence", 0.0)
            sources = ", ".join(fact.get("supporting_sources", []))
            verified_marker = "VERIFIED" if fact.get("verified") else "UNVERIFIED"
            lines.append(
                f"[{idx}] ({verified_marker}, conf={confidence:.2f}) {claim}"
                f"\n    Sources: {sources or 'none'}"
            )
        return "\n\n".join(lines)

    def _format_citations(self, citations: list[dict]) -> str:
        """Render citations for the LLM context window."""
        if not citations:
            return "(no citations)"
        lines: list[str] = []
        for idx, cit in enumerate(citations, 1):
            title = cit.get("title", "Untitled")
            url = cit.get("source_url", "N/A")
            lines.append(f"[{idx}] {title} – {url}")
        return "\n".join(lines)

    def _format_plan(self, plan: list[Any]) -> str:
        """Format the research plan as a bullet list."""
        lines: list[str] = []
        for task in plan:
            if isinstance(task, dict):
                lines.append(f"- {task.get('task', task)}")
            else:
                lines.append(f"- {task}")
        return "\n".join(lines)

    def _format_key_findings(self, metadata: dict) -> str:
        """Format key findings from metadata."""
        findings = metadata.get("key_findings", [])
        if not findings:
            return "(no key findings)"
        return "\n".join(f"- {f}" for f in findings)

    def _build_sources_for_extractor(
        self, citations: list[dict], verified_facts: list[dict]
    ) -> list[dict]:
        """Build source dicts compatible with ``CitationExtractor``."""
        sources: list[dict] = []
        seen_urls: set[str] = set()

        for cit in citations:
            url = cit.get("source_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources.append(
                    {
                        "title": cit.get("title", "Untitled"),
                        "url": url,
                        "content": cit.get("text", ""),
                    }
                )

        for fact in verified_facts:
            for src in fact.get("supporting_sources", []):
                if isinstance(src, str) and src not in seen_urls:
                    seen_urls.add(src)
                    sources.append(
                        {
                            "title": src,
                            "url": src,
                            "content": fact.get("claim", ""),
                        }
                    )

        return sources

    # ---- LLM calls ---------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _generate_report(
        self,
        query: str,
        summary: str,
        facts_text: str,
        citations_text: str,
    ) -> str:
        """Generate the markdown report via LLM."""
        return await self._report_chain.ainvoke(
            {
                "query": query,
                "summary": summary,
                "verified_facts": facts_text,
                "citations": citations_text,
            }
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _generate_diagram_llm(
        self,
        query: str,
        plan_text: str,
        findings_text: str,
    ) -> str:
        """Generate a Mermaid diagram via LLM."""
        raw: str = await self._diagram_chain.ainvoke(
            {
                "query": query,
                "plan": plan_text,
                "findings": findings_text,
            }
        )
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0].strip()
        return cleaned

    @staticmethod
    def _demo_diagram(query: str, plan: list[Any], metadata: dict) -> str:
        """Build a static Mermaid diagram for demo mode."""
        lines = ["graph TD", f'  Q["{query[:40]}"]']
        for i, task in enumerate(plan):
            label = task.get("task", str(task)) if isinstance(task, dict) else str(task)
            node = f"T{i}"
            lines.append(f'  {node}["{label[:30]}"]')
            lines.append(f"  Q --> {node}")
        lines.append('  R["Final Report"]')
        if plan:
            lines.append(f"  T{len(plan) - 1} --> R")
        else:
            lines.append("  Q --> R")
        return "\n".join(lines)

    async def _build_diagram(self, state: ResearchState) -> str:
        """Build a Mermaid diagram, falling back to the static generator.

        Tries an LLM-generated concept diagram first.  If that fails or
        produces invalid Mermaid, falls back to ``DiagramGenerator`` from
        ``backend.tools.diagram_generator``.
        """
        query = state.get("query", "")
        plan = state.get("plan", [])
        metadata = state.get("metadata", {})

        settings = get_settings()
        if settings.use_offline_mode:
            return self._demo_diagram(query, plan, metadata)

        try:
            diagram = await self._generate_diagram_llm(
                query=query,
                plan_text=self._format_plan(plan),
                findings_text=self._format_key_findings(metadata),
            )
            if diagram and self._diagram_generator._validate_mermaid(diagram):
                return diagram
        except Exception as exc:
            self.logger.warning("llm_diagram_failed", error=str(exc))

        steps = [
            {
                "id": "query",
                "label": f"Research: {query[:50]}",
                "type": "start",
                "next": [f"task_{i}" for i in range(len(plan))],
            }
        ]
        for i, task in enumerate(plan):
            label = task.get("task", str(task)) if isinstance(task, dict) else str(task)
            steps.append(
                {
                    "id": f"task_{i}",
                    "label": label[:60],
                    "next": ["report"],
                }
            )
        steps.append(
            {"id": "report", "label": "Final Report", "type": "end", "next": []}
        )

        return self._diagram_generator.generate_workflow_diagram(steps)

    # ---- main execute ------------------------------------------------------

    async def execute(self, state: ResearchState) -> dict:
        """Produce the final research report and Mermaid diagram.

        Returns
        -------
        dict
            ``report`` – full markdown report with formatted references.
            ``mermaid_diagram`` – Mermaid code for the concept diagram.
        """
        summary: str = state.get("summary", "")
        verified_facts: list[dict] = state.get("verified_facts", [])
        citations: list[dict] = state.get("citations", [])
        query: str = state.get("query", "")

        if not summary and not verified_facts:
            raise ValueError(
                "No summary or verified facts available. "
                "Run SummarizerAgent first."
            )

        settings = get_settings()
        self.logger.info("report_generation_started", demo=settings.use_offline_mode)

        facts_text = self._format_verified_facts(verified_facts)
        citations_text = self._format_citations(citations)

        if settings.use_offline_mode:
            report_raw = self._offline_report(
                query,
                summary,
                verified_facts,
                citations,
                state.get("plan", []),
            )
        elif self._chain is not None:
            raw = await self._chain.ainvoke({"query": query, "summary": summary})
            try:
                parsed = json.loads(raw)
                report_raw = parsed.get("report", raw)
            except json.JSONDecodeError:
                report_raw = raw
        else:
            report_raw = await self._generate_report(
                query=query,
                summary=summary,
                facts_text=facts_text,
                citations_text=citations_text,
            )

        sources = self._build_sources_for_extractor(citations, verified_facts)
        extracted = self._citation_extractor.extract_citations(
            report_raw, sources
        )
        report = self._citation_extractor.format_citations_inline(
            report_raw, extracted
        )
        bibliography = self._citation_extractor.generate_bibliography(extracted)
        if bibliography:
            report = report + "\n\n" + bibliography

        diagram = await self._build_diagram(state)

        self.logger.info(
            "report_generation_completed",
            report_length=len(report),
            has_diagram=bool(diagram),
        )

        return {
            "report": report,
            "mermaid_diagram": diagram,
        }
