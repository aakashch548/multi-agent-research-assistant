"""Application entry point for running the server via uvicorn."""

from __future__ import annotations

import uvicorn

from backend.core.config import get_settings


def main() -> None:
    """Launch the ASGI server with settings-driven configuration."""
    settings = get_settings()
    uvicorn.run(
        "backend.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
