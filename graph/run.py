#!/usr/bin/env python3
"""Entry point for the PV-Pranali LangGraph pipeline."""
from __future__ import annotations

import argparse
import sys
import uuid
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from graph.nodes import (
    bom_impact,
    cad,
    components,
    ecad,
    gate1,
    gate2,
    gate3,
    gate4,
    gate5,
    landing,
    linkedin,
    pcb,
    pitch,
    proposal,
    research,
    rfq_draft,
    risk_swot,
    standards,
)
from graph.state import PipelineState

# Ordered list of all 18 pipeline nodes
NODE_SEQUENCE = [
    "research", "standards", "components", "gate1",
    "cad", "ecad", "pcb", "gate2",
    "bom_impact", "risk_swot", "rfq_draft", "gate3",
    "proposal", "pitch", "gate4",
    "landing", "linkedin", "gate5",
]

NODE_FNS = {
    "research": research,
    "standards": standards,
    "components": components,
    "gate1": gate1,
    "cad": cad,
    "ecad": ecad,
    "pcb": pcb,
    "gate2": gate2,
    "bom_impact": bom_impact,
    "risk_swot": risk_swot,
    "rfq_draft": rfq_draft,
    "gate3": gate3,
    "proposal": proposal,
    "pitch": pitch,
    "gate4": gate4,
    "landing": landing,
    "linkedin": linkedin,
    "gate5": gate5,
}

# gate → next stage when approved (END for the final gate)
_GATE_NEXT = {
    "gate1": "cad",
    "gate2": "bom_impact",
    "gate3": "proposal",
    "gate4": "landing",
    "gate5": END,
}


def build_graph(checkpointer=None):
    """Build and compile the PV-Pranali LangGraph state machine."""
    g = StateGraph(PipelineState)

    for name, fn in NODE_FNS.items():
        g.add_node(name, fn)

    g.set_entry_point("research")

    # Sequential (non-gate) edges
    for src, dst in [
        ("research", "standards"),
        ("standards", "components"),
        ("components", "gate1"),
        ("cad", "ecad"),
        ("ecad", "pcb"),
        ("pcb", "gate2"),
        ("bom_impact", "risk_swot"),
        ("risk_swot", "rfq_draft"),
        ("rfq_draft", "gate3"),
        ("proposal", "pitch"),
        ("pitch", "gate4"),
        ("landing", "linkedin"),
        ("linkedin", "gate5"),
    ]:
        g.add_edge(src, dst)

    # Conditional edges from gate nodes:
    #   awaiting_human=True  → END   (tmux will re-invoke after Supabase approval)
    #   awaiting_human=False → next stage
    for gate, nxt in _GATE_NEXT.items():
        destinations = {END: END} if nxt == END else {END: END, nxt: nxt}
        g.add_conditional_edges(
            gate,
            lambda s, _nxt=nxt: END if s.get("awaiting_human") else _nxt,
            destinations,
        )

    return g.compile(checkpointer=checkpointer or MemorySaver())


def _empty_state(intent: str, proposal_id: str, run_id: str) -> PipelineState:
    return {
        "intent": intent,
        "proposal_id": proposal_id,
        "run_id": run_id,
        "current_node": "research",
        "awaiting_human": False,
        "gate_name": None,
        "completed_nodes": [],
        "tokens_used": 0,
        "error": None,
        "research_data": {},
        "standards_data": {},
        "bom": [],
        "cad_artifacts": {},
        "ecad_artifacts": {},
        "pcb_artifacts": {},
        "bom_impact_data": {},
        "risk_swot_data": {},
        "rfq_drafts": [],
        "proposal_doc": {},
        "pitch_doc": {},
        "landing_url": None,
        "linkedin_draft": None,
    }


def run(
    intent: str,
    proposal_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    checkpointer=None,
) -> PipelineState:
    """Invoke or resume the pipeline for a given thread."""
    graph = build_graph(checkpointer)
    tid = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    pid = proposal_id or str(uuid.uuid4())
    state = _empty_state(intent=intent, proposal_id=pid, run_id=str(uuid.uuid4()))
    return graph.invoke(state, config=config)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m graph.run",
        description="PV-Pranali LangGraph pipeline runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # start a fresh run
  python -m graph.run --intent "Build IEC 61215 Sun Simulator Class AAA"

  # resume an existing thread after gate approval in Supabase
  python -m graph.run --intent "Build EL Tester" --thread-id <uuid>

  # list all pipeline nodes
  python -m graph.run --list-nodes
        """,
    )
    parser.add_argument(
        "--intent",
        default="Build EL Tester",
        help="One-line product intent (default: 'Build EL Tester')",
    )
    parser.add_argument(
        "--proposal-id",
        default=None,
        help="Existing proposal UUID (optional; generated if omitted)",
    )
    parser.add_argument(
        "--resume-from",
        default=None,
        choices=NODE_SEQUENCE,
        metavar="NODE",
        help=(
            "Pipeline node to resume from. Requires --thread-id for checkpointer-based "
            f"resume. Choices: {', '.join(NODE_SEQUENCE)}"
        ),
    )
    parser.add_argument(
        "--thread-id",
        default=None,
        help="LangGraph thread ID to load a saved checkpoint (optional)",
    )
    parser.add_argument(
        "--list-nodes",
        action="store_true",
        help="Print all 18 pipeline nodes and exit",
    )
    args = parser.parse_args()

    if args.list_nodes:
        print("Pipeline nodes:", ", ".join(NODE_SEQUENCE))
        sys.exit(0)

    final = run(
        intent=args.intent,
        proposal_id=args.proposal_id,
        thread_id=args.thread_id,
    )

    if final.get("awaiting_human"):
        tid = args.thread_id or "<thread-id printed above>"
        print(f"Paused at gate: {final.get('gate_name')}")
        print(f"Approve in Supabase, then re-run with --thread-id {tid}")
    else:
        print("Pipeline complete. Nodes visited:", final.get("completed_nodes"))


if __name__ == "__main__":
    main()
