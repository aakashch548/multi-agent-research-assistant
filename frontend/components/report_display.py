"""Report display component with tabs for report, citations, diagram, and raw data."""

from __future__ import annotations

import json

import streamlit as st


def render_report(
    report: str,
    citations: list | None = None,
    mermaid_diagram: str | None = None,
    raw_data: dict | None = None,
) -> None:
    """Render the research report in a tabbed layout."""
    tab_names = ["Report", "Citations", "Diagram", "Raw"]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        _render_report_tab(report)

    with tabs[1]:
        _render_citations_tab(citations)

    with tabs[2]:
        _render_diagram_tab(mermaid_diagram)

    with tabs[3]:
        _render_raw_tab(raw_data)


def _render_report_tab(report: str) -> None:
    """Render the main report markdown content."""
    if not report:
        st.info("No report content available.")
        return

    st.markdown(f'<div class="report-container">', unsafe_allow_html=True)
    st.markdown(report)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_citations_tab(citations: list | None) -> None:
    """Render citations as a formatted list with links."""
    if not citations:
        st.info("No citations available for this report.")
        return

    st.markdown(f"**{len(citations)} source(s) cited:**")
    st.markdown("---")

    for i, citation in enumerate(citations, 1):
        if isinstance(citation, dict):
            title = citation.get("title", f"Source {i}")
            url = citation.get("url", citation.get("source_url", ""))
            snippet = citation.get("snippet", citation.get("description", ""))

            link_html = f'<a href="{url}" target="_blank">{title}</a>' if url else title
            snippet_html = f"<br><small>{snippet}</small>" if snippet else ""

            st.markdown(
                f"""
                <div class="citation-item">
                    <strong>{i}.</strong> {link_html}
                    {snippet_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif isinstance(citation, str):
            st.markdown(
                f"""
                <div class="citation-item">
                    <strong>{i}.</strong> {citation}
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_diagram_tab(mermaid_diagram: str | None) -> None:
    """Render the mermaid diagram as a code block with copy support."""
    if not mermaid_diagram:
        st.info("No diagram available for this report.")
        return

    st.markdown("#### Research Flow Diagram")
    st.markdown(
        "The diagram below shows the research workflow. "
        "Copy the code to render it with any Mermaid-compatible viewer."
    )

    st.markdown(
        f'<div class="mermaid-container"><pre><code>{mermaid_diagram}</code></pre></div>',
        unsafe_allow_html=True,
    )

    st.code(mermaid_diagram, language="mermaid")


def _render_raw_tab(raw_data: dict | None) -> None:
    """Render raw JSON data for debugging or inspection."""
    if not raw_data:
        st.info("No raw data available.")
        return

    st.markdown("#### Raw Response Data")
    st.json(raw_data)

    st.download_button(
        label="Download JSON",
        data=json.dumps(raw_data, indent=2, default=str),
        file_name="research_result.json",
        mime="application/json",
    )
