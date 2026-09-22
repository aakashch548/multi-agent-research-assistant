"""Unit tests for the RAG pipeline components."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.rag.chunker import DocumentChunker


class TestDocumentChunker:
    def test_splits_text(self) -> None:
        chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
        text = "This is a test sentence. " * 20
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.page_content) > 0

    def test_handles_empty_text(self) -> None:
        chunker = DocumentChunker()
        chunks = chunker.chunk_text("")
        assert chunks == []

    def test_respects_metadata(self) -> None:
        chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
        metadata = {"source": "test", "author": "tester"}
        text = "Word " * 100
        chunks = chunker.chunk_text(text, metadata=metadata)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata["source"] == "test"
            assert chunk.metadata["author"] == "tester"

    def test_single_short_text(self) -> None:
        chunker = DocumentChunker(chunk_size=1000, chunk_overlap=200)
        chunks = chunker.chunk_text("Short text.")
        assert len(chunks) == 1
        assert chunks[0].page_content == "Short text."
