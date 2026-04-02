# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Backend stage ─────────────────────────────────────────────────────────────
FROM base AS backend

COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/backend-requirements.txt

COPY backend/ ./backend/
COPY .env.example .env

RUN mkdir -p data/uploads data/vectors data/db logs

EXPOSE 8000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]

# ── Frontend stage ────────────────────────────────────────────────────────────
FROM base AS frontend

COPY frontend/requirements.txt /tmp/frontend-requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/frontend-requirements.txt

COPY frontend/ ./frontend/

EXPOSE 8501

CMD ["streamlit", "run", "frontend/app.py", \
     "--server.address", "0.0.0.0", \
     "--server.port", "8501", \
     "--server.headless", "true"]
