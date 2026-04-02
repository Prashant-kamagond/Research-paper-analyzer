"""Tests for DocumentProcessor."""

import uuid
from pathlib import Path

import pytest

from backend.document_processor import DocumentChunk, DocumentProcessor


@pytest.fixture
def processor():
    return DocumentProcessor(chunk_size=50, chunk_overlap=10, max_chunks=100)


class TestDocumentChunk:
    def test_repr(self):
        chunk = DocumentChunk(
            chunk_id="abc123",
            doc_id="doc1",
            content="Hello world",
            chunk_index=0,
            filename="test.txt",
        )
        assert "abc123" in repr(chunk)
        assert "0" in repr(chunk)


class TestDocumentProcessor:
    def test_process_txt(self, processor, sample_txt_file):
        doc_id = str(uuid.uuid4())
        chunks = processor.process_file(sample_txt_file, doc_id, "sample_paper.txt")

        assert len(chunks) > 0
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        assert all(c.doc_id == doc_id for c in chunks)
        assert all(c.filename == "sample_paper.txt" for c in chunks)

    def test_chunk_indices_sequential(self, processor, sample_txt_file):
        doc_id = str(uuid.uuid4())
        chunks = processor.process_file(sample_txt_file, doc_id, "sample_paper.txt")
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_ids_unique(self, processor, sample_txt_file):
        doc_id = str(uuid.uuid4())
        chunks = processor.process_file(sample_txt_file, doc_id, "sample_paper.txt")
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_unsupported_extension_raises(self, processor, tmp_dir):
        bad_file = tmp_dir / "paper.docx"
        bad_file.write_bytes(b"fake content")
        with pytest.raises(ValueError, match="Unsupported"):
            processor.process_file(bad_file, "doc1", "paper.docx")

    def test_empty_file_raises(self, processor, tmp_dir):
        empty = tmp_dir / "empty.txt"
        empty.write_text("   \n\n  ", encoding="utf-8")
        with pytest.raises(ValueError):
            processor.process_file(empty, "doc1", "empty.txt")

    def test_clean_text_normalises_whitespace(self):
        raw = "Hello    world\n\n\n\nGoodbye"
        cleaned = DocumentProcessor._clean_text(raw)
        assert "    " not in cleaned
        assert "\n\n\n" not in cleaned

    def test_split_text_produces_overlapping_chunks(self):
        proc = DocumentProcessor(chunk_size=5, chunk_overlap=2, max_chunks=50)
        text = " ".join(f"word{i}" for i in range(20))
        chunks = proc._split_text(text)
        assert len(chunks) > 1
        # Each chunk should have at most chunk_size words
        for chunk in chunks:
            assert len(chunk.split()) <= 5

    def test_split_text_empty(self, processor):
        assert processor._split_text("") == []

    def test_max_chunks_respected(self, tmp_dir):
        proc = DocumentProcessor(chunk_size=5, chunk_overlap=1, max_chunks=3)
        text = " ".join(f"word{i}" for i in range(100))
        chunks = proc._split_text(text)
        assert len(chunks) <= 3

    def test_different_encodings(self, processor, tmp_dir):
        path = tmp_dir / "latin.txt"
        path.write_bytes("caf\xe9 na\xefve".encode("latin-1"))
        doc_id = str(uuid.uuid4())
        chunks = processor.process_file(path, doc_id, "latin.txt")
        assert len(chunks) > 0
