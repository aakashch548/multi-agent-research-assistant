"""Shared pytest fixtures for the research assistant test suite."""

from __future__ import annotations

from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.models.state import ResearchState


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------

@pytest.fixture()
def test_settings() -> dict[str, Any]:
    """Minimal settings overrides for testing."""
    return {
        "OPENAI_API_KEY": "sk-test-key",
        "TAVILY_API_KEY": "tvly-test-key",
        "DATABASE_URL": "sqlite+aiosqlite:///test.db",
        "REDIS_URL": "redis://localhost:6379/1",
        "CHROMA_HOST": "localhost",
        "CHROMA_PORT": 8100,
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "DEBUG",
    }


# ------------------------------------------------------------------
# Mock LLM
# ------------------------------------------------------------------

@pytest.fixture()
def mock_llm() -> MagicMock:
    """A mocked ChatOpenAI instance that returns predictable output."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="mock response"))
    return llm


# ------------------------------------------------------------------
# Sample state
# ------------------------------------------------------------------

@pytest.fixture()
def sample_state() -> ResearchState:
    """A pre-populated ResearchState for testing agents."""
    return {
        "query": "What is the impact of AI on healthcare?",
        "plan": [
            "What are the current applications of AI in healthcare?",
            "What are the benefits and risks of AI in medical diagnosis?",
            "How is AI being used in drug discovery?",
        ],
        "research_results": [
            {
                "query": "What are the current applications of AI in healthcare?",
                "findings": "AI is used in imaging, diagnostics, and patient monitoring.",
                "sources": [
                    {"url": "https://example.com/ai-health", "title": "AI in Health", "relevance_score": 0.9},
                ],
            }
        ],
        "verified_facts": [
            {
                "claim": "AI is used in medical imaging analysis.",
                "confidence": 0.95,
                "supporting_sources": ["https://example.com/ai-health"],
                "contradicting_sources": [],
                "verified": True,
            }
        ],
        "citations": [
            {
                "text": "AI is used in imaging, diagnostics, and patient monitoring.",
                "source_url": "https://example.com/ai-health",
                "title": "AI in Health",
                "relevance_score": 0.9,
            }
        ],
        "summary": "AI is transforming healthcare through improved diagnostics and drug discovery.",
        "report": "",
        "mermaid_diagram": "",
        "errors": [],
        "metadata": {"depth": "standard"},
        "current_agent": "",
        "retry_count": 0,
        "max_retries": 3,
        "session_id": "test-session-001",
        "status": "started",
    }


# ------------------------------------------------------------------
# Mock Tavily
# ------------------------------------------------------------------

@pytest.fixture()
def mock_tavily() -> MagicMock:
    """Mocked Tavily search tool."""
    tool = MagicMock()
    tool.search = AsyncMock(
        return_value=[
            MagicMock(
                title="Test Result 1",
                url="https://example.com/result1",
                content="This is test content about AI.",
                score=0.9,
            ),
            MagicMock(
                title="Test Result 2",
                url="https://example.com/result2",
                content="More content about machine learning.",
                score=0.8,
            ),
        ]
    )
    return tool


# ------------------------------------------------------------------
# Mock Chroma
# ------------------------------------------------------------------

@pytest.fixture()
def mock_chroma() -> MagicMock:
    """Mocked ChromaDB client."""
    client = MagicMock()
    collection = MagicMock()
    collection.add = MagicMock()
    collection.query = MagicMock(
        return_value={
            "ids": [["doc1"]],
            "documents": [["Test document content"]],
            "metadatas": [[{"source": "test"}]],
            "distances": [[0.1]],
        }
    )
    collection.count = MagicMock(return_value=10)
    client.get_or_create_collection = MagicMock(return_value=collection)
    return client


# ------------------------------------------------------------------
# FastAPI test client
# ------------------------------------------------------------------

@pytest_asyncio.fixture()
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client wired to the FastAPI test app."""
    with (
        patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "sk-test",
                "TAVILY_API_KEY": "tvly-test",
                "DATABASE_URL": "sqlite+aiosqlite:///test.db",
                "ENVIRONMENT": "testing",
                "DEMO_MODE": "true",
            },
        ),
    ):
        from backend.api.app import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
