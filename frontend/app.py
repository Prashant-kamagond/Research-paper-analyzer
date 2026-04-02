"""Streamlit main entry point – Home / Dashboard page."""

import streamlit as st

from frontend.config import APP_ICON, APP_TAGLINE, APP_TITLE
from frontend.components.sidebar import render_sidebar
from frontend.components.utils import api_get, backend_is_online

st.set_page_config(
    page_title=f"{APP_TITLE} – Home",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="text-align:center; padding: 2rem 0 1rem;">
        <h1 style="font-size:3rem;">{APP_ICON} {APP_TITLE}</h1>
        <p style="font-size:1.2rem; color:#888;">{APP_TAGLINE}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Status banner ─────────────────────────────────────────────────────────────
if not backend_is_online():
    st.warning(
        "⚠️ The backend API is not reachable. "
        "Start it with `uvicorn backend.app:app --port 8000`."
    )
else:
    health = api_get("/health")
    if health:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📄 Documents", health.get("num_documents", 0))
        c2.metric("💬 Queries", health.get("num_queries", 0))
        c3.metric("🔍 Vector Index", "Ready" if health.get("vector_store_ready") else "Empty")
        c4.metric("🤖 LLM", "Online" if health.get("llm_available") else "Offline")

st.divider()

# ── How it works ──────────────────────────────────────────────────────────────
st.subheader("🚀 How it works")

cols = st.columns(4)
steps = [
    ("📤", "Upload", "Upload your PDF or TXT research papers"),
    ("⚙️", "Index", "Documents are chunked and embedded with Sentence Transformers"),
    ("🔍", "Retrieve", "Your question is matched to the most relevant passages via FAISS"),
    ("🤖", "Generate", "Llama generates a grounded answer with source citations"),
]
for col, (icon, title, desc) in zip(cols, steps):
    with col:
        st.markdown(
            f"""
            <div style="background:#1e1e2e;border-radius:12px;padding:1.2rem;text-align:center;height:160px;">
                <div style="font-size:2.5rem;">{icon}</div>
                <strong>{title}</strong>
                <p style="color:#aaa;font-size:0.85rem;margin-top:0.5rem;">{desc}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# ── Quick-start ───────────────────────────────────────────────────────────────
st.subheader("📋 Quick Start")
st.markdown(
    """
1. **Upload** – Go to the *Upload* page and add your research papers (PDF or TXT).
2. **Analyze** – Go to the *Analyze* page, type a question, and get an AI-generated answer.
3. **History** – Review past queries on the *History* page.
4. **Settings** – Configure model parameters on the *Settings* page.
"""
)

st.info(
    "💡 **Tip:** For best results, ask specific questions about methods, "
    "results, or conclusions from the papers you've uploaded."
)
