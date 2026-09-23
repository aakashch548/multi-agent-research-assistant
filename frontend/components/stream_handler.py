"""SSE stream handler for real-time research event consumption."""

from __future__ import annotations

import json
from typing import Generator

import httpx


class StreamHandler:
    """Handles Server-Sent Events (SSE) streaming from the research API."""

    def __init__(self, api_url: str) -> None:
        self.api_url = api_url.rstrip("/")

    def stream_events(self, session_id: str) -> Generator[dict, None, None]:
        """Connect to the SSE endpoint and yield structured event dicts.

        Each yielded dict has the shape:
        {"event_type": str, "agent_name": str, "data": Any, "timestamp": str}
        """
        url = f"{self.api_url}/api/v1/research/{session_id}/stream"

        try:
            with httpx.Client(timeout=None) as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    buffer = ""
                    for chunk in response.iter_text():
                        buffer += chunk
                        while "\n\n" in buffer:
                            event_str, buffer = buffer.split("\n\n", 1)
                            parsed = self._parse_event(event_str)
                            if parsed is not None:
                                yield parsed
        except httpx.HTTPStatusError as e:
            yield {
                "event_type": "error",
                "agent_name": "system",
                "data": f"HTTP error {e.response.status_code}: {e.response.text}",
                "timestamp": "",
            }
        except httpx.ConnectError:
            yield {
                "event_type": "error",
                "agent_name": "system",
                "data": "Could not connect to the research API. Is the backend running?",
                "timestamp": "",
            }
        except Exception as e:
            yield {
                "event_type": "error",
                "agent_name": "system",
                "data": f"Stream error: {str(e)}",
                "timestamp": "",
            }

    def _parse_event(self, raw: str) -> dict | None:
        """Parse a single SSE event block into a structured dict."""
        data_line = None
        for line in raw.strip().split("\n"):
            if line.startswith("data:"):
                data_line = line[len("data:"):].strip()
                break

        if not data_line:
            return None

        try:
            payload = json.loads(data_line)
            return {
                "event_type": payload.get("event_type", "unknown"),
                "agent_name": payload.get("agent_name", "unknown"),
                "data": payload.get("data", ""),
                "timestamp": payload.get("timestamp", ""),
            }
        except json.JSONDecodeError:
            return {
                "event_type": "raw",
                "agent_name": "system",
                "data": data_line,
                "timestamp": "",
            }
