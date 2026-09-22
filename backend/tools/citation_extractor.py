"""Citation extraction and formatting for research reports.

Supports APA, inline, and numbered citation styles with automatic
bibliography generation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass(slots=True)
class Citation:
    """Represents a single citation extracted from source material."""

    id: str
    text: str
    source_url: str
    title: str
    author: str = "Unknown"
    date: str = ""
    relevance_score: float = 0.0
    verified: bool = False


class CitationExtractor:
    """Extracts citations from text and formats them in various styles.

    Matches quoted passages and factual claims in the text against a
    provided list of source documents, then generates properly formatted
    citation strings.
    """

    def extract_citations(
        self,
        text: str,
        sources: list[dict[str, Any]],
    ) -> list[Citation]:
        """Identify claims in *text* attributable to the given sources.

        Uses keyword overlap between sentences and source content to
        determine which source backs each claim.

        Args:
            text: The report / answer text to scan.
            sources: List of source dicts (``title``, ``url``, ``content``,
                     and optionally ``author`` / ``date``).

        Returns:
            De-duplicated list of Citation objects ordered by relevance.
        """
        if not text or not sources:
            return []

        citations: list[Citation] = []
        seen_urls: set[str] = set()

        sentences = self._split_sentences(text)

        for source_idx, source in enumerate(sources):
            source_url: str = source.get("url", source.get("source_url", ""))
            source_title: str = source.get("title", "Untitled")
            source_content: str = source.get("content", "")
            author: str = source.get("author", "Unknown")
            date: str = source.get("date", "")

            if source_url in seen_urls:
                continue

            best_score = 0.0
            best_sentence = ""

            for sentence in sentences:
                score = self._compute_overlap(sentence, source_content)
                if score > best_score:
                    best_score = score
                    best_sentence = sentence

            if best_score > 0.15:
                citation = Citation(
                    id=f"cite-{source_idx + 1}",
                    text=best_sentence.strip(),
                    source_url=source_url,
                    title=source_title,
                    author=author,
                    date=date or self._current_year(),
                    relevance_score=round(best_score, 4),
                    verified=best_score > 0.4,
                )
                citations.append(citation)
                seen_urls.add(source_url)

        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        logger.info("citations_extracted", count=len(citations))
        return citations

    def format_citations_apa(self, citations: list[Citation]) -> str:
        """Format a list of citations in APA style.

        Args:
            citations: The citations to format.

        Returns:
            A newline-separated string of APA references.
        """
        if not citations:
            return ""

        lines: list[str] = []
        for c in citations:
            author_part = c.author if c.author != "Unknown" else c.title
            date_part = c.date or "n.d."
            line = f"{author_part} ({date_part}). {c.title}. Retrieved from {c.source_url}"
            lines.append(line)

        return "\n".join(lines)

    def format_citations_inline(
        self,
        text: str,
        citations: list[Citation],
    ) -> str:
        """Insert numbered inline citations into the text.

        Each citation's matched sentence is appended with a bracketed
        reference number, e.g. ``[1]``.

        Args:
            text: The original report text.
            citations: Extracted citations.

        Returns:
            The text with inline reference markers inserted.
        """
        if not citations:
            return text

        result = text
        for idx, c in enumerate(citations, start=1):
            if c.text and c.text in result:
                result = result.replace(
                    c.text, f"{c.text} [{idx}]", 1
                )

        return result

    def generate_bibliography(self, citations: list[Citation]) -> str:
        """Generate a full numbered bibliography section.

        Args:
            citations: The citations to include.

        Returns:
            Formatted bibliography string with header.
        """
        if not citations:
            return ""

        lines: list[str] = ["## References", ""]
        for idx, c in enumerate(citations, start=1):
            author = c.author if c.author != "Unknown" else "N/A"
            date = c.date or "n.d."
            verified_marker = " ✓" if c.verified else ""
            line = (
                f"[{idx}] {author} ({date}). "
                f"*{c.title}*. "
                f"{c.source_url}{verified_marker}"
            )
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Naively split text into sentences."""
        raw = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in raw if len(s.strip()) > 20]

    @staticmethod
    def _compute_overlap(sentence: str, source_content: str) -> float:
        """Word-level Jaccard similarity between sentence and source."""
        if not sentence or not source_content:
            return 0.0

        def tokens(t: str) -> set[str]:
            return {w.lower() for w in re.findall(r"\b\w{3,}\b", t)}

        s_tokens = tokens(sentence)
        c_tokens = tokens(source_content)
        if not s_tokens or not c_tokens:
            return 0.0

        intersection = s_tokens & c_tokens
        union = s_tokens | c_tokens
        return len(intersection) / len(union)

    @staticmethod
    def _current_year() -> str:
        return str(datetime.now(tz=timezone.utc).year)
