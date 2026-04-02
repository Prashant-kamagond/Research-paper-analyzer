"""Tests for the RAG pipeline (integration-style, no Ollama required)."""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.document_processor import DocumentProcessor
from backend.vector_store import VectorStore


class TestRAGPipelineComponents:
    """Test individual pipeline steps without requiring real models."""

    def test_processor_and_vector_store_integration(self, sample_txt_file, tmp_dir):
        """Process a document, embed with a stub, and verify retrieval."""
        processor = DocumentProcessor(chunk_size=30, chunk_overlap=5, max_chunks=50)
        doc_id = str(uuid.uuid4())
        chunks = processor.process_file(sample_txt_file, doc_id, "sample_paper.txt")
        assert len(chunks) > 0

        # Use deterministic random embeddings as a stub for the real model
        dim = 8
        rng = np.random.default_rng(0)
        embeddings = rng.random((len(chunks), dim)).astype(np.float32)

        store = VectorStore(embedding_dimension=dim)
        meta = [
            {
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "filename": c.filename,
                "content": c.content,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]
        store.add_chunks(embeddings, meta)
        assert store.is_ready

        # Query
        query_emb = rng.random((dim,)).astype(np.float32)
        results = store.search(query_emb, top_k=3)
        assert len(results) <= 3
        assert all("content" in r for r in results)

    def test_processor_preserves_content(self, sample_txt_file):
        processor = DocumentProcessor(chunk_size=20, chunk_overlap=5)
        doc_id = str(uuid.uuid4())
        chunks = processor.process_file(sample_txt_file, doc_id, "sample_paper.txt")

        # All chunk content should be non-empty strings
        assert all(isinstance(c.content, str) and len(c.content) > 0 for c in chunks)

    def test_remove_and_search_after_deletion(self, sample_txt_file, tmp_dir):
        processor = DocumentProcessor(chunk_size=30, chunk_overlap=5)
        doc_id = str(uuid.uuid4())
        chunks = processor.process_file(sample_txt_file, doc_id, "sample_paper.txt")

        dim = 8
        rng = np.random.default_rng(1)
        embeddings = rng.random((len(chunks), dim)).astype(np.float32)

        store = VectorStore(embedding_dimension=dim)
        meta = [
            {
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "filename": c.filename,
                "content": c.content,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]
        store.add_chunks(embeddings, meta)

        removed = store.remove_document(doc_id)
        assert removed == len(chunks)
        assert not store.is_ready

        query_emb = rng.random((dim,)).astype(np.float32)
        results = store.search(query_emb, top_k=5)
        assert results == []
