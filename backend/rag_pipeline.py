"""RAG pipeline: orchestrates embedding, retrieval, and generation."""

import logging
import time
import uuid
from pathlib import Path
from typing import Optional

import numpy as np

from backend.config import settings
from backend.database import Database
from backend.document_processor import DocumentChunk, DocumentProcessor
from backend.llm_handler import LLMHandler
from backend.models import QueryResponse, SourceChunk
from backend.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """End-to-end Retrieval-Augmented Generation pipeline.

    Responsibilities:
    - Ingest documents (process → embed → index → persist)
    - Answer questions (embed query → retrieve chunks → generate answer)
    - Manage the vector store and database lifecycle
    """

    def __init__(self) -> None:
        self.config = settings
        self.processor = DocumentProcessor(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            max_chunks=settings.max_chunks_per_doc,
        )
        self.vector_store = VectorStore(embedding_dimension=settings.embedding_dimension)
        self.llm = LLMHandler()
        self.db = Database(db_path=str(settings.data_dir / "db" / "papers.db"))
        self._embedding_model = None  # lazy-loaded

        # Try to restore persisted index
        self.vector_store.load(settings.vector_dir)

    # ── Embedding ─────────────────────────────────────────────────────────────

    @property
    def embedding_model(self):
        """Lazy-load the Sentence Transformer model."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model: %s", settings.embedding_model)
            self._embedding_model = SentenceTransformer(settings.embedding_model)
        return self._embedding_model

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Return a (N, D) float32 embedding matrix for *texts*."""
        return self.embedding_model.encode(
            texts, show_progress_bar=False, convert_to_numpy=True
        ).astype(np.float32)

    # ── Document ingestion ────────────────────────────────────────────────────

    def ingest_document(self, file_path: Path, filename: str) -> dict:
        """Process, embed, and index *file_path*.

        Returns a summary dict with ``doc_id``, ``filename``, and ``num_chunks``.
        """
        start = time.time()
        doc_id = str(uuid.uuid4())
        file_size = file_path.stat().st_size
        file_type = file_path.suffix.lstrip(".").lower()

        logger.info("Ingesting '%s' (doc_id=%s)", filename, doc_id)

        # 1. Extract + chunk
        chunks: list[DocumentChunk] = self.processor.process_file(file_path, doc_id, filename)
        if not chunks:
            raise ValueError(f"No text extracted from '{filename}'")

        # 2. Embed
        texts = [c.content for c in chunks]
        embeddings = self.embed_texts(texts)

        # 3. Build metadata list
        meta_list = [
            {
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "filename": c.filename,
                "content": c.content,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]

        # 4. Add to FAISS index
        self.vector_store.add_chunks(embeddings, meta_list)

        # 5. Persist index
        self.vector_store.save(settings.vector_dir)

        # 6. Persist metadata to DB
        self.db.save_document(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            num_chunks=len(chunks),
        )

        elapsed = (time.time() - start) * 1000
        logger.info(
            "Ingested '%s' in %.0f ms (%d chunks)", filename, elapsed, len(chunks)
        )
        return {"doc_id": doc_id, "filename": filename, "num_chunks": len(chunks)}

    def delete_document(self, doc_id: str) -> bool:
        """Remove a document from the index and database."""
        removed = self.vector_store.remove_document(doc_id)
        self.vector_store.save(settings.vector_dir)
        db_removed = self.db.delete_document(doc_id)
        logger.info("Deleted doc_id=%s (chunks removed=%d)", doc_id, removed)
        return db_removed

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(
        self,
        question: str,
        doc_id: Optional[str] = None,
        top_k: int = 5,
        temperature: Optional[float] = None,
    ) -> QueryResponse:
        """Answer *question* using RAG.

        1. Embed the question.
        2. Retrieve top-k similar chunks.
        3. Send context + question to the LLM.
        4. Persist the result.
        5. Return a :class:`~backend.models.QueryResponse`.
        """
        from datetime import datetime

        start = time.time()
        query_id = str(uuid.uuid4())

        if not self.vector_store.is_ready:
            raise ValueError("No documents are indexed. Please upload a document first.")

        # 1. Embed query
        query_embedding = self.embed_texts([question])[0]

        # 2. Retrieve
        raw_chunks = self.vector_store.search(
            query_embedding,
            top_k=top_k,
            doc_id=doc_id,
            threshold=settings.similarity_threshold,
        )

        # 3. Generate
        answer = self.llm.generate(question, raw_chunks, temperature=temperature)

        elapsed_ms = (time.time() - start) * 1000

        # 4. Build source objects
        sources = [
            SourceChunk(
                chunk_id=c["chunk_id"],
                doc_id=c["doc_id"],
                filename=c["filename"],
                content=c["content"],
                relevance_score=c["relevance_score"],
                chunk_index=c["chunk_index"],
            )
            for c in raw_chunks
        ]

        doc_ids_searched = list({c["doc_id"] for c in raw_chunks}) if raw_chunks else []

        # 5. Persist
        self.db.save_query(
            query_id=query_id,
            question=question,
            answer=answer,
            sources=[s.model_dump() for s in sources],
            doc_ids=doc_ids_searched,
            processing_time_ms=elapsed_ms,
        )

        return QueryResponse(
            query_id=query_id,
            question=question,
            answer=answer,
            sources=sources,
            doc_ids_searched=doc_ids_searched,
            processing_time_ms=elapsed_ms,
            timestamp=datetime.utcnow(),
        )

    # ── Status helpers ────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "num_documents": self.db.count_documents(),
            "num_chunks": self.vector_store.num_chunks,
            "num_queries": self.db.count_queries(),
            "vector_store_ready": self.vector_store.is_ready,
            "llm_available": self.llm.is_available(),
        }
