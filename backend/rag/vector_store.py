"""ChromaDB vector storage service for document persistence and similarity search.

Uses the HTTP client for client-server deployment with metadata filtering.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import chromadb
import structlog
from langchain_core.documents import Document

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single result from a vector similarity search."""

    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    document_id: str = ""


class VectorStoreService:
    """Manages a ChromaDB collection for document embeddings.

    Connects via ``chromadb.HttpClient`` so the backing Chroma server can
    run as a separate process or container.

    Args:
        host: Chroma server hostname.
        port: Chroma server port.
        collection_name: Name of the target collection.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        collection_name: str = "research_documents",
    ) -> None:
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self._client: chromadb.HttpClient | None = None
        self._collection: chromadb.Collection | None = None
        logger.info(
            "vector_store_configured",
            host=self.host,
            port=self.port,
            collection=self.collection_name,
        )

    async def initialize(self) -> None:
        """Connect to Chroma and create the collection if it does not exist."""
        try:
            self._client = chromadb.HttpClient(host=self.host, port=self.port)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "vector_store_initialized",
                collection=self.collection_name,
                count=self._collection.count(),
            )
        except Exception:
            logger.exception("vector_store_initialization_failed")
            raise

    def _ensure_collection(self) -> chromadb.Collection:
        if self._collection is None:
            raise RuntimeError(
                "VectorStoreService not initialized – call initialize() first"
            )
        return self._collection

    async def add_documents(
        self,
        documents: list[Document],
        embeddings: list[list[float]],
    ) -> list[str]:
        """Insert documents with pre-computed embeddings.

        Args:
            documents: LangChain Documents to store.
            embeddings: Corresponding embedding vectors (same order / length).

        Returns:
            List of generated document IDs.
        """
        collection = self._ensure_collection()

        if len(documents) != len(embeddings):
            raise ValueError(
                f"documents ({len(documents)}) and embeddings ({len(embeddings)}) "
                "must have the same length"
            )

        if not documents:
            return []

        ids: list[str] = [uuid.uuid4().hex for _ in documents]
        contents: list[str] = [doc.page_content for doc in documents]
        metadatas: list[dict[str, Any]] = [
            self._sanitize_metadata(doc.metadata or {}) for doc in documents
        ]

        batch_size = 500
        for start in range(0, len(ids), batch_size):
            end = start + batch_size
            try:
                collection.add(
                    ids=ids[start:end],
                    documents=contents[start:end],
                    embeddings=embeddings[start:end],
                    metadatas=metadatas[start:end],
                )
            except Exception:
                logger.exception(
                    "add_documents_batch_failed",
                    batch_start=start,
                    batch_end=end,
                )
                raise

        logger.info("documents_added_to_vector_store", count=len(ids))
        return ids

    async def search(
        self,
        query_embedding: list[float],
        k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Perform a similarity search using a pre-computed query embedding.

        Args:
            query_embedding: The query's embedding vector.
            k: Number of results to return.
            filter: Optional Chroma metadata filter (``where`` clause).

        Returns:
            Ranked list of SearchResult objects.
        """
        collection = self._ensure_collection()

        try:
            query_params: dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": min(k, collection.count()) or k,
            }
            if filter:
                query_params["where"] = filter

            raw = collection.query(**query_params)
        except Exception:
            logger.exception("vector_search_failed")
            raise

        results: list[SearchResult] = []
        if not raw["ids"] or not raw["ids"][0]:
            return results

        for idx, doc_id in enumerate(raw["ids"][0]):
            distance = raw["distances"][0][idx] if raw.get("distances") else 0.0
            score = 1.0 - distance  # cosine distance → similarity
            content = raw["documents"][0][idx] if raw.get("documents") else ""
            metadata = raw["metadatas"][0][idx] if raw.get("metadatas") else {}
            results.append(
                SearchResult(
                    content=content,
                    score=score,
                    metadata=metadata,
                    document_id=doc_id,
                )
            )

        logger.info("vector_search_completed", k=k, returned=len(results))
        return results

    async def delete_collection(self) -> None:
        """Delete the entire collection from the Chroma server."""
        if self._client is None:
            raise RuntimeError("VectorStoreService not initialized")

        try:
            self._client.delete_collection(name=self.collection_name)
            self._collection = None
            logger.info("collection_deleted", collection=self.collection_name)
        except Exception:
            logger.exception("collection_deletion_failed")
            raise

    async def get_collection_stats(self) -> dict[str, Any]:
        """Return basic statistics about the current collection.

        Returns:
            Dict with ``name``, ``count``, and ``metadata`` keys.
        """
        collection = self._ensure_collection()

        try:
            count = collection.count()
            metadata = collection.metadata or {}
            return {
                "name": self.collection_name,
                "count": count,
                "metadata": metadata,
            }
        except Exception:
            logger.exception("get_collection_stats_failed")
            raise

    @staticmethod
    def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        """Ensure all metadata values are Chroma-compatible scalar types."""
        sanitized: dict[str, Any] = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif value is None:
                sanitized[key] = ""
            else:
                sanitized[key] = str(value)
        return sanitized
