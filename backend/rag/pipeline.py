"""End-to-end RAG pipeline: chunk, embed, store, and retrieve."""

from __future__ import annotations

import uuid
from typing import Any

import chromadb
import structlog

from backend.core.config import get_settings
from backend.rag.chunker import DocumentChunker
from backend.rag.embeddings import EmbeddingService

logger = structlog.get_logger()


class RAGPipeline:
    """Combines chunking, embedding, and ChromaDB vector storage.

    Args:
        chunker: Optional custom chunker instance.
        embedding_service: Optional custom embedding service.
        collection_name: ChromaDB collection name override.
    """

    def __init__(
        self,
        chunker: DocumentChunker | None = None,
        embedding_service: EmbeddingService | None = None,
        collection_name: str | None = None,
    ) -> None:
        settings = get_settings()
        self._chunker = chunker or DocumentChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        self._embeddings = embedding_service or EmbeddingService(
            model=settings.embedding_model,
        )
        self._collection_name = collection_name or settings.chroma_collection

        self._client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("rag_pipeline_initialized", collection=self._collection_name)

    async def ingest(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, int]:
        """Chunk, embed, and store a document.

        Returns:
            A tuple of (document_id, chunk_count).
        """
        doc_id = str(uuid.uuid4())
        base_meta = {**(metadata or {}), "document_id": doc_id}

        chunks = self._chunker.chunk_text(text, metadata=base_meta)
        if not chunks:
            logger.warning("rag_ingest_no_chunks", document_id=doc_id)
            return doc_id, 0

        pairs = await self._embeddings.embed_documents(chunks)

        ids = [f"{doc_id}_{i}" for i in range(len(pairs))]
        documents = [doc.page_content for doc, _ in pairs]
        embeddings = [emb for _, emb in pairs]
        metadatas: list[dict[str, Any]] = []
        for doc, _ in pairs:
            safe_meta: dict[str, Any] = {}
            for k, v in (doc.metadata or {}).items():
                if isinstance(v, (str, int, float, bool)):
                    safe_meta[k] = v
            metadatas.append(safe_meta)

        self._collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info("document_ingested", document_id=doc_id, chunks=len(pairs))
        return doc_id, len(pairs)

    async def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Retrieve the *k* most relevant chunks for *query*.

        Returns:
            List of dicts with ``content``, ``metadata``, ``score``, ``source``.
        """
        query_embedding = await self._embeddings.embed_text(query)

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict[str, Any]] = []
        docs = results.get("documents") or [[]]
        metas = results.get("metadatas") or [[]]
        dists = results.get("distances") or [[]]

        for doc, meta, dist in zip(docs[0], metas[0], dists[0], strict=True):
            hits.append({
                "content": doc,
                "metadata": meta or {},
                "score": round(1.0 - dist, 4),
                "source": (meta or {}).get("source", ""),
            })

        logger.info("rag_search_completed", query_length=len(query), results=len(hits))
        return hits

    async def get_stats(self) -> dict[str, Any]:
        """Return high-level collection statistics."""
        count = self._collection.count()
        return {
            "collection": self._collection_name,
            "document_count": count,
        }
