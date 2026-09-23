"""Dual-mode UI: quick web-search chat and full multi-agent research."""

from __future__ import annotations

import os

import httpx
import streamlit as st

from components.research_output import render_research_result
from components.workflow_viz import AGENT_PIPELINE, render_workflow_from_steps
from styles import get_custom_css

API_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

MODES = {
    "chat": "💬 Chat — Web Search",
    "research": "🔬 Deep Research Report",
}

st.set_page_config(
    page_title="Research Assistant",
    page_icon="\u2728",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_custom_css(), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "mode" not in st.session_state:
    st.session_state.mode = "chat"
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "research_messages" not in st.session_state:
    st.session_state.research_messages = []
if "research_depth" not in st.session_state:
    st.session_state.research_depth = "standard"


def _current_messages() -> list[dict]:
    if st.session_state.mode == "chat":
        return st.session_state.chat_messages
    return st.session_state.research_messages


def _set_current_messages(messages: list[dict]) -> None:
    if st.session_state.mode == "chat":
        st.session_state.chat_messages = messages
    else:
        st.session_state.research_messages = messages


def search_web(query: str) -> dict | None:
    try:
        r = httpx.post(
            f"{API_URL}/api/v1/search",
            json={"query": query, "max_results": 5},
            timeout=90.0,
        )
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        st.error("Backend is offline. Run: `py -3 -m uvicorn backend.api.app:app --reload`")
        return None
    except Exception as e:
        st.error(f"Search failed: {e}")
        return None


def run_research(query: str, depth: str) -> dict | None:
    try:
        r = httpx.post(
            f"{API_URL}/api/v1/research",
            json={"query": query, "depth": depth},
            timeout=600.0,
        )
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        st.error("Backend is offline. Run: `py -3 -m uvicorn backend.api.app:app --reload`")
        return None
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:300] if e.response else str(e)
        st.error(f"Research failed ({e.response.status_code}): {detail}")
        return None
    except Exception as e:
        st.error(f"Research failed: {e}")
        return None


def _render_chat_message(msg: dict) -> None:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander(f"Sources ({len(msg['sources'])})"):
                for src in msg["sources"]:
                    title = src.get("title", "Source")
                    url = src.get("url", "")
                    if url:
                        st.markdown(f"- [{title}]({url})")
                    else:
                        st.markdown(f"- {title}")


def _render_research_message(msg: dict) -> None:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
            return

        data = msg.get("research_data", {})
        render_research_result(data.get("raw") or data, inline=True)


def _handle_chat_prompt(prompt: str) -> None:
    messages = _current_messages()
    messages.append({"role": "user", "content": prompt})
    _set_current_messages(messages)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching the web..."):
            result = search_web(prompt)

        if result:
            answer = result.get("answer", "Sorry, I couldn't generate an answer.")
            sources = result.get("sources", [])
            st.markdown(answer)

            if sources:
                with st.expander(f"Sources ({len(sources)})"):
                    for src in sources:
                        title = src.get("title", "Source")
                        url = src.get("url", "")
                        if url:
                            st.markdown(f"- [{title}]({url})")
                        else:
                            st.markdown(f"- {title}")

            messages = _current_messages()
            messages.append({
                "role": "assistant",
                "content": answer,
                "sources": sources,
            })
            _set_current_messages(messages)


def _handle_research_prompt(prompt: str) -> None:
    messages = _current_messages()
    messages.append({"role": "user", "content": prompt})
    _set_current_messages(messages)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        agent_labels = " → ".join(a["name"] for a in AGENT_PIPELINE)
        progress = st.progress(0, text=f"Starting pipeline: {agent_labels}")

        with st.spinner("Running 5-agent research pipeline (this may take a minute)..."):
            result = run_research(prompt, st.session_state.research_depth)

        progress.progress(100, text="Pipeline complete")

        if not result:
            return

        render_research_result(result)

        summary = result.get("summary", "")
        report = result.get("report", "")
        display = report or summary or "Research completed."

        messages = _current_messages()
        messages.append({
            "role": "assistant",
            "content": display[:500],
            "research_data": {
                "session_id": result.get("session_id"),
                "summary": summary,
                "report": report,
                "plan": result.get("plan", []),
                "steps": result.get("steps", []),
                "citations": result.get("citations", []),
                "mermaid_diagram": result.get("mermaid_diagram", ""),
                "errors": result.get("errors", []),
                "raw": result,
            },
        })
        _set_current_messages(messages)


# ---------------------------------------------------------------------------
# Sidebar — mode switch and settings
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(get_custom_css(), unsafe_allow_html=True)

    st.markdown(
        """
        <div class="sidebar-brand">
            <span class="sidebar-logo">✨</span>
            <div>
                <div class="sidebar-title" style="color:#0f172a!important">Research Assistant</div>
                <div class="sidebar-sub" style="color:#64748b!important">Search the web · Write reports</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="sidebar-section-label" style="color:#0d9488!important">Choose mode</p>',
        unsafe_allow_html=True,
    )
    selected_mode = st.radio(
        "Mode",
        options=list(MODES.keys()),
        format_func=lambda k: MODES[k],
        index=list(MODES.keys()).index(st.session_state.mode),
        label_visibility="collapsed",
    )
    if selected_mode != st.session_state.mode:
        st.session_state.mode = selected_mode
        st.rerun()

    if st.session_state.mode == "chat":
        st.markdown(
            """
            <div class="sidebar-info-card" style="color:#475569!important;background:#f8fafc!important">
                <strong style="color:#0f172a!important">Quick answers</strong><br>
                <span style="color:#475569!important">Searches the web and replies in plain text—best for fast Q&amp;A.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="sidebar-info-card" style="color:#475569!important;background:#f8fafc!important">
                <strong style="color:#0f172a!important">Full research report</strong><br>
                <span style="color:#475569!important">Plans sub-questions, searches the web for each, then delivers a
                detailed written report with sources.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.session_state.research_depth = st.selectbox(
            "Research depth",
            options=["quick", "standard", "deep"],
            index=["quick", "standard", "deep"].index(st.session_state.research_depth),
        )

    if st.button("Clear conversation", use_container_width=True, type="secondary"):
        _set_current_messages([])
        st.rerun()

    backend_ok = False
    try:
        backend_ok = httpx.get(f"{API_URL}/", timeout=2.0).status_code == 200
    except Exception:
        backend_ok = False

    status_html = (
        '<span class="sidebar-status-dot"></span> API online'
        if backend_ok
        else '<span class="sidebar-status-dot" style="background:#f87171;box-shadow:none"></span> API offline'
    )
    st.markdown(
        f"""
        <div class="sidebar-footer" style="color:#64748b!important">
            <div class="sidebar-status" style="color:#166534!important">{status_html}</div>
            <span style="color:#64748b!important">Backend </span>
            <a href="{API_URL}" target="_blank" style="color:#0d9488!important">{API_URL}</a><br>
            <span style="color:#64748b!important">Tip: add API keys in </span>
            <span class="tag" style="color:#334155!important">backend/.env</span>
            <span style="color:#64748b!important"> for best quality.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

is_chat = st.session_state.mode == "chat"
header_title = "Web Search AI" if is_chat else "Multi-Agent Research"
header_sub = (
    "Ask anything — I'll search the web and answer in plain text."
    if is_chat
    else "Ask a research question — we search the web and deliver a detailed written report."
)

header_class = "chat-header" if is_chat else "chat-header chat-header-research"
st.markdown(
    f"""
    <div class="{header_class}">
        <h1>{header_title}</h1>
        <p>{header_sub}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

mode_badge = "Chat mode" if is_chat else "Research mode"
st.markdown(
    f'<div style="text-align:center;margin-bottom:1rem;">'
    f'<span class="status-badge {"status-running" if is_chat else "status-completed"}">{mode_badge}</span>'
    f"</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

messages = _current_messages()
render_fn = _render_chat_message if is_chat else _render_research_message
for msg in messages:
    render_fn(msg)

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------

placeholder = (
    "Ask me anything..."
    if is_chat
    else "Enter a research question (e.g. impact of AI on healthcare)..."
)

if prompt := st.chat_input(placeholder):
    if is_chat:
        _handle_chat_prompt(prompt)
    else:
        _handle_research_prompt(prompt)
