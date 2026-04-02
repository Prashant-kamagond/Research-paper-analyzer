"""FastAPI main application."""

import logging
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.models import (
    DocumentListResponse,
    DocumentMetadata,
    DocumentResponse,
    ErrorResponse,
    HealthResponse,
    QueryHistoryEntry,
    QueryHistoryResponse,
    QueryRequest,
    QueryResponse,
)
from backend.rag_pipeline import RAGPipeline

# ── Logging ───────────────────────────────────────────────────────────────────

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "app.log"),
    ],
)
logger = logging.getLogger(__name__)

# ── App lifecycle ─────────────────────────────────────────────────────────────

pipeline: Optional[RAGPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001
    global pipeline
    logger.info("Starting Research Paper Analyzer API v%s", settings.app_version)
    pipeline = RAGPipeline()
    logger.info("RAG pipeline ready. Vector store: %s", pipeline.vector_store.is_ready)
    yield
    logger.info("Shutting down API")


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Production-ready Research Paper Analyzer using RAG, FAISS, "
        "Sentence Transformers, and Llama/Ollama."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_pipeline() -> RAGPipeline:
    if pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline not initialised yet. Try again in a moment.",
        )
    return pipeline


def _validate_upload(file: UploadFile) -> None:
    suffix = Path(file.filename or "").suffix.lstrip(".").lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '.{suffix}' not allowed. Allowed: {settings.allowed_extensions}",
        )


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Return API health status and counters."""
    p = _get_pipeline()
    status_info = p.get_status()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        num_documents=status_info["num_documents"],
        num_queries=status_info["num_queries"],
        vector_store_ready=status_info["vector_store_ready"],
        llm_available=status_info["llm_available"],
    )


@app.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Documents"],
)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF or TXT research paper and index it for Q&A."""
    _validate_upload(file)
    p = _get_pipeline()

    # Save to upload directory
    filename = file.filename or f"upload_{uuid.uuid4()}"
    dest_path = settings.upload_dir / filename

    try:
        with open(dest_path, "wb") as fh:
            shutil.copyfileobj(file.file, fh)
        logger.info("Saved upload: %s (%d bytes)", filename, dest_path.stat().st_size)

        # Check file size
        size_mb = dest_path.stat().st_size / (1024 * 1024)
        if size_mb > settings.max_file_size_mb:
            dest_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {settings.max_file_size_mb} MB limit",
            )

        result = p.ingest_document(dest_path, filename)
        return DocumentResponse(
            success=True,
            doc_id=result["doc_id"],
            filename=result["filename"],
            num_chunks=result["num_chunks"],
            message=f"Successfully processed '{filename}' into {result['num_chunks']} chunks.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to process upload '%s'", filename)
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@app.get("/documents", response_model=DocumentListResponse, tags=["Documents"])
async def list_documents():
    """Return metadata for all indexed documents."""
    p = _get_pipeline()
    docs_raw = p.db.list_documents()
    docs = [
        DocumentMetadata(
            doc_id=d["doc_id"],
            filename=d["filename"],
            file_type=d["file_type"],
            file_size=d["file_size"],
            num_chunks=d["num_chunks"],
            upload_timestamp=datetime.fromisoformat(d["upload_timestamp"]),
            status=d["status"],
        )
        for d in docs_raw
    ]
    return DocumentListResponse(documents=docs, total=len(docs))


@app.delete("/documents/{doc_id}", tags=["Documents"])
async def delete_document(doc_id: str):
    """Remove a document from the index and database."""
    p = _get_pipeline()
    removed = p.delete_document(doc_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )
    return {"success": True, "message": f"Document '{doc_id}' deleted"}


@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def query_documents(request: QueryRequest):
    """Answer a question using RAG over the indexed documents."""
    p = _get_pipeline()
    try:
        response = p.query(
            question=request.question,
            doc_id=request.doc_id,
            top_k=request.top_k,
            temperature=request.temperature,
        )
        return response
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception:
        logger.exception("Query processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your query.",
        )


@app.get("/history", response_model=QueryHistoryResponse, tags=["History"])
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Return paginated query history."""
    p = _get_pipeline()
    entries_raw, total = p.db.get_query_history(page=page, page_size=page_size)
    entries = [
        QueryHistoryEntry(
            query_id=e["query_id"],
            question=e["question"],
            answer=e["answer"],
            num_sources=len(e.get("sources", [])),
            processing_time_ms=e["processing_time_ms"],
            timestamp=datetime.fromisoformat(e["timestamp"]),
            doc_ids=e.get("doc_ids", []),
        )
        for e in entries_raw
    ]
    return QueryHistoryResponse(
        entries=entries,
        total=total,
        page=page,
        page_size=page_size,
    )


@app.delete("/history", tags=["History"])
async def clear_history():
    """Delete all query history."""
    p = _get_pipeline()
    deleted = p.db.clear_history()
    return {"success": True, "deleted": deleted}


# ── Error handlers ────────────────────────────────────────────────────────────


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):  # noqa: ANN001
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
        ).model_dump(mode="json"),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
