"""Semantic retriever with context-aware retrieval and reranking.

Combines vector similarity search with lightweight relevance scoring to
surface the most useful chunks for a given query.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import structlog

from backend.rag.embeddings import EmbeddingService
from backend.rag.vector_store import VectorStoreService

logger = structlog.get_logger()

RELEVANCE_THRESHOLD: float = 0.3


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """A single retrieval result enriched with relevance metadata."""

    content: str
    source: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class ResearchRetriever:
    """Retrieves and reranks documents from the vector store.

    Supports context-aware retrieval where prior conversation turns are
    folded into the query for improved relevance.

    Args:
        vector_store: The underlying vector store service.
        embedding_service: Service used to embed queries.
    """

    def __init__(
        self,
        vector_store: VectorStoreService,
        embedding_service: EmbeddingService,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        logger.info("research_retriever_initialized")

    async def retrieve(
        self, query: str, k: int = 5
    ) -> list[RetrievalResult]:
        """Retrieve the top-k documents most relevant to *query*.

        Args:
            query: The user's natural-language query.
            k: Maximum number of results to return.

        Returns:
            Ranked list of RetrievalResult objects above the relevance threshold.
        """
        if not query or not query.strip():
            logger.warning("retrieve_called_with_empty_query")
            return []

        try:
            query_embedding = await self.embedding_service.embed_text(query)
            raw_results = await self.vector_store.search(
                query_embedding=query_embedding, k=k * 2
            )
        except Exception:
            logger.exception("retrieval_failed", query=query[:100])
            raise

        results = self._rerank_results(raw_results, query)

        filtered = [r for r in results if r.score >= RELEVANCE_THRESHOLD]
        final = filtered[:k]

        logger.info(
            "retrieval_complete",
            query_length=len(query),
            raw=len(raw_results),
            after_rerank=len(results),
            after_filter=len(final),
        )
        return final

    async def retrieve_with_context(
        self, query: str, context: list[str], k: int = 5
    ) -> list[RetrievalResult]:
        """Retrieve documents using a context-augmented query.

        Prior conversation turns are concatenated with the current query so
        the embedding captures more of the user's intent.

        Args:
            query: The current question.
            context: Previous conversation turns / messages.
            k: Maximum results.

        Returns:
            Ranked list of RetrievalResult objects.
        """
        if not context:
            return await self.retrieve(query, k=k)

        recent_context = context[-3:]  # keep the window small
        augmented_query = (
            "Context:\n"
            + "\n".join(recent_context)
            + f"\n\nCurrent question: {query}"
        )
        logger.debug(
            "context_augmented_query",
            original_length=len(query),
            augmented_length=len(augmented_query),
        )
        return await self.retrieve(augmented_query, k=k)

    def _rerank_results(
        self,
        results: list,
        query: str,
    ) -> list[RetrievalResult]:
        """Combine the vector similarity score with a keyword relevance signal.

        Args:
            results: Raw search results from the vector store.
            query: The original query string.

        Returns:
            Re-scored and sorted list of RetrievalResult instances.
        """
        reranked: list[RetrievalResult] = []
        for result in results:
            content: str = getattr(result, "content", "")
            vector_score: float = getattr(result, "score", 0.0)
            keyword_score = self._calculate_relevance(query, content)

            combined = 0.7 * vector_score + 0.3 * keyword_score

            source = ""
            metadata: dict[str, Any] = getattr(result, "metadata", {}) or {}
            if metadata:
                source = str(
                    metadata.get("source_url", metadata.get("source", ""))
                )

            reranked.append(
                RetrievalResult(
                    content=content,
                    source=source,
                    score=combined,
                    metadata=metadata,
                )
            )

        reranked.sort(key=lambda r: r.score, reverse=True)
        return reranked

    @staticmethod
    def _calculate_relevance(query: str, content: str) -> float:
        """Compute a lightweight keyword-overlap relevance score (0-1).

        Uses TF-based overlap between query terms and the content.

        Args:
            query: The query string.
            content: The document chunk content.

        Returns:
            A float between 0.0 and 1.0.
        """
        if not query or not content:
            return 0.0

        def tokenize(text: str) -> list[str]:
            return re.findall(r"\b\w{2,}\b", text.lower())

        query_tokens = tokenize(query)
        if not query_tokens:
            return 0.0

        content_tokens = tokenize(content)
        content_counter = Counter(content_tokens)

        matches = sum(1 for t in query_tokens if content_counter[t] > 0)
        base_score = matches / len(query_tokens)

        idf_bonus = 0.0
        total_content_tokens = len(content_tokens) or 1
        for token in query_tokens:
            tf = content_counter[token] / total_content_tokens
            if tf > 0:
                idf_bonus += math.log(1 + tf)
        idf_bonus = min(idf_bonus / len(query_tokens), 0.3)

        return min(base_score + idf_bonus, 1.0)
