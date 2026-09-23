"""Document chunking with multiple strategies for the RAG pipeline.

Supports recursive character splitting with configurable chunk sizes,
token counting via tiktoken, and robust edge-case handling.
"""

from __future__ import annotations

import structlog
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = structlog.get_logger()

MAX_SINGLE_DOCUMENT_CHARS: int = 10_000_000


class DocumentChunker:
    """Splits documents into smaller chunks suitable for embedding and retrieval.

    Uses LangChain's RecursiveCharacterTextSplitter under the hood, with
    tiktoken-based token counting for cost estimation.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be smaller than chunk_size ({chunk_size})"
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            is_separator_regex=False,
        )

        try:
            self._encoding = tiktoken.encoding_for_model("gpt-4o")
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")

        logger.info(
            "document_chunker_initialized",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    def chunk_text(
        self, text: str, metadata: dict | None = None
    ) -> list[Document]:
        """Split raw text into a list of LangChain Documents.

        Args:
            text: The source text to chunk.
            metadata: Optional metadata dict attached to every resulting chunk.

        Returns:
            A list of Document objects, each with page_content and metadata.
        """
        if not text or not text.strip():
            logger.warning("chunk_text_called_with_empty_input")
            return []

        if len(text) > MAX_SINGLE_DOCUMENT_CHARS:
            logger.warning(
                "document_exceeds_max_chars",
                length=len(text),
                max_allowed=MAX_SINGLE_DOCUMENT_CHARS,
            )

        base_metadata = metadata or {}
        sanitized = self._sanitize_text(text)
        token_count = self._estimate_tokens(sanitized)

        logger.debug(
            "chunking_text",
            char_length=len(sanitized),
            estimated_tokens=token_count,
        )

        try:
            chunks = self._splitter.split_text(sanitized)
        except Exception:
            logger.exception("text_splitting_failed")
            return [
                Document(
                    page_content=sanitized,
                    metadata={**base_metadata, "chunk_index": 0, "total_chunks": 1},
                )
            ]

        documents: list[Document] = []
        for idx, chunk in enumerate(chunks):
            chunk_metadata = {
                **base_metadata,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "chunk_tokens": self._estimate_tokens(chunk),
            }
            documents.append(Document(page_content=chunk, metadata=chunk_metadata))

        logger.info(
            "text_chunked_successfully",
            total_chunks=len(documents),
            total_tokens=token_count,
        )
        return documents

    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        """Split a list of existing Documents into smaller chunks.

        Preserves and augments each document's original metadata.

        Args:
            documents: Source documents to re-chunk.

        Returns:
            A flat list of chunked Documents.
        """
        if not documents:
            logger.warning("chunk_documents_called_with_empty_list")
            return []

        all_chunks: list[Document] = []
        for doc_idx, doc in enumerate(documents):
            doc_metadata = {**(doc.metadata or {}), "source_doc_index": doc_idx}
            chunks = self.chunk_text(doc.page_content, metadata=doc_metadata)
            all_chunks.extend(chunks)

        logger.info(
            "documents_chunked",
            input_count=len(documents),
            output_count=len(all_chunks),
        )
        return all_chunks

    def _estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in *text* using tiktoken.

        Args:
            text: The string to tokenize.

        Returns:
            Token count (0 for empty / whitespace-only strings).
        """
        if not text or not text.strip():
            return 0

        try:
            return len(self._encoding.encode(text))
        except Exception:
            logger.exception("token_estimation_failed")
            return len(text) // 4  # rough fallback

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Normalize whitespace and strip null bytes."""
        text = text.replace("\x00", "")
        lines = text.splitlines()
        cleaned = "\n".join(line.rstrip() for line in lines)
        return cleaned.strip()
