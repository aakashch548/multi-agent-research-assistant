"""Document ingestion and search service backed by the RAG pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from backend.core.config import Settings
from backend.core.exceptions import RAGError
from backend.schemas.documents import DocumentResponse, DocumentUpload, SearchResult

logger = structlog.get_logger(__name__)


class DocumentService:
    """Orchestrates document ingestion and semantic search.

    Provides a thin facade over the RAG pipeline and ChromaDB for
    use by the API layer.
    """

    def __init__(
        self,
        chroma_client: Any | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._chroma = chroma_client
        self._settings = settings
        self._collection_name = (
            settings.chroma_collection if settings else "research_documents"
        )

    def _get_collection(self) -> Any:
        """Get or create the ChromaDB collection."""
        if self._chroma is None:
            raise RAGError("ChromaDB client not initialized")
        return self._chroma.get_or_create_collection(name=self._collection_name)

    async def ingest_document(self, document: DocumentUpload) -> DocumentResponse:
        """Chunk and store a document in the vector store.

        Args:
            document: Validated upload payload.

        Returns:
            A DocumentResponse with the document ID and chunk count.
        """
        logger.info(
            "document_ingestion_started",
            title=document.title,
            content_length=len(document.content),
        )

        doc_id = str(uuid.uuid4())

        try:
            from backend.rag.chunker import DocumentChunker

            chunker = DocumentChunker(
                chunk_size=self._settings.chunk_size if self._settings else 1000,
                chunk_overlap=self._settings.chunk_overlap if self._settings else 200,
            )

            chunks = chunker.chunk_text(
                document.content,
                metadata={
                    "title": document.title,
                    "source_url": document.source_url or "",
                    "document_id": doc_id,
                    **(document.metadata or {}),
                },
            )

            if chunks and self._chroma:
                collection = self._get_collection()
                collection.add(
                    ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
                    documents=[c.page_content for c in chunks],
                    metadatas=[c.metadata for c in chunks],
                )

            chunk_count = len(chunks)
        except RAGError:
            raise
        except Exception as exc:
            logger.exception("document_ingestion_failed", title=document.title)
            raise RAGError(
                f"Failed to ingest document '{document.title}': {exc}"
            ) from exc

        logger.info(
            "document_ingestion_completed",
            document_id=doc_id,
            chunk_count=chunk_count,
        )

        return DocumentResponse(
            id=doc_id,
            title=document.title,
            chunk_count=chunk_count,
            created_at=datetime.now(timezone.utc),
        )

    async def search_documents(
        self, query: str, top_k: int = 5
    ) -> list[SearchResult]:
        """Perform semantic search across ingested documents.

        Args:
            query: Natural-language search query.
            top_k: Maximum number of results.

        Returns:
            Ranked list of SearchResult instances.
        """
        if not query or not query.strip():
            return []

        logger.info("document_search_started", query=query[:120], k=top_k)

        try:
            collection = self._get_collection()
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
            )

            search_results: list[SearchResult] = []
            if results and results.get("ids"):
                ids = results["ids"][0]
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]

                for i, doc_id in enumerate(ids):
                    score = 1.0 - distances[i] if i < len(distances) else 0.0
                    search_results.append(
                        SearchResult(
                            document_id=doc_id,
                            content=documents[i] if i < len(documents) else "",
                            score=round(score, 4),
                            metadata=metadatas[i] if i < len(metadatas) else {},
                        )
                    )

            logger.info("document_search_completed", results=len(search_results))
            return search_results

        except Exception as exc:
            logger.exception("document_search_failed", query=query[:120])
            raise RAGError(f"Document search failed: {exc}") from exc

    async def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics about the document store."""
        try:
            if self._chroma is None:
                return {
                    "total_documents": 0,
                    "collection_name": self._collection_name,
                    "status": "not_connected",
                }

            collection = self._get_collection()
            count = collection.count()

            return {
                "total_documents": count,
                "collection_name": self._collection_name,
                "status": "connected",
            }
        except Exception as exc:
            logger.exception("document_stats_failed")
            return {
                "total_documents": 0,
                "collection_name": self._collection_name,
                "status": f"error: {exc}",
            }
