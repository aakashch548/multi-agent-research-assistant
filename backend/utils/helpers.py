"""General-purpose utility functions used across the application."""

from __future__ import annotations

import json
import re
import uuid


def generate_session_id() -> str:
    """Generate a unique session identifier as a UUID-4 hex string."""
    return uuid.uuid4().hex


def sanitize_query(query: str) -> str:
    """Sanitize a user-provided query string.

    Strips leading/trailing whitespace, collapses multiple spaces,
    and removes control characters that could break downstream processing.
    """
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", query)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to a maximum length, appending an ellipsis if clipped.

    Args:
        text: The input text to potentially truncate.
        max_length: Maximum allowed character count (must be > 3).

    Returns:
        Original text if within limits, otherwise truncated with '...' suffix.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def format_duration(ms: float) -> str:
    """Convert a duration in milliseconds to a human-readable string.

    Examples:
        - 450.0 -> "450ms"
        - 1500.0 -> "1.50s"
        - 65000.0 -> "1m 5.00s"
        - 3661000.0 -> "1h 1m 1.00s"
    """
    if ms < 1000:
        return f"{ms:.0f}ms"

    seconds = ms / 1000

    if seconds < 60:
        return f"{seconds:.2f}s"

    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60

    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.2f}s"

    hours = int(minutes // 60)
    remaining_minutes = minutes % 60
    return f"{hours}h {remaining_minutes}m {remaining_seconds:.2f}s"


def safe_json_loads(text: str) -> dict | list | None:
    """Attempt to parse a JSON string, returning None on failure.

    Handles common issues like leading/trailing whitespace and
    single-quoted JSON (which is technically invalid but common).

    Args:
        text: The string to parse as JSON.

    Returns:
        Parsed dict/list on success, None on any parse failure.
    """
    if not text or not text.strip():
        return None
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
