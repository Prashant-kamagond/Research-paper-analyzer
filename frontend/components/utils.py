"""Utility helpers for the Streamlit frontend."""

import logging
from typing import Any, Optional

import httpx
import streamlit as st

from frontend.config import API_BASE_URL

logger = logging.getLogger(__name__)

_TIMEOUT = 60.0  # seconds


def api_get(path: str, params: Optional[dict] = None) -> Optional[dict]:
    """GET request to the backend.  Returns parsed JSON or *None* on error."""
    try:
        response = httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.debug("GET %s failed: %s", path, exc)
        return None


def api_post(path: str, json: Optional[dict] = None, files=None) -> Optional[dict]:
    """POST request to the backend.  Returns parsed JSON or *None* on error."""
    try:
        response = httpx.post(
            f"{API_BASE_URL}{path}",
            json=json,
            files=files,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("detail", str(exc))
        st.error(f"❌ API Error: {detail}")
        return None
    except Exception as exc:
        st.error(f"❌ Connection error: {exc}")
        return None


def api_delete(path: str) -> Optional[dict]:
    """DELETE request to the backend."""
    try:
        response = httpx.delete(f"{API_BASE_URL}{path}", timeout=_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"❌ Delete failed: {exc}")
        return None


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 ** 2):.1f} MB"


def format_ms(ms: float) -> str:
    """Human-readable duration."""
    if ms < 1000:
        return f"{ms:.0f} ms"
    return f"{ms / 1000:.1f} s"


def backend_is_online() -> bool:
    """Quick check whether the backend is reachable."""
    return api_get("/health") is not None


def init_session_state(defaults: dict) -> None:
    """Initialise session-state keys that do not yet exist."""
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
