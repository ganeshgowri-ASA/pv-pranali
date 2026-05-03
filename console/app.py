"""pv-pranali Streamlit pipeline console.

Run with:
    streamlit run console/app.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import streamlit as st

# Ensure console/ is on the path when invoked as `streamlit run console/app.py`
sys.path.insert(0, str(Path(__file__).parent.parent))

from console.components.kanban import render_kanban, PIPELINE_STAGES  # noqa: E402
from console.components.token_meter import render_token_meter  # noqa: E402

st.set_page_config(
    page_title="PV-Pranali Console",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Supabase helpers (graceful degradation when not configured)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _supabase_client():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY", "")
    if not (url and key):
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None


def _load_runs(db) -> list[dict]:
    if not db:
        return []
    try:
        return db.table("proposals").select("id, intent, status, created_at").order("created_at", desc=True).limit(20).execute().data or []
    except Exception:
        return []


def _load_stage_states(db, run_id: str) -> dict[str, str]:
    """Return stage_id → status for the given run."""
    if not db or not run_id:
        return {}
    try:
        rows = (
            db.table("pipeline_stages")
            .select("stage_id, status")
            .eq("run_id", run_id)
            .execute()
            .data
        ) or []
        return {r["stage_id"]: r["status"] for r in rows}
    except Exception:
        return {}


def _load_gate_states(db, run_id: str) -> dict[str, str]:
    """Return gate_name → status from gate_events table."""
    if not db or not run_id:
        return {}
    try:
        rows = (
            db.table("gate_events")
            .select("gate_name, status")
            .eq("run_id", run_id)
            .execute()
            .data
        ) or []
        return {r["gate_name"]: r["status"] for r in rows}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Gate actions — delegate to console/gate.py via subprocess
# ---------------------------------------------------------------------------

_GATE_STAGE_MAP = {
    1: "bom_freeze",
    2: "drc_pass",
    3: "rfq_send",
    4: "public_post",
    5: "customer_send",
}


def _call_gate(action: str, run_id: str, reason: str = "") -> bool:
    gate_py = Path(__file__).parent / "gate.py"
    cmd = [sys.executable, str(gate_py), action, run_id]
    if action == "reject" and reason:
        cmd += ["--reason", reason]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            st.toast(f"Gate {action}d for run {run_id[:8]}…", icon="✅" if action == "approve" else "❌")
            return True
        else:
            st.error(f"gate.py error: {result.stderr.strip()}")
            return False
    except Exception as exc:
        st.error(f"Failed to call gate.py: {exc}")
        return False


def on_approve(run_id: str, gate_num: int) -> None:
    if _call_gate("approve", run_id):
        st.rerun()


def on_reject(run_id: str, gate_num: int, reason: str) -> None:
    if _call_gate("reject", run_id, reason):
        st.rerun()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("⚡ PV-Pranali")
st.sidebar.caption("Multi-agent proposal pipeline console")

db = _supabase_client()
if not db:
    st.sidebar.warning("Supabase not configured — running in demo mode.")

runs = _load_runs(db)
run_options = {f"{r['id'][:8]}… | {r.get('intent','')[:30]}": r["id"] for r in runs}
run_options["— demo run —"] = "demo"

selected_label = st.sidebar.selectbox("Active Run", list(run_options.keys()))
run_id: str | None = run_options[selected_label]
if run_id == "demo":
    run_id = None  # triggers demo stage states

# Token meter
session_token_id = run_id or "demo"
render_token_meter(session_token_id)

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.title("Pipeline Console")

if run_id:
    stage_states = _load_stage_states(db, run_id)
    gate_states = _load_gate_states(db, run_id)
    # Merge gate status into stage_states
    for stage in PIPELINE_STAGES:
        if stage["gate"] is not None:
            gate_stage_id = stage["id"]
            # Map from gate_events gate_name conventions
            for key in (gate_stage_id, f"gate_{stage['gate']}"):
                if key in gate_states:
                    stage_states.setdefault(gate_stage_id, gate_states[key])
else:
    # Demo: show a sample state
    stage_states = {
        "intent":             "done",
        "research":           "done",
        "standards_lookup":   "done",
        "component_select":   "done",
        "bom_freeze":         "pending",
        "cad":                "idle",
        "ecad":               "idle",
        "pcb":                "idle",
        "drc_pass":           "idle",
        "bom_impact":         "idle",
        "risk_swot":          "idle",
        "supplier_rfq_draft": "idle",
        "rfq_send":           "idle",
        "proposal_assemble":  "idle",
        "pitch_deck":         "idle",
        "public_post":        "idle",
        "landing_linkedin":   "idle",
        "customer_send":      "idle",
    }
    st.info("Demo mode: Supabase not connected. Stage states are illustrative.")

render_kanban(
    run_id=run_id or "demo",
    stage_states=stage_states,
    on_approve=on_approve,
    on_reject=on_reject,
)

# ---------------------------------------------------------------------------
# Run details footer
# ---------------------------------------------------------------------------
if run_id and runs:
    run_meta = next((r for r in runs if r["id"] == run_id), None)
    if run_meta:
        with st.expander("Run metadata"):
            st.json(run_meta)
