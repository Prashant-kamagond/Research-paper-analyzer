"""Document Upload page."""

import streamlit as st

from frontend.config import ALLOWED_FILE_TYPES, APP_ICON, APP_TITLE, MAX_FILE_SIZE_MB
from frontend.components.sidebar import render_sidebar
from frontend.components.utils import api_delete, api_get, format_file_size

st.set_page_config(
    page_title=f"{APP_TITLE} – Upload",
    page_icon=APP_ICON,
    layout="wide",
)

render_sidebar()

st.title("📤 Upload Research Papers")
st.caption("Supported formats: PDF, TXT · Max size: 50 MB per file")

# ── Upload form ───────────────────────────────────────────────────────────────

uploaded_files = st.file_uploader(
    "Choose files",
    type=ALLOWED_FILE_TYPES,
    accept_multiple_files=True,
    help=f"Upload one or more research papers (PDF or TXT, max {MAX_FILE_SIZE_MB} MB each)",
)

if uploaded_files:
    if st.button("🚀 Upload & Index", type="primary"):
        import httpx

        from frontend.config import API_BASE_URL

        progress = st.progress(0, text="Preparing…")
        results = []

        for i, file in enumerate(uploaded_files):
            progress.progress(
                int((i / len(uploaded_files)) * 100),
                text=f"Uploading {file.name}…",
            )
            try:
                resp = httpx.post(
                    f"{API_BASE_URL}/documents/upload",
                    files={"file": (file.name, file.getvalue(), file.type or "application/octet-stream")},
                    timeout=120,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    results.append(("✅", file.name, data.get("num_chunks", "?"), data.get("doc_id")))
                else:
                    detail = resp.json().get("detail", resp.text)
                    results.append(("❌", file.name, detail, None))
            except Exception as exc:
                results.append(("❌", file.name, str(exc), None))

        progress.progress(100, text="Done!")

        for icon, name, info, _ in results:
            if icon == "✅":
                st.success(f"{icon} **{name}** – indexed ({info} chunks)")
            else:
                st.error(f"{icon} **{name}** – {info}")

        st.balloons()

st.divider()

# ── Indexed documents ─────────────────────────────────────────────────────────

st.subheader("📚 Indexed Documents")

data = api_get("/documents")
if data is None:
    st.warning("Could not reach the backend. Is it running?")
elif data.get("total", 0) == 0:
    st.info("No documents indexed yet. Upload some papers above!")
else:
    docs = data["documents"]
    st.caption(f"{data['total']} document(s) in the index")

    for doc in docs:
        with st.expander(f"📄 {doc['filename']}", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Type:** `{doc['file_type'].upper()}`")
            c2.markdown(f"**Size:** {format_file_size(doc['file_size'])}")
            c3.markdown(f"**Chunks:** {doc['num_chunks']}")
            st.caption(f"ID: `{doc['doc_id']}`")
            st.caption(f"Uploaded: {doc['upload_timestamp'][:19].replace('T', ' ')} UTC")

            if st.button("🗑️ Delete", key=f"del_{doc['doc_id']}"):
                result = api_delete(f"/documents/{doc['doc_id']}")
                if result:
                    st.success(f"Deleted '{doc['filename']}'")
                    st.rerun()
