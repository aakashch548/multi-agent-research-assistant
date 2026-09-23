"""Search results display component for external web sources."""

from __future__ import annotations

import streamlit as st


def render_search_response(result: dict) -> None:
    """Render answer and external source cards from a search API response."""
    query = result.get("query", "")
    answer = result.get("answer", "")
    sources = result.get("sources", [])
    demo_mode = result.get("demo_mode", False)
    search_time = result.get("search_time_ms", 0)

    # Status bar
    if demo_mode:
        st.info(
            "Demo mode — showing sample sources. "
            "Add your **OpenAI** and **Tavily** API keys in `backend/.env` "
            "and set `DEMO_MODE=false` for live web search."
        )
    else:
        st.success(f"Found {len(sources)} external source(s) in {search_time:.0f} ms")

    # Answer
    st.markdown("### Answer")
    st.markdown(
        f'<div class="answer-box">{answer}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(answer)

    # External sources
    if sources:
        st.markdown("---")
        st.markdown(f"### External Sources ({len(sources)})")

        for i, source in enumerate(sources, 1):
            title = source.get("title", f"Source {i}")
            url = source.get("url", "")
            content = source.get("content", "")
            score = source.get("score", 0)

            with st.container():
                col_num, col_body = st.columns([0.05, 0.95])
                with col_num:
                    st.markdown(f"**{i}**")
                with col_body:
                    if url:
                        st.markdown(f"#### [{title}]({url})")
                        st.caption(f"{url}  ·  relevance: {score:.0%}")
                    else:
                        st.markdown(f"#### {title}")

                    if content:
                        preview = content[:400] + ("..." if len(content) > 400 else "")
                        st.markdown(preview)

                    if url:
                        st.link_button(
                            "Open source",
                            url,
                            use_container_width=False,
                        )
                st.markdown("---")

    # Query echo
    with st.expander("Search details"):
        st.markdown(f"**Query:** {query}")
        st.markdown(f"**Sources found:** {len(sources)}")
        st.markdown(f"**Search time:** {search_time:.0f} ms")
        st.markdown(f"**Mode:** {'Demo' if demo_mode else 'Live (Tavily)'}")
