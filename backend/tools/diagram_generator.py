"""Mermaid diagram generation for research visualizations.

Generates valid Mermaid syntax for flowcharts, concept maps, and timelines
from structured input data.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger()


class DiagramGenerator:
    """Produces Mermaid diagram source code from structured data.

    Supports workflow flowcharts, concept maps (mind maps), and timeline
    diagrams.
    """

    def generate_workflow_diagram(self, steps: list[dict[str, Any]]) -> str:
        """Generate a top-down flowchart from a list of workflow steps.

        Each step dict should contain:
          - ``id``: unique node identifier
          - ``label``: display text
          - ``next`` (optional): list of successor step IDs
          - ``type`` (optional): ``"decision"`` for diamond nodes

        Args:
            steps: Ordered list of step definitions.

        Returns:
            Mermaid flowchart source string.

        Raises:
            ValueError: If *steps* is empty.
        """
        if not steps:
            raise ValueError("steps must not be empty")

        lines: list[str] = ["flowchart TD"]

        for step in steps:
            node_id = self._safe_id(step.get("id", f"step_{steps.index(step)}"))
            label = self._escape_label(step.get("label", node_id))
            step_type = step.get("type", "process")

            if step_type == "decision":
                lines.append(f"    {node_id}{{{{{label}}}}}")
            elif step_type == "start" or step_type == "end":
                lines.append(f"    {node_id}([{label}])")
            else:
                lines.append(f"    {node_id}[{label}]")

        for step in steps:
            node_id = self._safe_id(step.get("id", f"step_{steps.index(step)}"))
            successors: list[str] = step.get("next", [])
            edge_labels: list[str] = step.get("edge_labels", [])

            for idx, next_id in enumerate(successors):
                safe_next = self._safe_id(next_id)
                if idx < len(edge_labels) and edge_labels[idx]:
                    edge_text = self._escape_label(edge_labels[idx])
                    lines.append(f"    {node_id} -->|{edge_text}| {safe_next}")
                else:
                    lines.append(f"    {node_id} --> {safe_next}")

        diagram = "\n".join(lines)
        if not self._validate_mermaid(diagram):
            logger.warning("generated_workflow_may_be_invalid")
        logger.info("workflow_diagram_generated", steps=len(steps))
        return diagram

    def generate_concept_map(self, concepts: list[dict[str, Any]]) -> str:
        """Generate a Mermaid mind map from a concept hierarchy.

        Each concept dict should contain:
          - ``label``: concept name
          - ``children`` (optional): list of child concept dicts (recursive)

        Args:
            concepts: Top-level concepts with optional nested children.

        Returns:
            Mermaid mindmap source string.

        Raises:
            ValueError: If *concepts* is empty.
        """
        if not concepts:
            raise ValueError("concepts must not be empty")

        lines: list[str] = ["mindmap"]

        root_label = "Research"
        if len(concepts) == 1:
            root_label = self._escape_label(concepts[0].get("label", "Root"))
            lines.append(f"  root(({root_label}))")
            children = concepts[0].get("children", [])
            self._build_mindmap_branch(children, depth=2, lines=lines)
        else:
            lines.append(f"  root(({root_label}))")
            self._build_mindmap_branch(concepts, depth=2, lines=lines)

        diagram = "\n".join(lines)
        logger.info("concept_map_generated", concepts=len(concepts))
        return diagram

    def generate_timeline(self, events: list[dict[str, Any]]) -> str:
        """Generate a Mermaid timeline diagram.

        Each event dict should contain:
          - ``period``: time label (e.g. ``"2024 Q1"``)
          - ``events``: list of event description strings

        Args:
            events: Ordered list of period definitions.

        Returns:
            Mermaid timeline source string.

        Raises:
            ValueError: If *events* is empty.
        """
        if not events:
            raise ValueError("events must not be empty")

        lines: list[str] = ["timeline"]

        title = "Research Timeline"
        lines.append(f"    title {title}")

        for entry in events:
            period = self._escape_label(entry.get("period", "Unknown"))
            event_list: list[str] = entry.get("events", [])

            if not event_list:
                lines.append(f"    {period}")
                continue

            lines.append(f"    section {period}")
            for evt in event_list:
                lines.append(f"        {self._escape_label(evt)}")

        diagram = "\n".join(lines)
        logger.info("timeline_generated", periods=len(events))
        return diagram

    def _validate_mermaid(self, code: str) -> bool:
        """Run basic structural checks on generated Mermaid code.

        This is *not* a full parser – it catches obvious problems like
        missing diagram type declarations and unbalanced brackets.

        Args:
            code: Mermaid source to validate.

        Returns:
            True if the code passes basic validation.
        """
        if not code or not code.strip():
            return False

        first_line = code.strip().splitlines()[0].strip().lower()
        valid_prefixes = (
            "flowchart",
            "graph",
            "sequencediagram",
            "mindmap",
            "timeline",
            "gantt",
            "classDiagram",
            "erdiagram",
            "pie",
            "gitgraph",
        )
        if not any(first_line.startswith(p.lower()) for p in valid_prefixes):
            logger.warning("mermaid_unknown_diagram_type", first_line=first_line)
            return False

        open_brackets = sum(code.count(c) for c in "([{")
        close_brackets = sum(code.count(c) for c in ")]}")
        if open_brackets != close_brackets:
            logger.warning(
                "mermaid_unbalanced_brackets",
                open=open_brackets,
                close=close_brackets,
            )
            return False

        return True

    def _build_mindmap_branch(
        self,
        nodes: list[dict[str, Any]],
        depth: int,
        lines: list[str],
    ) -> None:
        """Recursively build indented mind map lines."""
        indent = "  " * depth
        for node in nodes:
            label = self._escape_label(node.get("label", ""))
            if not label:
                continue
            lines.append(f"{indent}{label}")
            children = node.get("children", [])
            if children:
                self._build_mindmap_branch(children, depth + 1, lines)

    @staticmethod
    def _safe_id(raw: str) -> str:
        """Sanitize an ID to contain only alphanumerics and underscores."""
        return re.sub(r"[^a-zA-Z0-9_]", "_", raw)

    @staticmethod
    def _escape_label(text: str) -> str:
        """Escape characters that conflict with Mermaid syntax."""
        text = text.replace('"', "'")
        text = text.replace("<", "‹").replace(">", "›")
        return text.strip()
