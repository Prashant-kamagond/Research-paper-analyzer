"""Settings page."""

import streamlit as st

from frontend.config import API_BASE_URL, APP_ICON, APP_TITLE
from frontend.components.sidebar import render_sidebar
from frontend.components.utils import api_get

st.set_page_config(
    page_title=f"{APP_TITLE} – Settings",
    page_icon=APP_ICON,
    layout="wide",
)

render_sidebar()

st.title("⚙️ Settings")
st.caption("Configuration and status information.")

# ── Backend info ──────────────────────────────────────────────────────────────

st.subheader("🔗 Backend Connection")
st.code(f"API URL: {API_BASE_URL}", language=None)

health = api_get("/health")
if health:
    st.success("✅ Backend is reachable")

    st.subheader("📊 System Status")
    c1, c2, c3 = st.columns(3)
    c1.metric("Documents indexed", health.get("num_documents", 0))
    c2.metric("Queries answered", health.get("num_queries", 0))
    c3.metric("API version", health.get("version", "—"))

    st.subheader("🤖 LLM Status")
    if health.get("llm_available"):
        st.success("✅ Ollama is running and the LLM is available")
    else:
        st.warning(
            "⚠️ Ollama is not running. Answers will fall back to context-only mode.\n\n"
            "Start Ollama with:\n```bash\nollama serve\n```\n"
            "Then pull a model:\n```bash\nollama pull llama2\n```"
        )

    st.subheader("🔍 Vector Store")
    if health.get("vector_store_ready"):
        st.success("✅ FAISS index is populated and ready for queries")
    else:
        st.info("ℹ️ Vector store is empty. Upload documents to populate it.")
else:
    st.error(
        "❌ Cannot reach backend. Make sure the API is running:\n"
        "```bash\nuvicorn backend.app:app --port 8000\n```"
    )

# ── Environment tips ──────────────────────────────────────────────────────────

st.subheader("📝 Environment Variables")
st.markdown(
    """
Copy `.env.example` to `.env` and adjust the values:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama service URL |
| `OLLAMA_MODEL` | `llama2` | Model to use for generation |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformer model |
| `CHUNK_SIZE` | `500` | Words per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `TOP_K_RESULTS` | `5` | Default number of retrieved chunks |
| `LLM_TEMPERATURE` | `0.1` | Generation temperature |
| `API_BASE_URL` | `http://localhost:8000` | Frontend → backend URL |
"""
)
