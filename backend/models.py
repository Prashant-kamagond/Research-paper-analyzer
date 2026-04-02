"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Document models ──────────────────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    """Metadata stored for each uploaded document."""

    doc_id: str
    filename: str
    file_type: str
    file_size: int
    num_chunks: int
    upload_timestamp: datetime
    status: str = "processed"


class DocumentResponse(BaseModel):
    """Response returned after a successful document upload."""

    success: bool
    doc_id: str
    filename: str
    num_chunks: int
    message: str


class DocumentListResponse(BaseModel):
    """List of all indexed documents."""

    documents: list[DocumentMetadata]
    total: int


# ── Query models ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Incoming query from the user."""

    question: str = Field(..., min_length=3, max_length=2000)
    doc_id: Optional[str] = Field(None, description="Restrict search to a specific document")
    top_k: int = Field(5, ge=1, le=20)
    temperature: float = Field(0.1, ge=0.0, le=2.0)


class SourceChunk(BaseModel):
    """A retrieved source chunk with relevance information."""

    chunk_id: str
    doc_id: str
    filename: str
    content: str
    relevance_score: float
    chunk_index: int


class QueryResponse(BaseModel):
    """Full response to a user query."""

    query_id: str
    question: str
    answer: str
    sources: list[SourceChunk]
    doc_ids_searched: list[str]
    processing_time_ms: float
    timestamp: datetime


# ── History models ───────────────────────────────────────────────────────────

class QueryHistoryEntry(BaseModel):
    """Single entry in the query history."""

    query_id: str
    question: str
    answer: str
    num_sources: int
    processing_time_ms: float
    timestamp: datetime
    doc_ids: list[str]


class QueryHistoryResponse(BaseModel):
    """Paginated query history."""

    entries: list[QueryHistoryEntry]
    total: int
    page: int
    page_size: int


# ── Health / Status models ────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """API health-check response."""

    status: str
    version: str
    num_documents: int
    num_queries: int
    vector_store_ready: bool
    llm_available: bool


# ── Error model ───────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
