"""Document processor: extracts text from PDF/TXT files and splits it into chunks."""

import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DocumentChunk:
    """A single text chunk from a document."""

    def __init__(
        self,
        chunk_id: str,
        doc_id: str,
        content: str,
        chunk_index: int,
        filename: str,
    ) -> None:
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.content = content
        self.chunk_index = chunk_index
        self.filename = filename

    def __repr__(self) -> str:
        return f"DocumentChunk(id={self.chunk_id}, index={self.chunk_index}, len={len(self.content)})"


class DocumentProcessor:
    """Extracts text from uploaded documents and splits it into overlapping chunks."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        max_chunks: int = 500,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_chunks = max_chunks

    # ── Public API ────────────────────────────────────────────────────────────

    def process_file(self, file_path: Path, doc_id: str, filename: str) -> list[DocumentChunk]:
        """Extract text from *file_path* and return a list of :class:`DocumentChunk` objects."""
        logger.info("Processing file: %s (doc_id=%s)", filename, doc_id)

        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            text = self._extract_pdf(file_path)
        elif suffix == ".txt":
            text = self._extract_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        if not text.strip():
            raise ValueError(f"No text could be extracted from '{filename}'")

        text = self._clean_text(text)
        chunks = self._split_text(text)
        logger.info("Produced %d chunks from '%s'", len(chunks), filename)

        return [
            DocumentChunk(
                chunk_id=self._make_chunk_id(doc_id, idx),
                doc_id=doc_id,
                content=chunk,
                chunk_index=idx,
                filename=filename,
            )
            for idx, chunk in enumerate(chunks)
        ]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_txt(self, file_path: Path) -> str:
        """Read plain-text file, trying common encodings."""
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Unable to decode '{file_path}' with any supported encoding")

    def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from a PDF using PyMuPDF (fitz), with pdfplumber fallback."""
        text_parts: list[str] = []

        try:
            import fitz  # PyMuPDF

            with fitz.open(str(file_path)) as doc:
                for page in doc:
                    text_parts.append(page.get_text())
            return "\n".join(text_parts)
        except ImportError:
            logger.warning("PyMuPDF not available, falling back to pdfplumber")
        except Exception as exc:
            logger.warning("PyMuPDF failed (%s), falling back to pdfplumber", exc)

        try:
            import pdfplumber

            with pdfplumber.open(str(file_path)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n".join(text_parts)
        except ImportError:
            raise ImportError(
                "Neither PyMuPDF nor pdfplumber is installed. "
                "Install one of them to enable PDF support."
            )

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalise whitespace and remove control characters."""
        # Replace various whitespace with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Normalise multiple newlines → at most two
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip leading/trailing whitespace per line
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(lines)
        return text.strip()

    def _split_text(self, text: str) -> list[str]:
        """Split *text* into overlapping chunks of roughly :attr:`chunk_size` words."""
        words = text.split()
        if not words:
            return []

        chunks: list[str] = []
        start = 0

        while start < len(words) and len(chunks) < self.max_chunks:
            end = start + self.chunk_size
            chunk_words = words[start:end]
            chunk = " ".join(chunk_words)
            chunks.append(chunk)
            # Advance by (chunk_size - overlap) so consecutive chunks share context
            start += self.chunk_size - self.chunk_overlap

        return chunks

    @staticmethod
    def _make_chunk_id(doc_id: str, chunk_index: int) -> str:
        raw = f"{doc_id}_{chunk_index}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]
