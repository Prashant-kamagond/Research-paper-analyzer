"""Q&A Analysis page."""

import streamlit as st

from frontend.config import (
    APP_ICON,
    APP_TITLE,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    MAX_QUESTION_LENGTH,
)
from frontend.components.sidebar import render_sidebar
from frontend.components.utils import api_get, api_post, format_ms, init_session_state

st.set_page_config(
    page_title=f"{APP_TITLE} – Analyze",
    page_icon=APP_ICON,
    layout="wide",
)

render_sidebar()
init_session_state({"last_response": None, "question_input": ""})

st.title("💬 Analyze Research Papers")
st.caption("Ask questions and get AI-generated answers grounded in your uploaded papers.")

# ── Check documents ───────────────────────────────────────────────────────────

health = api_get("/health")
if health and not health.get("vector_store_ready"):
    st.warning("⚠️ No documents are indexed yet. Please upload papers on the **Upload** page first.")

# ── Sidebar controls ──────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Query Settings")
    top_k = st.slider("Top-K results", 1, 20, DEFAULT_TOP_K)
    temperature = st.slider("Temperature", 0.0, 2.0, DEFAULT_TEMPERATURE, step=0.05)

    # Filter by document
    docs_data = api_get("/documents")
    doc_options = {"All documents": None}
    if docs_data:
        for d in docs_data.get("documents", []):
            doc_options[d["filename"]] = d["doc_id"]

    selected_doc_label = st.selectbox("Restrict to document", list(doc_options.keys()))
    selected_doc_id = doc_options[selected_doc_label]

# ── Question input ────────────────────────────────────────────────────────────

question = st.text_area(
    "Your question",
    placeholder="e.g. What evaluation metrics were used in this study?",
    max_chars=MAX_QUESTION_LENGTH,
    height=100,
)

col_ask, col_clear = st.columns([1, 5])
with col_ask:
    ask_clicked = st.button("🔍 Ask", type="primary", disabled=not question.strip())
with col_clear:
    if st.button("🗑️ Clear") and st.session_state.last_response:
        st.session_state.last_response = None
        st.rerun()

# ── Ask ───────────────────────────────────────────────────────────────────────

if ask_clicked and question.strip():
    with st.spinner("Thinking…"):
        payload = {
            "question": question.strip(),
            "top_k": top_k,
            "temperature": temperature,
        }
        if selected_doc_id:
            payload["doc_id"] = selected_doc_id

        response = api_post("/query", json=payload)

    if response:
        st.session_state.last_response = response

# ── Display response ──────────────────────────────────────────────────────────

resp = st.session_state.last_response
if resp:
    st.divider()

    # Answer
    st.subheader("🤖 Answer")
    st.markdown(resp["answer"])

    # Meta
    st.caption(
        f"⏱️ {format_ms(resp['processing_time_ms'])}  ·  "
        f"Query ID: `{resp['query_id']}`"
    )

    # Sources
    sources = resp.get("sources", [])
    if sources:
        st.divider()
        st.subheader(f"📎 Sources ({len(sources)})")
        for i, src in enumerate(sources, 1):
            relevance_pct = int(src["relevance_score"] * 100)
            with st.expander(
                f"[{i}] {src['filename']} – relevance {relevance_pct}%",
                expanded=(i == 1),
            ):
                st.progress(src["relevance_score"], text=f"Similarity: {src['relevance_score']:.3f}")
                st.markdown(f"**Chunk #{src['chunk_index']}**")
                st.text(src["content"][:800] + ("…" if len(src["content"]) > 800 else ""))
                st.caption(f"Doc ID: `{src['doc_id']}`")
