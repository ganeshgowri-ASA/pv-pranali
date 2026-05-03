"""One function per pipeline node. Stub implementations until MCP servers are live."""
from __future__ import annotations

from typing import Any, Dict

from graph.state import PipelineState


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _stub_mcp(tool: str, **kwargs) -> Dict[str, Any]:
    """Placeholder for an MCP tool call."""
    return {"tool": tool, "status": "stub", **kwargs}


def _check_gate_approval(proposal_id: str, gate: str) -> bool:
    """Stub: checks Supabase `gates` table for status='approved'. Always False until wired."""
    return False


def _gate(state: PipelineState, gate_id: str, label: str) -> dict:
    """
    Generic gate logic. Returns awaiting_human=True when not yet approved so the
    graph routes to END. The tmux agent polls Supabase, sets status='approved', then
    re-invokes the graph with the same thread_id — on re-invocation the gate clears.
    """
    approved = _check_gate_approval(state.get("proposal_id", ""), gate_id)
    if not approved:
        return {
            "awaiting_human": True,
            "gate_name": f"{gate_id}:{label}",
            "current_node": gate_id,
        }
    return {
        "awaiting_human": False,
        "gate_name": None,
        "current_node": gate_id,
        "completed_nodes": [gate_id],
    }


# ---------------------------------------------------------------------------
# Stage nodes
# ---------------------------------------------------------------------------

def research(state: PipelineState) -> dict:
    data = _stub_mcp("antaryami.rag_query", intent=state.get("intent", ""))
    return {
        "research_data": data,
        "current_node": "research",
        "completed_nodes": ["research"],
    }


def standards(state: PipelineState) -> dict:
    data = _stub_mcp("suryaprajna.iec_lookup", intent=state.get("intent", ""))
    return {
        "standards_data": data,
        "current_node": "standards",
        "completed_nodes": ["standards"],
    }


def components(state: PipelineState) -> dict:
    bom = [_stub_mcp("mouser.search", intent=state.get("intent", ""))]
    return {
        "bom": bom,
        "current_node": "components",
        "completed_nodes": ["components"],
    }


def cad(state: PipelineState) -> dict:
    data = _stub_mcp("shilpasutra.cad_generate", bom=state.get("bom", []))
    return {
        "cad_artifacts": data,
        "current_node": "cad",
        "completed_nodes": ["cad"],
    }


def ecad(state: PipelineState) -> dict:
    data = _stub_mcp("vidyut.schematic", bom=state.get("bom", []))
    return {
        "ecad_artifacts": data,
        "current_node": "ecad",
        "completed_nodes": ["ecad"],
    }


def pcb(state: PipelineState) -> dict:
    data = _stub_mcp("vidyut.layout", ecad=state.get("ecad_artifacts", {}))
    return {
        "pcb_artifacts": data,
        "current_node": "pcb",
        "completed_nodes": ["pcb"],
    }


def bom_impact(state: PipelineState) -> dict:
    data = _stub_mcp("photoniq.bom_impact", bom=state.get("bom", []))
    return {
        "bom_impact_data": data,
        "current_node": "bom_impact",
        "completed_nodes": ["bom_impact"],
    }


def risk_swot(state: PipelineState) -> dict:
    data = _stub_mcp("suryaprajna.fmea", bom=state.get("bom", []))
    return {
        "risk_swot_data": data,
        "current_node": "risk_swot",
        "completed_nodes": ["risk_swot"],
    }


def rfq_draft(state: PipelineState) -> dict:
    drafts = [_stub_mcp("skyvern.fill_contact_form", bom=state.get("bom", []))]
    return {
        "rfq_drafts": drafts,
        "current_node": "rfq_draft",
        "completed_nodes": ["rfq_draft"],
    }


def proposal(state: PipelineState) -> dict:
    data = _stub_mcp(
        "vidyalaya.docx",
        research=state.get("research_data", {}),
        bom=state.get("bom", []),
    )
    return {
        "proposal_doc": data,
        "current_node": "proposal",
        "completed_nodes": ["proposal"],
    }


def pitch(state: PipelineState) -> dict:
    data = _stub_mcp("vidyalaya.pptx", proposal=state.get("proposal_doc", {}))
    return {
        "pitch_doc": data,
        "current_node": "pitch",
        "completed_nodes": ["pitch"],
    }


def landing(state: PipelineState) -> dict:
    data = _stub_mcp("vercel.deploy", pitch=state.get("pitch_doc", {}))
    return {
        "landing_url": data.get("url", "https://stub.vercel.app"),
        "current_node": "landing",
        "completed_nodes": ["landing"],
    }


def linkedin(state: PipelineState) -> dict:
    draft = _stub_mcp("unipile.draft", landing_url=state.get("landing_url", ""))
    return {
        "linkedin_draft": str(draft),
        "current_node": "linkedin",
        "completed_nodes": ["linkedin"],
    }


# ---------------------------------------------------------------------------
# Gate nodes  (HITL — pause until human approves in Supabase)
# ---------------------------------------------------------------------------

def gate1(state: PipelineState) -> dict:
    """Gate 1 — BoM Freeze: approve component list before engineering begins."""
    return _gate(state, "gate1", "bom_freeze")


def gate2(state: PipelineState) -> dict:
    """Gate 2 — PCB DRC pass: approve PCB design before cost-impact analysis."""
    return _gate(state, "gate2", "pcb_drc")


def gate3(state: PipelineState) -> dict:
    """Gate 3 — RFQ Send: approve supplier RFQ drafts before sending."""
    return _gate(state, "gate3", "rfq_send")


def gate4(state: PipelineState) -> dict:
    """Gate 4 — Public Post: approve landing page and LinkedIn draft."""
    return _gate(state, "gate4", "public_post")


def gate5(state: PipelineState) -> dict:
    """Gate 5 — Customer Send: final approval before delivering proposal."""
    return _gate(state, "gate5", "customer_send")
