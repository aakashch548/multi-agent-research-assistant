"""Integration tests for FastAPI endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoints:
    async def test_root_returns_ok(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_health_endpoint(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


@pytest.mark.asyncio
class TestResearchEndpoints:
    async def test_list_sessions_empty(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/v1/research")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data

    async def test_get_session_not_found(self, async_client: AsyncClient) -> None:
        response = await async_client.get(
            "/api/v1/research/nonexistent-session-id"
        )
        assert response.status_code == 404

    async def test_delete_session_not_found(self, async_client: AsyncClient) -> None:
        response = await async_client.delete(
            "/api/v1/research/nonexistent-session-id"
        )
        assert response.status_code == 404

    async def test_export_invalid_format(self, async_client: AsyncClient) -> None:
        response = await async_client.get(
            "/api/v1/research/test-id/export/invalid"
        )
        assert response.status_code == 400


@pytest.mark.asyncio
class TestDocumentEndpoints:
    async def test_get_stats(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/v1/documents/stats")
        assert response.status_code == 200
