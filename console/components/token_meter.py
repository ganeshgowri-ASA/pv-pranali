"""Token usage bar-chart component.

Reads token usage from Langfuse (via HTTP) or falls back to a local SQLite
counter at /tmp/pp_tokens.db.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

import streamlit as st

_DB_PATH = Path(os.environ.get("PP_TOKEN_DB", "/tmp/pp_tokens.db"))
SESSION_CAP = int(os.environ.get("MIMO_SESSION_TOKEN_CAP", 8_000_000))


def _init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS token_usage (
            session_id TEXT PRIMARY KEY,
            used       INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    return conn


def _read_sqlite(session_id: str) -> int:
    conn = _init_db()
    row = conn.execute(
        "SELECT used FROM token_usage WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def _read_langfuse(session_id: str) -> Optional[int]:
    """Query Langfuse public API for token usage on a session."""
    try:
        import requests  # type: ignore

        base = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
        pk = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        sk = os.environ.get("LANGFUSE_SECRET_KEY", "")
        if not (pk and sk):
            return None
        resp = requests.get(
            f"{base}/api/public/sessions/{session_id}",
            auth=(pk, sk),
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        usage = data.get("totalTokens") or data.get("usage", {}).get("totalTokens")
        return int(usage) if usage is not None else None
    except Exception:
        return None


def get_token_usage(session_id: str) -> tuple[int, int]:
    """Return (used, cap) for the given session."""
    used = _read_langfuse(session_id)
    if used is None:
        used = _read_sqlite(session_id)
    return used, SESSION_CAP


def render_token_meter(session_id: str) -> None:
    """Render a token-usage progress bar + bar chart in the sidebar."""
    st.sidebar.markdown("### Token Usage")
    if not session_id:
        st.sidebar.caption("No active session.")
        return

    used, cap = get_token_usage(session_id)
    pct = min(used / cap, 1.0) if cap else 0.0
    remaining = max(cap - used, 0)

    colour = "normal" if pct < 0.75 else ("off" if pct < 0.90 else "inverse")
    st.sidebar.progress(pct, text=f"{used:,} / {cap:,} tokens used")

    if pct >= 0.90:
        st.sidebar.warning("⚠️ Token budget > 90% consumed!")

    import pandas as pd
    import altair as alt

    chart_data = pd.DataFrame(
        {"Category": ["Used", "Remaining"], "Tokens": [used, remaining]}
    )
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("Category:N", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Tokens:Q"),
            color=alt.Color(
                "Category:N",
                scale=alt.Scale(
                    domain=["Used", "Remaining"],
                    range=["#ef4444", "#22c55e"],
                ),
            ),
            tooltip=["Category", "Tokens"],
        )
        .properties(height=180)
    )
    st.sidebar.altair_chart(chart, use_container_width=True)
    st.sidebar.caption(f"Cap: {cap:,} | Remaining: {remaining:,}")
