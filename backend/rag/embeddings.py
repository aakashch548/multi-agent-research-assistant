"""Embedding service wrapping OpenAI's text-embedding models.

Provides async batch processing with rate limiting and automatic retries.
"""

from __future__ import annotations

import asyncio
from typing import Sequence

import structlog
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger()

_BATCH_SIZE: int = 100
_RATE_LIMIT_DELAY: float = 0.25  # seconds between batches


class EmbeddingService:
    """Async wrapper around OpenAI embeddings with batching and retry logic.

    Args:
        model: The OpenAI embedding model identifier.
    """

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self.model = model
        self._client = OpenAIEmbeddings(model=self.model)
        logger.info("embedding_service_initialized", model=self.model)

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text string.

        Args:
            text: The input string.

        Returns:
            A list of floats representing the embedding.

        Raises:
            ValueError: If *text* is empty.
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        logger.debug("embedding_single_text", length=len(text))
        try:
            embedding: list[float] = await self._client.aembed_query(text)
            return embedding
        except Exception:
            logger.exception("embed_text_failed", length=len(text))
            raise

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts with batching and rate limiting.

        Args:
            texts: List of input strings.

        Returns:
            Corresponding list of embedding vectors.
        """
        if not texts:
            return []

        cleaned: list[str] = [t if t and t.strip() else " " for t in texts]
        all_embeddings: list[list[float]] = []

        for batch_start in range(0, len(cleaned), _BATCH_SIZE):
            batch = cleaned[batch_start : batch_start + _BATCH_SIZE]
            logger.debug(
                "embedding_batch",
                batch_start=batch_start,
                batch_size=len(batch),
                total=len(cleaned),
            )
            try:
                batch_embeddings = await self._embed_batch(batch)
                all_embeddings.extend(batch_embeddings)
            except Exception:
                logger.exception(
                    "batch_embedding_failed",
                    batch_start=batch_start,
                    batch_size=len(batch),
                )
                raise

            if batch_start + _BATCH_SIZE < len(cleaned):
                await asyncio.sleep(_RATE_LIMIT_DELAY)

        logger.info("texts_embedded", count=len(all_embeddings))
        return all_embeddings

    async def embed_documents(
        self, documents: list[Document]
    ) -> list[tuple[Document, list[float]]]:
        """Embed a list of LangChain Documents.

        Args:
            documents: Documents whose ``page_content`` will be embedded.

        Returns:
            List of (Document, embedding) tuples.
        """
        if not documents:
            return []

        texts = [doc.page_content for doc in documents]
        embeddings = await self.embed_texts(texts)
        pairs = list(zip(documents, embeddings, strict=True))
        logger.info("documents_embedded", count=len(pairs))
        return pairs

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a single batch with retry logic."""
        return await self._client.aembed_documents(list(texts))
