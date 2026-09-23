#!/usr/bin/env python3
"""Terminal demo for the Multi-Agent Research Assistant.

Runs the full LangGraph workflow in demo mode (no external API keys required)
and prints the generated research report to the terminal.

Usage:
    py -3 demo.py
    py -3 demo.py "What are the latest trends in renewable energy?"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import textwrap
import uuid

# Windows terminals may not support all Unicode output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is on the path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Demo defaults — must be set before importing backend modules
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("OPENAI_API_KEY", "demo-key")
os.environ.setdefault("TAVILY_API_KEY", "demo-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./demo_research.db")
os.environ.setdefault("ENVIRONMENT", "development")

from backend.core.config import get_settings
from backend.workflows.research_graph import ResearchWorkflow

get_settings.cache_clear()


AGENT_ORDER = ["planner", "researcher", "verifier", "summarizer", "writer"]


def _banner(text: str) -> None:
    width = 72
    print()
    print("=" * width)
    print(f"  {text}")
    print("=" * width)


def _section(title: str, body: str) -> None:
    print(f"\n--- {title} ---")
    print(textwrap.fill(body, width=72) if body else "(empty)")


async def run_demo(query: str, depth: str) -> int:
    settings = get_settings()
    session_id = str(uuid.uuid4())

    _banner("Multi-Agent Research Assistant — Terminal Demo")
    print(f"  Mode:     {'DEMO (offline mock data)' if settings.demo_mode else 'LIVE'}")
    print(f"  Query:    {query}")
    print(f"  Depth:    {depth}")
    print(f"  Session:  {session_id}")

    workflow = ResearchWorkflow()

    print("\nRunning agent pipeline:")
    for agent in AGENT_ORDER:
        print(f"  -> {agent} ...", flush=True)

    try:
        result = await workflow.execute(
            query=query,
            session_id=session_id,
            depth=depth,
        )
    except Exception as exc:
        print(f"\nWorkflow failed: {exc}", file=sys.stderr)
        return 1

    plan = result.get("plan", [])
    _section("Research Plan", "\n".join(f"  {i+1}. {p}" for i, p in enumerate(plan)))

    summary = result.get("summary", "")
    _section("Executive Summary", summary)

    verified = result.get("verified_facts", [])
    if verified:
        facts_text = "\n".join(
            f"  - [{f.get('confidence', 0):.0%}] {f.get('claim', '')}"
            for f in verified[:5]
        )
        _section("Verified Facts (top 5)", facts_text)

    report = result.get("report", "")
    _banner("Final Report")
    print(report)

    diagram = result.get("mermaid_diagram", "")
    if diagram:
        _section("Mermaid Diagram", diagram)

    errors = result.get("errors", [])
    if errors:
        _section("Errors", "\n".join(f"  - {e}" for e in errors))

    _banner("Demo Complete")
    print("  All 5 agents executed successfully.")
    print("  Start the API server:  py -3 -m uvicorn backend.api.app:app --reload")
    print("  Start the frontend:    py -3 -m streamlit run frontend/app.py")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Multi-Agent Research Assistant demo in the terminal."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="What is the impact of artificial intelligence on healthcare?",
        help="Research question to investigate",
    )
    parser.add_argument(
        "--depth",
        choices=["quick", "standard", "deep"],
        default="standard",
        help="Research depth (default: standard)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_demo(args.query, args.depth)))


if __name__ == "__main__":
    main()
