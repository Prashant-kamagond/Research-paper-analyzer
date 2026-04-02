# API Documentation

Base URL: `http://localhost:8000`

Interactive Swagger UI: `http://localhost:8000/docs`

---

## System

### GET /health

Returns system health and counters.

**Response 200**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "num_documents": 3,
  "num_queries": 12,
  "vector_store_ready": true,
  "llm_available": true
}
```

---

## Documents

### POST /documents/upload

Upload a PDF or TXT research paper.

**Request** – multipart/form-data
- `file` – The document file (PDF or TXT, max 50 MB)

**Response 201**
```json
{
  "success": true,
  "doc_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "my_paper.pdf",
  "num_chunks": 42,
  "message": "Successfully processed 'my_paper.pdf' into 42 chunks."
}
```

**Errors**
- `400` – Unsupported file type
- `413` – File too large
- `422` – Text extraction failed

---

### GET /documents

List all indexed documents.

**Response 200**
```json
{
  "documents": [
    {
      "doc_id": "550e8400-...",
      "filename": "my_paper.pdf",
      "file_type": "pdf",
      "file_size": 204800,
      "num_chunks": 42,
      "upload_timestamp": "2024-01-15T10:30:00",
      "status": "processed"
    }
  ],
  "total": 1
}
```

---

### DELETE /documents/{doc_id}

Remove a document from the index and database.

**Response 200**
```json
{
  "success": true,
  "message": "Document '550e8400-...' deleted"
}
```

**Errors**
- `404` – Document not found

---

## Query

### POST /query

Ask a question using RAG.

**Request**
```json
{
  "question": "What methodology was used in the study?",
  "doc_id": null,
  "top_k": 5,
  "temperature": 0.1
}
```

**Response 200**
```json
{
  "query_id": "abc123...",
  "question": "What methodology was used in the study?",
  "answer": "The study used a BERT-based model fine-tuned on...",
  "sources": [
    {
      "chunk_id": "def456...",
      "doc_id": "550e8400-...",
      "filename": "my_paper.pdf",
      "content": "We fine-tune a BERT-based model...",
      "relevance_score": 0.87,
      "chunk_index": 5
    }
  ],
  "doc_ids_searched": ["550e8400-..."],
  "processing_time_ms": 1234.5,
  "timestamp": "2024-01-15T10:35:00"
}
```

**Errors**
- `422` – No documents indexed, or invalid request

---

## History

### GET /history

Return paginated query history.

**Query params**
- `page` (int, default 1)
- `page_size` (int, default 20, max 100)

**Response 200**
```json
{
  "entries": [...],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### DELETE /history

Clear all query history.

**Response 200**
```json
{
  "success": true,
  "deleted": 42
}
```
