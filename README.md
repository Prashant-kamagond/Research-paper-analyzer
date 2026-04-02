# Research Paper Analyzer - GenAI RAG Application

A production-ready Research Paper Analyzer powered by Generative AI with Retrieval-Augmented Generation (RAG). Upload research papers, ask intelligent questions, and get answers backed by retrieved document context.

## Features
- 📄 Support for PDF and TXT documents
- 🔍 Semantic search using FAISS vector database
- 🤖 Intelligent responses using Llama LLM
- 💬 Conversational Q&A interface
- 📊 Query history and analytics
- 🐳 Docker support for easy deployment

## Tech Stack
- **Backend**: FastAPI
- **Frontend**: Streamlit
- **Vector DB**: FAISS
- **LLM**: Llama (via Ollama)
- **Embeddings**: Sentence Transformers
- **Database**: SQLite

## Quick Start
See [SETUP.md](SETUP.md) for detailed installation instructions.

```bash
# Clone the repository
git clone https://github.com/Prashant-kamagond/research-paper-analyzer.git
cd research-paper-analyzer

# Using Docker Compose
docker-compose up

# Visit
# - Backend API: http://localhost:8000
# - Frontend: http://localhost:8501
```

## Project Structure
- `backend/` - FastAPI backend with RAG pipeline
- `frontend/` - Streamlit user interface
- `tests/` - Unit tests
- `data/` - Documents, vectors, and metadata

## Documentation
- [Setup Guide](SETUP.md)
- [API Documentation](backend/README.md)
- [Architecture](docs/ARCHITECTURE.md)

## Author
Prashant Kamagond

## License
MIT