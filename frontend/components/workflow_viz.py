"""Workflow visualization component for the agent pipeline."""

from __future__ import annotations

import streamlit as st


AGENT_PIPELINE = [
    {"key": "planner", "name": "Planner", "icon": "\U0001f4cb"},
    {"key": "researcher", "name": "Researcher", "icon": "\U0001f50d"},
    {"key": "verifier", "name": "Verifier", "icon": "\u2705"},
    {"key": "summarizer", "name": "Summarizer", "icon": "\U0001f4dd"},
    {"key": "writer", "name": "Writer", "icon": "\u270d\ufe0f"},
]

STATUS_CONFIG = {
    "completed": {"color": "#28a745", "label": "Completed", "css_class": "agent-node-completed"},
    "running": {"color": "#007bff", "label": "Running", "css_class": "agent-node-running"},
    "pending": {"color": "#6c757d", "label": "Pending", "css_class": "agent-node-pending"},
    "failed": {"color": "#dc3545", "label": "Failed", "css_class": "agent-node-failed"},
}


def _get_agent_status(events: list[dict]) -> dict[str, dict]:
    """Derive each agent's status and timing from the event stream."""
    agent_states: dict[str, dict] = {}

    for agent in AGENT_PIPELINE:
        agent_states[agent["key"]] = {"status": "pending", "duration": None, "output": None}

    for event in events:
        agent_name = event.get("agent_name", "").lower()
        event_type = event.get("event_type", "")

        matched_key = None
        for agent in AGENT_PIPELINE:
            if agent["key"] in agent_name or agent_name in agent["key"]:
                matched_key = agent["key"]
                break

        if not matched_key:
            continue

        if event_type in ("agent_start", "start", "running"):
            agent_states[matched_key]["status"] = "running"
        elif event_type in ("agent_complete", "complete", "completed", "done"):
            agent_states[matched_key]["status"] = "completed"
            if isinstance(event.get("data"), dict):
                agent_states[matched_key]["duration"] = event["data"].get("duration")
                agent_states[matched_key]["output"] = event["data"].get("output")
            elif isinstance(event.get("data"), str):
                agent_states[matched_key]["output"] = event["data"]
        elif event_type in ("agent_error", "error", "failed"):
            agent_states[matched_key]["status"] = "failed"
            agent_states[matched_key]["output"] = event.get("data")

    return agent_states


def steps_to_events(steps: list[dict]) -> list[dict]:
    """Convert research API step records into workflow event dicts."""
    events: list[dict] = []
    for step in steps:
        status = step.get("status", "pending")
        event_type = {
            "completed": "completed",
            "skipped": "completed",
            "failed": "failed",
            "running": "running",
        }.get(status, "pending")
        events.append({
            "agent_name": step.get("agent_name", ""),
            "event_type": event_type,
            "data": step.get("output_data"),
        })
    return events


def render_workflow_from_steps(steps: list[dict]) -> None:
    """Render the agent pipeline from a research session's step list."""
    render_workflow_status(steps_to_events(steps))


def render_workflow_status(events: list[dict]) -> None:
    """Render the agent pipeline with visual status indicators."""
    agent_states = _get_agent_status(events)

    cols = st.columns(len(AGENT_PIPELINE) * 2 - 1)

    col_idx = 0
    for i, agent in enumerate(AGENT_PIPELINE):
        state = agent_states[agent["key"]]
        status = state["status"]
        config = STATUS_CONFIG[status]

        with cols[col_idx]:
            duration_text = ""
            if state["duration"] is not None:
                duration_text = f'<div class="agent-time">{state["duration"]:.1f}s</div>'

            st.markdown(
                f"""
                <div class="agent-node {config['css_class']}">
                    <div class="agent-icon">{agent['icon']}</div>
                    <div class="agent-name">{agent['name']}</div>
                    <div class="status-badge status-{status}">{config['label']}</div>
                    {duration_text}
                </div>
                """,
                unsafe_allow_html=True,
            )

        if i < len(AGENT_PIPELINE) - 1:
            col_idx += 1
            with cols[col_idx]:
                st.markdown(
                    '<div class="arrow-connector">\u2192</div>',
                    unsafe_allow_html=True,
                )

        col_idx += 1


def render_agent_details(events: list[dict]) -> None:
    """Render expandable details for each agent that has output."""
    agent_states = _get_agent_status(events)

    for agent in AGENT_PIPELINE:
        state = agent_states[agent["key"]]
        if state["status"] == "pending":
            continue

        status_emoji = {
            "completed": "\u2705",
            "running": "\u23f3",
            "failed": "\u274c",
        }.get(state["status"], "\u2b55")

        label = f"{status_emoji} {agent['name']}"
        if state["duration"] is not None:
            label += f" ({state['duration']:.1f}s)"

        expanded = state["status"] == "running"
        with st.expander(label, expanded=expanded):
            if state["output"]:
                if isinstance(state["output"], dict):
                    st.json(state["output"])
                else:
                    st.markdown(str(state["output"]))
            elif state["status"] == "running":
                st.info("Agent is currently working...")
            elif state["status"] == "failed":
                st.error("Agent encountered an error.")
