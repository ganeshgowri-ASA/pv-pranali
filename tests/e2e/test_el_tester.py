"""End-to-end tests for the EL Tester pipeline.

Run with:
    GATE_AUTO_APPROVE=true pytest tests/e2e/test_el_tester.py
"""
from __future__ import annotations

import os
import uuid

import pytest

import graph.nodes as nodes_module
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
from graph.run import NODE_SEQUENCE, build_graph
from graph.state import PipelineState

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EL_INTENT = "Build EL Tester for IEC 60904-3 compliance"

# node name -> MCP tool it must call exactly once
NODE_MCP_TOOLS = {
    "research":   "antaryami.rag_query",
    "standards":  "suryaprajna.iec_lookup",
    "components": "mouser.search",
    "cad":        "shilpasutra.cad_generate",
    "ecad":       "vidyut.schematic",
    "pcb":        "vidyut.layout",
    "bom_impact": "photoniq.bom_impact",
    "risk_swot":  "suryaprajna.fmea",
    "rfq_draft":  "skyvern.fill_contact_form",
    "proposal":   "vidyalaya.docx",
    "pitch":      "vidyalaya.pptx",
    "landing":    "vercel.deploy",
    "linkedin":   "unipile.draft",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(**overrides) -> PipelineState:
    base: PipelineState = {
        "intent": EL_INTENT,
        "proposal_id": "el-test-proposal-001",
        "run_id": "el-test-run-001",
        "current_node": "",
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
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auto_approve(monkeypatch):
    """Patch _check_gate_approval to always return True."""
    monkeypatch.setattr(nodes_module, "_check_gate_approval", lambda *_: True)


@pytest.fixture
def reject_all(monkeypatch):
    """Patch _check_gate_approval to always return False."""
    monkeypatch.setattr(nodes_module, "_check_gate_approval", lambda *_: False)


@pytest.fixture
def mcp_tracker(monkeypatch):
    """Patch _stub_mcp to record every call and return a predictable dict."""
    calls: list = []

    def _tracked(tool: str, **kwargs) -> dict:
        calls.append({"tool": tool, **kwargs})
        return {"tool": tool, "status": "ok", "url": "https://stub.vercel.app"}

    monkeypatch.setattr(nodes_module, "_stub_mcp", _tracked)
    return calls


# ---------------------------------------------------------------------------
# TestELTesterPipeline — full pipeline runs
# ---------------------------------------------------------------------------

class TestELTesterPipeline:
    """Full end-to-end runs of the EL Tester pipeline."""

    def test_full_pipeline_all_gates_approved(self, auto_approve, mcp_tracker):
        """With all gates approved, all 18 nodes run to completion."""
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = graph.invoke(make_state(), config=config)

        assert result["awaiting_human"] is False
        assert result["error"] is None
        completed = result["completed_nodes"]
        for node in NODE_SEQUENCE:
            assert node in completed, f"Stage '{node}' not in completed_nodes"
        assert len(mcp_tracker) >= 13

    def test_pipeline_halts_at_gate1_when_not_approved(self, reject_all):
        """Without approval the pipeline pauses at gate1."""
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = graph.invoke(make_state(), config=config)

        assert result["awaiting_human"] is True
        assert "gate1" in result["gate_name"]
        for pre in ("research", "standards", "components"):
            assert pre in result["completed_nodes"]
        for post in ("cad", "ecad", "pcb"):
            assert post not in result["completed_nodes"]

    def test_pipeline_stage_outputs_in_full_run(self, auto_approve, mcp_tracker):
        """Every stage output field is populated in the final state."""
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = graph.invoke(make_state(), config=config)

        # Stage 1: research
        assert isinstance(result["research_data"], dict) and result["research_data"]
        # Stage 2: standards
        assert isinstance(result["standards_data"], dict) and result["standards_data"]
        # Stage 3: components
        assert isinstance(result["bom"], list) and len(result["bom"]) > 0
        # Stage 5: cad
        assert isinstance(result["cad_artifacts"], dict) and result["cad_artifacts"]
        # Stage 6: ecad
        assert isinstance(result["ecad_artifacts"], dict) and result["ecad_artifacts"]
        # Stage 7: pcb
        assert isinstance(result["pcb_artifacts"], dict) and result["pcb_artifacts"]
        # Stage 9: bom_impact
        assert isinstance(result["bom_impact_data"], dict) and result["bom_impact_data"]
        # Stage 10: risk_swot
        assert isinstance(result["risk_swot_data"], dict) and result["risk_swot_data"]
        # Stage 11: rfq_draft
        assert isinstance(result["rfq_drafts"], list) and len(result["rfq_drafts"]) > 0
        # Stage 13: proposal
        assert isinstance(result["proposal_doc"], dict) and result["proposal_doc"]
        # Stage 14: pitch
        assert isinstance(result["pitch_doc"], dict) and result["pitch_doc"]
        # Stage 16: landing
        assert result["landing_url"] is not None
        # Stage 17: linkedin
        assert result["linkedin_draft"] is not None

    def test_proposal_id_preserved(self, auto_approve):
        pid = "el-tester-proposal-xyz"
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = graph.invoke(make_state(proposal_id=pid), config=config)
        assert result["proposal_id"] == pid

    def test_intent_preserved(self, auto_approve):
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = graph.invoke(make_state(intent=EL_INTENT), config=config)
        assert result["intent"] == EL_INTENT

    def test_node_execution_respects_sequence(self, auto_approve):
        """Nodes in completed_nodes appear in valid pipeline sequence order."""
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = graph.invoke(make_state(), config=config)
        completed = result["completed_nodes"]
        # Verify that each node in sequence appears before any later-sequence node
        seq_positions = [
            (NODE_SEQUENCE.index(n), completed.index(n))
            for n in NODE_SEQUENCE
            if n in completed
        ]
        for i in range(len(seq_positions) - 1):
            assert seq_positions[i][1] <= seq_positions[i + 1][1]


# ---------------------------------------------------------------------------
# TestStageNodes — one test per stage (18 stages)
# ---------------------------------------------------------------------------

class TestStageNodes:
    """Each of the 18 pipeline stages has at least one assertion."""

    # Stage 1
    def test_research(self, mcp_tracker):
        result = research(make_state())
        assert "research_data" in result
        assert result["current_node"] == "research"
        assert "research" in result["completed_nodes"]
        assert any(c["tool"] == "antaryami.rag_query" for c in mcp_tracker)

    # Stage 2
    def test_standards(self, mcp_tracker):
        result = standards(make_state())
        assert "standards_data" in result
        assert result["current_node"] == "standards"
        assert "standards" in result["completed_nodes"]
        assert any(c["tool"] == "suryaprajna.iec_lookup" for c in mcp_tracker)

    # Stage 3
    def test_components(self, mcp_tracker):
        result = components(make_state())
        assert "bom" in result
        assert isinstance(result["bom"], list) and len(result["bom"]) > 0
        assert result["current_node"] == "components"
        assert any(c["tool"] == "mouser.search" for c in mcp_tracker)

    # Stage 4: gate1 — reject
    def test_gate1_reject(self, reject_all):
        result = gate1(make_state())
        assert result["awaiting_human"] is True
        assert "gate1" in result["gate_name"]
        assert "bom_freeze" in result["gate_name"]

    # Stage 4: gate1 — approve
    def test_gate1_approve(self, auto_approve):
        result = gate1(make_state())
        assert result["awaiting_human"] is False
        assert "gate1" in result["completed_nodes"]

    # Stage 5
    def test_cad(self, mcp_tracker):
        result = cad(make_state(bom=[{"part": "LED-IR-940nm", "qty": 10}]))
        assert "cad_artifacts" in result
        assert result["current_node"] == "cad"
        assert "cad" in result["completed_nodes"]
        assert any(c["tool"] == "shilpasutra.cad_generate" for c in mcp_tracker)

    # Stage 6
    def test_ecad(self, mcp_tracker):
        result = ecad(make_state(bom=[{"part": "LED-IR-940nm", "qty": 10}]))
        assert "ecad_artifacts" in result
        assert result["current_node"] == "ecad"
        assert "ecad" in result["completed_nodes"]
        assert any(c["tool"] == "vidyut.schematic" for c in mcp_tracker)

    # Stage 7
    def test_pcb(self, mcp_tracker):
        result = pcb(make_state(ecad_artifacts={"netlist": "stub"}))
        assert "pcb_artifacts" in result
        assert result["current_node"] == "pcb"
        assert "pcb" in result["completed_nodes"]
        assert any(c["tool"] == "vidyut.layout" for c in mcp_tracker)

    # Stage 8: gate2 — reject
    def test_gate2_reject(self, reject_all):
        result = gate2(make_state())
        assert result["awaiting_human"] is True
        assert "gate2" in result["gate_name"]
        assert "pcb_drc" in result["gate_name"]

    # Stage 8: gate2 — approve
    def test_gate2_approve(self, auto_approve):
        result = gate2(make_state())
        assert result["awaiting_human"] is False
        assert "gate2" in result["completed_nodes"]

    # Stage 9
    def test_bom_impact(self, mcp_tracker):
        result = bom_impact(make_state(bom=[{"part": "LED-IR-940nm"}]))
        assert "bom_impact_data" in result
        assert result["current_node"] == "bom_impact"
        assert "bom_impact" in result["completed_nodes"]
        assert any(c["tool"] == "photoniq.bom_impact" for c in mcp_tracker)

    # Stage 10
    def test_risk_swot(self, mcp_tracker):
        result = risk_swot(make_state(bom=[{"part": "LED-IR-940nm"}]))
        assert "risk_swot_data" in result
        assert result["current_node"] == "risk_swot"
        assert "risk_swot" in result["completed_nodes"]
        assert any(c["tool"] == "suryaprajna.fmea" for c in mcp_tracker)

    # Stage 11
    def test_rfq_draft(self, mcp_tracker):
        result = rfq_draft(make_state(bom=[{"part": "LED-IR-940nm"}]))
        assert "rfq_drafts" in result
        assert isinstance(result["rfq_drafts"], list) and len(result["rfq_drafts"]) > 0
        assert result["current_node"] == "rfq_draft"
        assert any(c["tool"] == "skyvern.fill_contact_form" for c in mcp_tracker)

    # Stage 12: gate3 — reject
    def test_gate3_reject(self, reject_all):
        result = gate3(make_state())
        assert result["awaiting_human"] is True
        assert "gate3" in result["gate_name"]
        assert "rfq_send" in result["gate_name"]

    # Stage 12: gate3 — approve
    def test_gate3_approve(self, auto_approve):
        result = gate3(make_state())
        assert result["awaiting_human"] is False
        assert "gate3" in result["completed_nodes"]

    # Stage 13
    def test_proposal(self, mcp_tracker):
        result = proposal(make_state(
            research_data={"findings": "stub"},
            bom=[{"part": "LED-IR-940nm"}],
        ))
        assert "proposal_doc" in result
        assert result["current_node"] == "proposal"
        assert "proposal" in result["completed_nodes"]
        assert any(c["tool"] == "vidyalaya.docx" for c in mcp_tracker)

    # Stage 14
    def test_pitch(self, mcp_tracker):
        result = pitch(make_state(proposal_doc={"content": "stub"}))
        assert "pitch_doc" in result
        assert result["current_node"] == "pitch"
        assert "pitch" in result["completed_nodes"]
        assert any(c["tool"] == "vidyalaya.pptx" for c in mcp_tracker)

    # Stage 15: gate4 — reject
    def test_gate4_reject(self, reject_all):
        result = gate4(make_state())
        assert result["awaiting_human"] is True
        assert "gate4" in result["gate_name"]
        assert "public_post" in result["gate_name"]

    # Stage 15: gate4 — approve
    def test_gate4_approve(self, auto_approve):
        result = gate4(make_state())
        assert result["awaiting_human"] is False
        assert "gate4" in result["completed_nodes"]

    # Stage 16
    def test_landing(self, mcp_tracker):
        result = landing(make_state(pitch_doc={"slides": "stub"}))
        assert "landing_url" in result
        assert result["landing_url"] is not None
        assert result["current_node"] == "landing"
        assert "landing" in result["completed_nodes"]
        assert any(c["tool"] == "vercel.deploy" for c in mcp_tracker)

    # Stage 17
    def test_linkedin(self, mcp_tracker):
        result = linkedin(make_state(landing_url="https://stub.vercel.app"))
        assert "linkedin_draft" in result
        assert result["linkedin_draft"] is not None
        assert result["current_node"] == "linkedin"
        assert "linkedin" in result["completed_nodes"]
        assert any(c["tool"] == "unipile.draft" for c in mcp_tracker)

    # Stage 18: gate5 — reject
    def test_gate5_reject(self, reject_all):
        result = gate5(make_state())
        assert result["awaiting_human"] is True
        assert "gate5" in result["gate_name"]
        assert "customer_send" in result["gate_name"]

    # Stage 18: gate5 — approve
    def test_gate5_approve(self, auto_approve):
        result = gate5(make_state())
        assert result["awaiting_human"] is False
        assert "gate5" in result["completed_nodes"]


# ---------------------------------------------------------------------------
# TestGateApproveRejectPaths — 5 gates × 2 paths = 10 parametrized cases
# ---------------------------------------------------------------------------

GATE_PARAMS = [
    (gate1, "gate1", "bom_freeze"),
    (gate2, "gate2", "pcb_drc"),
    (gate3, "gate3", "rfq_send"),
    (gate4, "gate4", "public_post"),
    (gate5, "gate5", "customer_send"),
]


class TestGateApproveRejectPaths:
    @pytest.mark.parametrize("gate_fn,gate_id,label", GATE_PARAMS)
    def test_gate_reject_path(self, gate_fn, gate_id, label, reject_all):
        result = gate_fn(make_state())
        assert result["awaiting_human"] is True
        assert gate_id in result["gate_name"]
        assert label in result["gate_name"]
        assert result["current_node"] == gate_id

    @pytest.mark.parametrize("gate_fn,gate_id,label", GATE_PARAMS)
    def test_gate_approve_path(self, gate_fn, gate_id, label, auto_approve):
        result = gate_fn(make_state())
        assert result["awaiting_human"] is False
        assert result["gate_name"] is None
        assert gate_id in result["completed_nodes"]
        assert result["current_node"] == gate_id


# ---------------------------------------------------------------------------
# TestMCPCallCounts — verify mock call counts
# ---------------------------------------------------------------------------

class TestMCPCallCounts:
    """MCP tool call counts verified via mcp_tracker fixture."""

    @pytest.mark.parametrize("node_name,expected_tool", list(NODE_MCP_TOOLS.items()))
    def test_stage_calls_mcp_tool_exactly_once(self, node_name, expected_tool, mcp_tracker):
        _node_fns = {
            "research": research, "standards": standards, "components": components,
            "cad": cad, "ecad": ecad, "pcb": pcb,
            "bom_impact": bom_impact, "risk_swot": risk_swot, "rfq_draft": rfq_draft,
            "proposal": proposal, "pitch": pitch, "landing": landing, "linkedin": linkedin,
        }
        _node_fns[node_name](make_state())
        tools_called = [c["tool"] for c in mcp_tracker]
        assert tools_called.count(expected_tool) == 1, (
            f"Stage '{node_name}' must call '{expected_tool}' exactly once. Got: {tools_called}"
        )

    def test_full_pipeline_calls_exactly_13_mcp_tools(self, auto_approve, mcp_tracker):
        """Full run triggers exactly 13 MCP calls (one per non-gate stage)."""
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        graph.invoke(make_state(), config=config)
        assert len(mcp_tracker) == 13, (
            f"Expected 13 MCP calls, got {len(mcp_tracker)}: "
            f"{[c['tool'] for c in mcp_tracker]}"
        )

    def test_all_mcp_tools_present_in_full_run(self, auto_approve, mcp_tracker):
        """Every expected MCP tool appears at least once in a full run."""
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        graph.invoke(make_state(), config=config)
        tools_called = {c["tool"] for c in mcp_tracker}
        for tool in NODE_MCP_TOOLS.values():
            assert tool in tools_called, f"MCP tool '{tool}' was never called"


# ---------------------------------------------------------------------------
# TestNodeInventory — structural checks
# ---------------------------------------------------------------------------

class TestNodeInventory:
    def test_node_sequence_has_18_entries(self):
        assert len(NODE_SEQUENCE) == 18

    def test_node_sequence_starts_with_research(self):
        assert NODE_SEQUENCE[0] == "research"

    def test_node_sequence_ends_with_gate5(self):
        assert NODE_SEQUENCE[-1] == "gate5"

    def test_all_5_gates_in_sequence(self):
        assert {"gate1", "gate2", "gate3", "gate4", "gate5"}.issubset(set(NODE_SEQUENCE))

    def test_gate_order_correct(self):
        seq = NODE_SEQUENCE
        assert seq.index("gate1") < seq.index("cad")
        assert seq.index("gate2") < seq.index("bom_impact")
        assert seq.index("gate3") < seq.index("proposal")
        assert seq.index("gate4") < seq.index("landing")
        assert seq.index("gate4") < seq.index("gate5")

    def test_graph_compiles(self):
        graph = build_graph()
        assert graph is not None


# ---------------------------------------------------------------------------
# TestGATEAutoApproveEnvVar — env-var-driven gate behaviour
# ---------------------------------------------------------------------------

class TestGATEAutoApproveEnvVar:
    """GATE_AUTO_APPROVE env var drives full pipeline completion."""

    def test_env_var_true_runs_full_pipeline(self, monkeypatch):
        monkeypatch.setenv("GATE_AUTO_APPROVE", "true")
        monkeypatch.setattr(
            nodes_module,
            "_check_gate_approval",
            lambda *_: os.environ.get("GATE_AUTO_APPROVE", "false").lower() == "true",
        )
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = graph.invoke(make_state(), config=config)
        assert result["awaiting_human"] is False
        for node in NODE_SEQUENCE:
            assert node in result["completed_nodes"]

    def test_env_var_false_halts_at_gate1(self, monkeypatch):
        monkeypatch.setenv("GATE_AUTO_APPROVE", "false")
        monkeypatch.setattr(
            nodes_module,
            "_check_gate_approval",
            lambda *_: os.environ.get("GATE_AUTO_APPROVE", "false").lower() == "true",
        )
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = graph.invoke(make_state(), config=config)
        assert result["awaiting_human"] is True
        assert "gate1" in result["gate_name"]
