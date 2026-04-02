# Backend – API Reference

## Overview

The FastAPI backend exposes a RESTful API on **port 8000**.  
It orchestrates the full RAG pipeline: document ingestion → embedding → FAISS retrieval → LLM generation.

## Base URL

```
http://localhost:8000
```

## Endpoints

### System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check with counters |

### Documents

| Method | Path | Description |
|--------|------|-------------|
| POST | `/documents/upload` | Upload a PDF or TXT file |
| GET | `/documents` | List all indexed documents |
| DELETE | `/documents/{doc_id}` | Remove a document |

### Query

| Method | Path | Description |
|--------|------|-------------|
| POST | `/query` | Ask a question using RAG |

### History

| Method | Path | Description |
|--------|------|-------------|
| GET | `/history` | Paginated query history |
| DELETE | `/history` | Clear all history |

## Interactive Docs

Visit `http://localhost:8000/docs` for the full Swagger UI.

## Running the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```
