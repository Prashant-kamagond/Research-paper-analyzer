# Setup Guide

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) (for LLM generation)
- Docker & Docker Compose (optional, for containerised deployment)

---

## Option 1 – Local Development

### 1. Clone the repository

```bash
git clone https://github.com/Prashant-kamagond/Research-paper-analyzer.git
cd Research-paper-analyzer
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env to suit your setup
```

### 5. Start Ollama and pull a model

```bash
ollama serve &
ollama pull llama2
```

### 6. Start the backend

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

Visit `http://localhost:8000/docs` for the Swagger UI.

### 7. Start the frontend

Open a new terminal:

```bash
streamlit run frontend/app.py
```

Visit `http://localhost:8501`.

---

## Option 2 – Docker Compose

```bash
cp .env.example .env
docker-compose up --build
```

Services:
- Backend API: `http://localhost:8000`
- Frontend UI: `http://localhost:8501`
- Ollama:      `http://localhost:11434`

Pull a model into the running Ollama container:

```bash
docker exec -it rpa-ollama ollama pull llama2
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Backend unreachable | Check that `uvicorn` is running on port 8000 |
| LLM offline | Run `ollama serve` and `ollama pull llama2` |
| PDF extraction fails | Install PyMuPDF: `pip install PyMuPDF` |
| Empty search results | Lower `SIMILARITY_THRESHOLD` in `.env` |
