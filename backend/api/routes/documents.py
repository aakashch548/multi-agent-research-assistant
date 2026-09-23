"""Document ingestion and vector-search endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

import structlog

from backend.services.document_service import DocumentService
from backend.api.dependencies import get_document_service
from backend.schemas.documents import (
    DocumentUpload,
    DocumentResponse,
    SearchQuery,
    SearchResult,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a document into the vector store",
)
async def ingest_document(
    payload: DocumentUpload,
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """Upload and ingest a document for RAG retrieval.

    The document is chunked, embedded, and stored in the vector database
    so it can be referenced during research sessions.
    """
    logger.info(
        "document_ingest_requested",
        title=payload.title,
        content_length=len(payload.content) if payload.content else 0,
    )
    result = await service.ingest_document(payload)
    logger.info("document_ingested", document_id=str(result.id))
    return result


@router.post(
    "/search",
    response_model=list[SearchResult],
    summary="Semantic search over ingested documents",
)
async def search_documents(
    query: SearchQuery,
    service: DocumentService = Depends(get_document_service),
) -> list[SearchResult]:
    """Perform a semantic similarity search across all ingested documents.

    Returns ranked results with relevance scores and source metadata.
    """
    logger.info("document_search_requested", query=query.query)
    results = await service.search_documents(query.query, top_k=query.top_k)
    logger.info("document_search_completed", num_results=len(results))
    return results


@router.get(
    "/stats",
    summary="Get vector store statistics",
)
async def get_stats(
    service: DocumentService = Depends(get_document_service),
) -> dict:
    """Retrieve statistics about the vector store.

    Includes document count, total chunks, and storage utilization.
    """
    return await service.get_stats()
