"""Reusable Kanban column component for the pv-pranali pipeline console."""
from __future__ import annotations

from typing import Any

import streamlit as st

# 18 pipeline stages (gates are embedded as stage entries)
PIPELINE_STAGES: list[dict[str, Any]] = [
    {"id": "intent",               "label": "Intent",                 "gate": None},
    {"id": "research",             "label": "Research",               "gate": None},
    {"id": "standards_lookup",     "label": "Standards Lookup",       "gate": None},
    {"id": "component_select",     "label": "Component Select",       "gate": None},
    {"id": "bom_freeze",           "label": "BoM Freeze",             "gate": 1},
    {"id": "cad",                  "label": "CAD",                    "gate": None},
    {"id": "ecad",                 "label": "eCAD",                   "gate": None},
    {"id": "pcb",                  "label": "PCB",                    "gate": None},
    {"id": "drc_pass",             "label": "DRC Pass",               "gate": 2},
    {"id": "bom_impact",           "label": "BoM Impact",             "gate": None},
    {"id": "risk_swot",            "label": "Risk / SWOT",            "gate": None},
    {"id": "supplier_rfq_draft",   "label": "Supplier RFQ Draft",     "gate": None},
    {"id": "rfq_send",             "label": "RFQ Send",               "gate": 3},
    {"id": "proposal_assemble",    "label": "Proposal Assemble",      "gate": None},
    {"id": "pitch_deck",           "label": "Pitch Deck",             "gate": None},
    {"id": "public_post",          "label": "Public Post",            "gate": 4},
    {"id": "landing_linkedin",     "label": "Landing + LinkedIn",     "gate": None},
    {"id": "customer_send",        "label": "Customer Send",          "gate": 5},
]

_STATUS_COLOUR = {
    "done":     "#22c55e",
    "active":   "#3b82f6",
    "pending":  "#f59e0b",
    "rejected": "#ef4444",
    "idle":     "#6b7280",
}


def _stage_status(stage_id: str, states: dict[str, str]) -> str:
    return states.get(stage_id, "idle")


def render_kanban(
    run_id: str | None,
    stage_states: dict[str, str],
    on_approve: Any = None,
    on_reject: Any = None,
) -> None:
    """Render the full Kanban board.

    Args:
        run_id:       Active pipeline run UUID (or None).
        stage_states: Mapping of stage_id → status string.
        on_approve:   Callable(run_id, gate_num) called on Approve click.
        on_reject:    Callable(run_id, gate_num, reason) called on Reject click.
    """
    st.markdown("### Pipeline Kanban")
    if not run_id:
        st.info("No active run. Select or start a run to view the pipeline.")
        return

    cols_per_row = 6
    rows = [
        PIPELINE_STAGES[i : i + cols_per_row]
        for i in range(0, len(PIPELINE_STAGES), cols_per_row)
    ]

    for row in rows:
        cols = st.columns(len(row))
        for col, stage in zip(cols, row):
            status = _stage_status(stage["id"], stage_states)
            colour = _STATUS_COLOUR.get(status, _STATUS_COLOUR["idle"])
            gate_badge = f" 🔒 Gate {stage['gate']}" if stage["gate"] else ""
            col.markdown(
                f"""
                <div style="
                    background:{colour}22;
                    border-left:4px solid {colour};
                    border-radius:6px;
                    padding:8px 10px;
                    margin-bottom:4px;
                    font-size:0.8rem;
                ">
                    <b>{stage['label']}</b>{gate_badge}<br/>
                    <span style="color:{colour};font-size:0.75rem;">{status.upper()}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Gate action panel
    st.markdown("---")
    st.markdown("#### Gate Approvals")
    gate_stages = [s for s in PIPELINE_STAGES if s["gate"]]
    gate_cols = st.columns(len(gate_stages))
    for col, stage in zip(gate_cols, gate_stages):
        status = _stage_status(stage["id"], stage_states)
        col.markdown(f"**Gate {stage['gate']}**  
{stage['label']}")
        if status == "pending":
            if col.button("✅ Approve", key=f"approve_{stage['gate']}"):
                if on_approve:
                    on_approve(run_id, stage["gate"])
            reason = col.text_input("Reason", key=f"reason_{stage['gate']}", label_visibility="collapsed", placeholder="Reject reason…")
            if col.button("❌ Reject", key=f"reject_{stage['gate']}"):
                if on_reject:
                    on_reject(run_id, stage["gate"], reason)
        else:
            col.caption(f"Status: {status}")
