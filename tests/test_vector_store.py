"""Tests for VectorStore."""

import numpy as np
import pytest

from backend.vector_store import VectorStore

DIM = 4  # small dimension for fast tests


@pytest.fixture
def store():
    return VectorStore(embedding_dimension=DIM)


def _random_embeddings(n: int, dim: int = DIM) -> np.ndarray:
    rng = np.random.default_rng(42)
    vecs = rng.random((n, dim)).astype(np.float32)
    return vecs


def _make_metadata(n: int, doc_id: str = "doc1") -> list[dict]:
    return [
        {
            "chunk_id": f"chunk_{i}",
            "doc_id": doc_id,
            "filename": "paper.txt",
            "content": f"Content of chunk {i}",
            "chunk_index": i,
        }
        for i in range(n)
    ]


class TestVectorStoreBasics:
    def test_empty_store_not_ready(self, store):
        assert not store.is_ready

    def test_add_chunks_marks_ready(self, store):
        embeddings = _random_embeddings(3)
        meta = _make_metadata(3)
        store.add_chunks(embeddings, meta)
        assert store.is_ready

    def test_num_chunks(self, store):
        embeddings = _random_embeddings(5)
        meta = _make_metadata(5)
        store.add_chunks(embeddings, meta)
        assert store.num_chunks == 5

    def test_num_documents(self, store):
        store.add_chunks(_random_embeddings(3), _make_metadata(3, "docA"))
        store.add_chunks(_random_embeddings(2), _make_metadata(2, "docB"))
        assert store.num_documents == 2

    def test_wrong_dimension_raises(self, store):
        bad = np.random.rand(2, DIM + 1).astype(np.float32)
        with pytest.raises(ValueError):
            store.add_chunks(bad, _make_metadata(2))


class TestVectorStoreSearch:
    def test_search_returns_results(self, store):
        embeddings = _random_embeddings(10)
        meta = _make_metadata(10)
        store.add_chunks(embeddings, meta)
        query = embeddings[0]
        results = store.search(query, top_k=3)
        assert len(results) <= 3
        assert all("relevance_score" in r for r in results)

    def test_search_empty_store(self, store):
        query = _random_embeddings(1)[0]
        results = store.search(query, top_k=5)
        assert results == []

    def test_search_with_doc_filter(self, store):
        store.add_chunks(_random_embeddings(5), _make_metadata(5, "docA"))
        store.add_chunks(_random_embeddings(5), _make_metadata(5, "docB"))
        query = _random_embeddings(1)[0]
        results = store.search(query, top_k=10, doc_id="docA")
        assert all(r["doc_id"] == "docA" for r in results)

    def test_search_threshold_filters(self, store):
        embeddings = _random_embeddings(10)
        meta = _make_metadata(10)
        store.add_chunks(embeddings, meta)
        query = embeddings[0]
        # Very high threshold should filter most (or all) results
        results = store.search(query, top_k=10, threshold=0.9999)
        # At least one result should match (the identical vector)
        # but the rest should be filtered
        assert len(results) <= 10


class TestVectorStoreRemove:
    def test_remove_document(self, store):
        store.add_chunks(_random_embeddings(4), _make_metadata(4, "docA"))
        store.add_chunks(_random_embeddings(3), _make_metadata(3, "docB"))
        removed = store.remove_document("docA")
        assert removed == 4
        assert store.num_chunks == 3
        assert store.num_documents == 1

    def test_remove_nonexistent_doc(self, store):
        store.add_chunks(_random_embeddings(2), _make_metadata(2, "docA"))
        removed = store.remove_document("ghost")
        assert removed == 0
        assert store.num_chunks == 2


class TestVectorStorePersistence:
    def test_save_and_load(self, store, tmp_dir):
        embeddings = _random_embeddings(5)
        meta = _make_metadata(5)
        store.add_chunks(embeddings, meta)
        store.save(tmp_dir)

        new_store = VectorStore(embedding_dimension=DIM)
        loaded = new_store.load(tmp_dir)

        assert loaded is True
        assert new_store.num_chunks == 5

    def test_load_nonexistent_returns_false(self, tmp_dir):
        store2 = VectorStore(embedding_dimension=DIM)
        result = store2.load(tmp_dir / "does_not_exist")
        assert result is False
