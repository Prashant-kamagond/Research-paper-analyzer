"""SQLite database layer for document metadata and query history."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger(__name__)


class Database:
    """Thin wrapper around SQLite that handles document metadata and query history."""

    def __init__(self, db_path: str = "data/db/papers.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ── Connection management ─────────────────────────────────────────────────

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Create tables if they do not already exist."""
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id          TEXT PRIMARY KEY,
                    filename        TEXT NOT NULL,
                    file_type       TEXT NOT NULL,
                    file_size       INTEGER NOT NULL,
                    num_chunks      INTEGER NOT NULL DEFAULT 0,
                    upload_timestamp TEXT NOT NULL,
                    status          TEXT NOT NULL DEFAULT 'processed'
                );

                CREATE TABLE IF NOT EXISTS query_history (
                    query_id            TEXT PRIMARY KEY,
                    question            TEXT NOT NULL,
                    answer              TEXT NOT NULL,
                    sources_json        TEXT NOT NULL DEFAULT '[]',
                    doc_ids_json        TEXT NOT NULL DEFAULT '[]',
                    processing_time_ms  REAL NOT NULL DEFAULT 0.0,
                    timestamp           TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_queries_timestamp
                    ON query_history(timestamp DESC);
                """
            )
        logger.info("Database schema initialised at %s", self.db_path)

    # ── Document operations ───────────────────────────────────────────────────

    def save_document(
        self,
        doc_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        num_chunks: int,
    ) -> None:
        """Insert or replace document metadata."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents
                    (doc_id, filename, file_type, file_size, num_chunks, upload_timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?, 'processed')
                """,
                (doc_id, filename, file_type, file_size, num_chunks, datetime.utcnow().isoformat()),
            )
        logger.debug("Saved document metadata: %s (%s)", filename, doc_id)

    def get_document(self, doc_id: str) -> Optional[dict]:
        """Return metadata dict for *doc_id*, or *None* if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_documents(self) -> list[dict]:
        """Return all documents ordered by upload time (newest first)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY upload_timestamp DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_document(self, doc_id: str) -> bool:
        """Delete document record.  Returns *True* if a row was removed."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        return cursor.rowcount > 0

    def count_documents(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    # ── Query history operations ──────────────────────────────────────────────

    def save_query(
        self,
        query_id: str,
        question: str,
        answer: str,
        sources: list[dict],
        doc_ids: list[str],
        processing_time_ms: float,
    ) -> None:
        """Persist a query and its answer."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO query_history
                    (query_id, question, answer, sources_json, doc_ids_json,
                     processing_time_ms, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    question,
                    answer,
                    json.dumps(sources),
                    json.dumps(doc_ids),
                    processing_time_ms,
                    datetime.utcnow().isoformat(),
                ),
            )

    def get_query_history(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        """Return paginated query history and total count."""
        offset = (page - 1) * page_size
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM query_history").fetchone()[0]
            rows = conn.execute(
                """
                SELECT * FROM query_history
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            ).fetchall()
        entries = []
        for row in rows:
            entry = dict(row)
            entry["sources"] = json.loads(entry.pop("sources_json", "[]"))
            entry["doc_ids"] = json.loads(entry.pop("doc_ids_json", "[]"))
            entries.append(entry)
        return entries, total

    def count_queries(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM query_history").fetchone()[0]

    def clear_history(self) -> int:
        """Delete all query history.  Returns the number of rows deleted."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM query_history")
        return cursor.rowcount
