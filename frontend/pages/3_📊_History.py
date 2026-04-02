"""Query History page."""

import streamlit as st

from frontend.config import APP_ICON, APP_TITLE, PAGE_SIZE
from frontend.components.sidebar import render_sidebar
from frontend.components.utils import api_delete, api_get, format_ms, init_session_state

st.set_page_config(
    page_title=f"{APP_TITLE} – History",
    page_icon=APP_ICON,
    layout="wide",
)

render_sidebar()
init_session_state({"history_page": 1})

st.title("📊 Query History")
st.caption("Review all past questions and answers.")

# ── Controls ──────────────────────────────────────────────────────────────────

col_refresh, col_clear = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Refresh"):
        st.rerun()
with col_clear:
    if st.button("🗑️ Clear All History"):
        result = api_delete("/history")
        if result:
            st.success(f"Cleared {result.get('deleted', 0)} entries")
            st.session_state.history_page = 1
            st.rerun()

# ── Fetch history ─────────────────────────────────────────────────────────────

page = st.session_state.history_page
data = api_get("/history", params={"page": page, "page_size": PAGE_SIZE})

if data is None:
    st.error("Could not reach the backend.")
elif data.get("total", 0) == 0:
    st.info("No queries yet. Go to the **Analyze** page to ask your first question!")
else:
    total = data["total"]
    entries = data["entries"]
    total_pages = max(1, -(-total // PAGE_SIZE))  # ceiling division

    st.caption(f"Showing {len(entries)} of {total} queries  ·  Page {page}/{total_pages}")

    # Entries
    for entry in entries:
        ts = entry["timestamp"][:19].replace("T", " ")
        with st.expander(f"🕐 {ts} UTC  ·  {entry['question'][:80]}…", expanded=False):
            st.markdown(f"**Question:** {entry['question']}")
            st.markdown("**Answer:**")
            st.markdown(entry["answer"])
            c1, c2, c3 = st.columns(3)
            c1.caption(f"⏱️ {format_ms(entry['processing_time_ms'])}")
            c2.caption(f"📎 {entry['num_sources']} source(s)")
            c3.caption(f"ID: `{entry['query_id'][:8]}…`")

    # Pagination
    st.divider()
    prev_col, _, next_col = st.columns([1, 6, 1])
    with prev_col:
        if st.button("◀ Prev", disabled=(page <= 1)):
            st.session_state.history_page -= 1
            st.rerun()
    with next_col:
        if st.button("Next ▶", disabled=(page >= total_pages)):
            st.session_state.history_page += 1
            st.rerun()
