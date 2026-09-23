"""Report export in multiple formats (Markdown, HTML, PDF).

Uses Jinja2 for HTML templating and weasyprint for PDF generation,
with graceful fallback when weasyprint is unavailable.
"""

from __future__ import annotations

import html as html_mod
from datetime import datetime, timezone
from typing import Any

import structlog
from jinja2 import BaseLoader, Environment

logger = structlog.get_logger()

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>
  :root { --accent: #2563eb; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    line-height: 1.7; color: #1e293b; max-width: 860px;
    margin: 2rem auto; padding: 0 1.5rem;
  }
  h1 { font-size: 1.8rem; margin-bottom: .6rem; color: var(--accent); }
  h2 { font-size: 1.35rem; margin: 1.6rem 0 .5rem; border-bottom: 2px solid #e2e8f0; padding-bottom: .25rem; }
  h3 { font-size: 1.1rem; margin: 1.2rem 0 .4rem; }
  p  { margin-bottom: .8rem; }
  a  { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .meta { color: #64748b; font-size: .85rem; margin-bottom: 1.5rem; }
  .toc { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1.5rem; }
  .toc ul { list-style: none; padding-left: 1rem; }
  .toc li { margin: .25rem 0; }
  .toc a { font-size: .95rem; }
  blockquote { border-left: 3px solid var(--accent); padding-left: 1rem; color: #475569; margin: .8rem 0; }
  code { background: #f1f5f9; padding: .15rem .35rem; border-radius: 4px; font-size: .9em; }
  pre { background: #f1f5f9; padding: 1rem; border-radius: 6px; overflow-x: auto; margin: .8rem 0; }
  pre code { background: none; padding: 0; }
  .references { margin-top: 2rem; padding-top: 1rem; border-top: 2px solid #e2e8f0; }
  .references li { margin-bottom: .4rem; font-size: .92rem; }
  .mermaid-container { text-align: center; margin: 1rem 0; }
  @media print { body { max-width: 100%; margin: 0; } }
</style>
</head>
<body>
  <h1>{{ title }}</h1>
  <div class="meta">
    {% if author %}Author: {{ author }} | {% endif %}
    Generated: {{ generated_date }}
  </div>

  {% if toc_items %}
  <nav class="toc">
    <strong>Table of Contents</strong>
    <ul>
      {% for item in toc_items %}
      <li><a href="#section-{{ loop.index }}">{{ item }}</a></li>
      {% endfor %}
    </ul>
  </nav>
  {% endif %}

  <div class="content">{{ content }}</div>

  {% if citations %}
  <div class="references">
    <h2>References</h2>
    <ol>
      {% for cite in citations %}
      <li>{{ cite.author | default("N/A", true) }} ({{ cite.date | default("n.d.", true) }}).
          <em>{{ cite.title }}</em>.
          {% if cite.url %}<a href="{{ cite.url }}">{{ cite.url }}</a>{% endif %}
      </li>
      {% endfor %}
    </ol>
  </div>
  {% endif %}
</body>
</html>
"""

_JINJA_ENV = Environment(loader=BaseLoader(), autoescape=True)


class ReportExporter:
    """Exports research reports in Markdown, HTML, and PDF formats.

    Leverages Jinja2 templates for HTML generation and optionally
    weasyprint for PDF rendering.
    """

    def export_markdown(
        self,
        report: str,
        citations: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> str:
        """Export the report as a Markdown string.

        Args:
            report: The body of the report in Markdown.
            citations: List of citation dicts.
            metadata: Report metadata (``title``, ``author``, etc.).

        Returns:
            Full Markdown document with title, body, and references.
        """
        title = metadata.get("title", "Research Report")
        author = metadata.get("author", "")
        date_str = metadata.get("date", self._now_iso())

        parts: list[str] = [
            f"# {title}",
            "",
        ]
        if author:
            parts.append(f"**Author:** {author}  ")
        parts.append(f"**Date:** {date_str}")
        parts.append("")

        toc_items = self._extract_headings(report)
        if toc_items:
            parts.append("## Table of Contents")
            parts.append("")
            for idx, heading in enumerate(toc_items, 1):
                parts.append(f"{idx}. {heading}")
            parts.append("")

        parts.append("---")
        parts.append("")
        parts.append(report)

        if citations:
            parts.append("")
            parts.append("---")
            parts.append("")
            parts.append("## References")
            parts.append("")
            for idx, cite in enumerate(citations, 1):
                author_c = cite.get("author", "N/A")
                date_c = cite.get("date", "n.d.")
                title_c = cite.get("title", "Untitled")
                url_c = cite.get("url", cite.get("source_url", ""))
                parts.append(
                    f"[{idx}] {author_c} ({date_c}). *{title_c}*. {url_c}"
                )

        logger.info("report_exported_markdown", title=title)
        return "\n".join(parts)

    def export_html(
        self,
        report: str,
        citations: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> str:
        """Export the report as a styled HTML document.

        Args:
            report: Report body in Markdown (basic Markdown-to-HTML
                    conversion is applied).
            citations: Citation dicts.
            metadata: Report metadata.

        Returns:
            Complete HTML document string.
        """
        title = metadata.get("title", "Research Report")
        context = {
            "title": title,
            "author": metadata.get("author", ""),
            "generated_date": metadata.get("date", self._now_iso()),
            "content": self._markdown_to_html(report),
            "toc_items": self._extract_headings(report),
            "citations": citations,
        }

        rendered = self._render_template(_HTML_TEMPLATE, context)
        logger.info("report_exported_html", title=title)
        return rendered

    def export_pdf(
        self,
        report: str,
        citations: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> bytes:
        """Export the report as a PDF.

        Attempts to use weasyprint; falls back to a UTF-8-encoded HTML
        bytes object if weasyprint is not installed.

        Args:
            report: Report body in Markdown.
            citations: Citation dicts.
            metadata: Report metadata.

        Returns:
            PDF file content as bytes.
        """
        html_content = self.export_html(report, citations, metadata)

        try:
            from weasyprint import HTML as WeasyprintHTML  # type: ignore[import-untyped]

            pdf_bytes: bytes = WeasyprintHTML(string=html_content).write_pdf()
            logger.info("report_exported_pdf", engine="weasyprint")
            return pdf_bytes
        except ImportError:
            logger.warning(
                "weasyprint_not_available_falling_back_to_html_bytes"
            )
            return html_content.encode("utf-8")
        except Exception:
            logger.exception("pdf_generation_failed")
            raise

    def _render_template(
        self, template_str: str, context: dict[str, Any]
    ) -> str:
        """Render a Jinja2 template from a raw string.

        Args:
            template_str: The Jinja2 template source.
            context: Template context variables.

        Returns:
            Rendered HTML string.
        """
        try:
            template = _JINJA_ENV.from_string(template_str)
            return template.render(**context)
        except Exception:
            logger.exception("template_rendering_failed")
            raise

    def _generate_mermaid_svg(self, mermaid_code: str) -> str:
        """Wrap Mermaid source in an HTML container for client-side rendering.

        Actual SVG rendering is left to a Mermaid JS runtime in the
        browser / PDF renderer.

        Args:
            mermaid_code: Valid Mermaid diagram source.

        Returns:
            HTML snippet wrapping the Mermaid code.
        """
        escaped = html_mod.escape(mermaid_code)
        return (
            '<div class="mermaid-container">'
            f'<pre class="mermaid">{escaped}</pre>'
            "</div>"
        )

    @staticmethod
    def _extract_headings(text: str) -> list[str]:
        """Pull Markdown headings (## …) from text for a TOC."""
        import re

        headings: list[str] = []
        for match in re.finditer(r"^#{2,3}\s+(.+)$", text, re.MULTILINE):
            headings.append(match.group(1).strip())
        return headings

    @staticmethod
    def _markdown_to_html(md: str) -> str:
        """Minimal Markdown-to-HTML conversion for common constructs."""
        import re

        text = html_mod.escape(md)

        text = re.sub(
            r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE
        )
        text = re.sub(
            r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE
        )
        text = re.sub(
            r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE
        )
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        text = re.sub(
            r"`(.+?)`", r"<code>\1</code>", text
        )
        text = re.sub(r"^- (.+)$", r"<li>\1</li>", text, flags=re.MULTILINE)
        text = re.sub(
            r"((?:<li>.+</li>\n?)+)",
            r"<ul>\1</ul>",
            text,
        )
        text = re.sub(r"^&gt; (.+)$", r"<blockquote>\1</blockquote>", text, flags=re.MULTILINE)

        paragraphs: list[str] = []
        for block in re.split(r"\n{2,}", text):
            block = block.strip()
            if not block:
                continue
            if block.startswith("<"):
                paragraphs.append(block)
            else:
                paragraphs.append(f"<p>{block}</p>")

        return "\n".join(paragraphs)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
