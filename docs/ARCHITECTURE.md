# System Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP
┌──────────────────────────▼──────────────────────────────────────┐
│                   Streamlit Frontend (:8501)                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────┐  │
│  │  Home/Dash  │  │    Upload    │  │  Analyze │  │ History │  │
│  └─────────────┘  └──────────────┘  └──────────┘  └─────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │  REST API (httpx)
┌──────────────────────────▼──────────────────────────────────────┐
│                    FastAPI Backend (:8000)                        │
│                                                                  │
│  POST /documents/upload    GET /documents                        │
│  POST /query               GET /history                          │
│  GET  /health              DELETE /documents/{id}                │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    RAG Pipeline                           │   │
│  │                                                          │   │
│  │  1. DocumentProcessor                                    │   │
│  │     • PDF extraction (PyMuPDF / pdfplumber)              │   │
│  │     • TXT extraction                                     │   │
│  │     • Text cleaning                                      │   │
│  │     • Overlapping chunk splitting                        │   │
│  │                                                          │   │
│  │  2. Sentence Transformer (all-MiniLM-L6-v2)             │   │
│  │     • Encode chunks → 384-dim float32 vectors           │   │
│  │                                                          │   │
│  │  3. VectorStore (FAISS IndexFlatIP)                      │   │
│  │     • Cosine similarity search                           │   │
│  │     • Persist index + metadata to disk                   │   │
│  │                                                          │   │
│  │  4. LLMHandler (Ollama REST API)                         │   │
│  │     • Build RAG prompt (context + question)              │   │
│  │     • Generate / stream answer                           │   │
│  │     • Graceful fallback if Ollama unavailable            │   │
│  │                                                          │   │
│  │  5. Database (SQLite via sqlite3)                        │   │
│  │     • Document metadata                                  │   │
│  │     • Query history                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
┌───────▼───────┐                    ┌────────▼───────┐
│  Ollama LLM   │                    │  File System   │
│  (:11434)     │                    │  data/uploads  │
│  llama2, etc. │                    │  data/vectors  │
└───────────────┘                    │  data/db       │
                                     └────────────────┘
```

## Data Flow

### Upload

```
User → upload file → FastAPI → DocumentProcessor
  → extract text → split chunks → SentenceTransformer
  → embed → VectorStore.add_chunks() → FAISS index
  → VectorStore.save() → disk
  → Database.save_document() → SQLite
```

### Query

```
User → question → FastAPI → SentenceTransformer.encode(question)
  → VectorStore.search() → top-k chunks
  → LLMHandler.generate(question, chunks) → Ollama
  → answer + sources → Database.save_query() → SQLite
  → return QueryResponse → Streamlit → User
```

## Component Responsibilities

| Component | File | Responsibility |
|-----------|------|----------------|
| `DocumentProcessor` | `backend/document_processor.py` | Text extraction and chunking |
| `VectorStore` | `backend/vector_store.py` | FAISS index management |
| `LLMHandler` | `backend/llm_handler.py` | Ollama LLM integration |
| `Database` | `backend/database.py` | SQLite CRUD operations |
| `RAGPipeline` | `backend/rag_pipeline.py` | Orchestration |
| FastAPI app | `backend/app.py` | HTTP API and validation |
| Streamlit app | `frontend/` | User interface |
