"""FAISS vector store wrapper for semantic similarity search."""

import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages FAISS index and chunk metadata for semantic search.

    Each entry in the index corresponds to a :class:`~backend.document_processor.DocumentChunk`.
    Metadata (doc_id, chunk_id, filename, content, chunk_index) is stored alongside the
    FAISS index and serialised to disk with :meth:`save` / :meth:`load`.
    """

    def __init__(self, embedding_dimension: int = 384) -> None:
        self.embedding_dimension = embedding_dimension
        self._index = None  # faiss.IndexFlatIP
        self._metadata: list[dict] = []  # parallel list to the FAISS vectors

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        """Return *True* when the index contains at least one vector."""
        return self._index is not None and len(self._metadata) > 0

    @property
    def num_documents(self) -> int:
        """Total number of unique documents indexed."""
        return len({m["doc_id"] for m in self._metadata})

    @property
    def num_chunks(self) -> int:
        """Total number of chunks indexed."""
        return len(self._metadata)

    def add_chunks(self, embeddings: np.ndarray, metadata_list: list[dict]) -> None:
        """Add *embeddings* (shape ``[N, D]``) with corresponding *metadata_list* to the index."""
        import faiss

        if embeddings.ndim != 2 or embeddings.shape[1] != self.embedding_dimension:
            raise ValueError(
                f"Expected embeddings of shape (N, {self.embedding_dimension}), "
                f"got {embeddings.shape}"
            )

        # Normalise for cosine similarity via inner product
        faiss.normalize_L2(embeddings)

        if self._index is None:
            self._index = faiss.IndexFlatIP(self.embedding_dimension)

        self._index.add(embeddings)
        self._metadata.extend(metadata_list)
        logger.info("Added %d chunks; total=%d", len(metadata_list), self.num_chunks)

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        doc_id: Optional[str] = None,
        threshold: float = 0.0,
    ) -> list[dict]:
        """Return top-*k* chunks most similar to *query_embedding*.

        Args:
            query_embedding: 1-D or 2-D array of shape ``(D,)`` or ``(1, D)``.
            top_k:           Maximum number of results.
            doc_id:          When provided, restrict results to this document.
            threshold:       Minimum cosine similarity score (0–1).

        Returns:
            List of metadata dicts enriched with a ``relevance_score`` key.
        """
        import faiss

        if not self.is_ready:
            logger.warning("Vector store is empty; returning no results")
            return []

        # Ensure 2-D float32
        embedding = np.array(query_embedding, dtype=np.float32)
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        faiss.normalize_L2(embedding)

        # Fetch more than top_k so we can filter by doc_id afterwards
        fetch_k = min(top_k * 10 if doc_id else top_k, self.num_chunks)
        scores, indices = self._index.search(embedding, fetch_k)

        results: list[dict] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            if score < threshold:
                continue
            meta = dict(self._metadata[idx])
            meta["relevance_score"] = float(score)
            if doc_id is None or meta["doc_id"] == doc_id:
                results.append(meta)
            if len(results) >= top_k:
                break

        return results

    def remove_document(self, doc_id: str) -> int:
        """Remove all chunks belonging to *doc_id*.  Returns the number removed."""
        if not self.is_ready:
            return 0

        import faiss

        keep_indices = [i for i, m in enumerate(self._metadata) if m["doc_id"] != doc_id]
        removed = len(self._metadata) - len(keep_indices)

        if removed == 0:
            return 0

        # Rebuild the index from the kept vectors
        all_vectors = self._index.reconstruct_n(0, self._index.ntotal)
        kept_vectors = all_vectors[keep_indices].astype(np.float32)

        self._index = faiss.IndexFlatIP(self.embedding_dimension)
        if len(kept_vectors) > 0:
            self._index.add(kept_vectors)

        self._metadata = [self._metadata[i] for i in keep_indices]
        logger.info("Removed %d chunks for doc_id=%s", removed, doc_id)
        return removed

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, directory: Path) -> None:
        """Persist the FAISS index and metadata to *directory*."""
        import faiss

        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(directory / "faiss.index"))
        with open(directory / "metadata.pkl", "wb") as fh:
            pickle.dump(self._metadata, fh)
        logger.info("Vector store saved to %s", directory)

    def load(self, directory: Path) -> bool:
        """Load index and metadata from *directory*.  Returns *True* on success."""
        import faiss

        index_path = directory / "faiss.index"
        meta_path = directory / "metadata.pkl"

        if not index_path.exists() or not meta_path.exists():
            logger.info("No persisted vector store found at %s", directory)
            return False

        self._index = faiss.read_index(str(index_path))
        with open(meta_path, "rb") as fh:
            self._metadata = pickle.load(fh)
        logger.info("Vector store loaded from %s (%d chunks)", directory, self.num_chunks)
        return True
