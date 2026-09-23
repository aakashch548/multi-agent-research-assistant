"""Pydantic v2 schemas for document ingestion and search results."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentUpload(BaseModel):
    """Payload for uploading a new source document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Human-readable document title.",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Full text content of the document.",
    )
    source_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Original URL the document was sourced from.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata attached to the document.",
    )


class DocumentResponse(BaseModel):
    """Response schema for a persisted document."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    chunk_count: int = 0
    created_at: datetime


class SearchQuery(BaseModel):
    """Payload for a document search request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language search query.",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return.",
    )


class SearchResult(BaseModel):
    """A single vector-search hit returned from the RAG pipeline."""

    document_id: str = Field(
        ..., description="Identifier of the source document in the vector store."
    )
    content: str = Field(
        ..., description="Matched text chunk."
    )
    score: float = Field(
        ..., description="Cosine-similarity score."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata stored alongside the chunk.",
    )
