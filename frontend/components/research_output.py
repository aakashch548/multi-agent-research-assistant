"""Rich research result layout for Multi-Agent Research mode."""



from __future__ import annotations



import streamlit as st



from components.report_display import render_report

from components.workflow_viz import render_workflow_from_steps





def render_research_result(result: dict, *, inline: bool = True) -> None:

    """Display summary, full text report, sources, and optional metadata."""

    summary = (result.get("summary") or "").strip()

    report = (result.get("report") or "").strip()

    citations = result.get("citations") or []

    plan = result.get("plan") or []

    steps = result.get("steps") or []

    errors = result.get("errors") or []



    if summary:

        st.markdown(

            f'<div class="summary-box"><strong>Executive Summary</strong><br><br>'

            f"{_escape_html(summary)}</div>",

            unsafe_allow_html=True,

        )



    body = report or summary

    if body:

        st.markdown("#### Research Report")
        with st.container(border=True):
            st.markdown(body)



        st.download_button(

            label="Download report (.md)",

            data=body,

            file_name="research_report.md",

            mime="text/markdown",

            use_container_width=False,

        )

    elif inline:

        st.info("Research finished but no report text was returned.")



    if citations:

        st.markdown("#### Sources")

        cols = st.columns(min(3, len(citations)))

        for i, cit in enumerate(citations[:9]):

            if not isinstance(cit, dict):

                continue

            title = cit.get("title") or f"Source {i + 1}"

            url = cit.get("source_url") or cit.get("url") or ""

            with cols[i % len(cols)]:

                if url:

                    st.markdown(

                        f'<div class="source-card">'

                        f'<a href="{url}" target="_blank">{_escape_html(title[:80])}</a>'

                        f"</div>",

                        unsafe_allow_html=True,

                    )

                else:

                    st.markdown(

                        f'<div class="source-card">{_escape_html(title[:80])}</div>',

                        unsafe_allow_html=True,

                    )



    if plan:

        with st.expander(f"Research plan ({len(plan)} sub-questions)", expanded=False):

            for i, item in enumerate(plan, 1):

                text = item if isinstance(item, str) else item.get("question", str(item))

                st.markdown(f"{i}. {text}")



    if steps:

        with st.expander("Agent pipeline", expanded=False):

            render_workflow_from_steps(steps)



    if report and (citations or result.get("mermaid_diagram")):

        with st.expander("Report extras (citations, diagram, JSON)", expanded=False):

            render_report(

                report=report,

                citations=citations,

                mermaid_diagram=result.get("mermaid_diagram"),

                raw_data=result,

            )



    if errors:

        st.warning("Some steps encountered errors: " + "; ".join(errors))





def _escape_html(text: str) -> str:

    return (

        text.replace("&", "&amp;")

        .replace("<", "&lt;")

        .replace(">", "&gt;")

        .replace('"', "&quot;")

    )


