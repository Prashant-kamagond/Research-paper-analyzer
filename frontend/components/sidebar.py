"""Sidebar component displayed on every Streamlit page."""

import streamlit as st

from frontend.config import API_BASE_URL, APP_ICON, APP_TAGLINE, APP_TITLE
from frontend.components.utils import api_get


def render_sidebar() -> None:
    """Render the shared sidebar with branding, status, and navigation."""
    with st.sidebar:
        # Branding
        st.markdown(f"## {APP_ICON} {APP_TITLE}")
        st.caption(APP_TAGLINE)
        st.divider()

        # Backend status
        _render_status()
        st.divider()

        # Quick stats
        _render_stats()
        st.divider()

        # Footer
        st.caption(f"🔗 API: `{API_BASE_URL}`")
        st.caption("Built with FastAPI · FAISS · Streamlit")


def _render_status() -> None:
    health = api_get("/health")
    if health is None:
        st.error("⚠️ Backend unreachable")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Status", "🟢 Online")
    with col2:
        llm = "🟢" if health.get("llm_available") else "🔴"
        st.metric("LLM", f"{llm} Ollama")


def _render_stats() -> None:
    health = api_get("/health")
    if health is None:
        return

    st.markdown("**📊 Quick Stats**")
    c1, c2 = st.columns(2)
    c1.metric("Documents", health.get("num_documents", 0))
    c2.metric("Queries", health.get("num_queries", 0))
