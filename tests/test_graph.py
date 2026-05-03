"""Unit tests for the PV-Pranali LangGraph pipeline."""
from __future__ import annotations

import uuid

import pytest

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
# Helpers
# ---------------------------------------------------------------------------

def make_state(**overrides) -> PipelineState:
    base: PipelineState = {
        "intent": "Build EL Tester",
        "proposal_id": "test-proposal-001",
        "run_id": "test-run-001",
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
# Stage nodes return correct state keys
# ---------------------------------------------------------------------------

class TestStageNodes:
    def test_research_returns_research_data(self):
        result = research(make_state())
        assert "research_data" in result
        assert result["current_node"] == "research"
        assert "research" in result["completed_nodes"]

    def test_standards_returns_standards_data(self):
        result = standards(make_state())
        assert "standards_data" in result
        assert result["current_node"] == "standards"

    def test_components_returns_non_empty_bom(self):
        result = components(make_state())
        assert "bom" in result
        assert isinstance(result["bom"], list)
        assert len(result["bom"]) > 0

    def test_cad_returns_cad_artifacts(self):
        result = cad(make_state())
        assert "cad_artifacts" in result

    def test_ecad_returns_ecad_artifacts(self):
        result = ecad(make_state())
        assert "ecad_artifacts" in result

    def test_pcb_returns_pcb_artifacts(self):
        result = pcb(make_state())
        assert "pcb_artifacts" in result

    def test_bom_impact_returns_bom_impact_data(self):
        result = bom_impact(make_state())
        assert "bom_impact_data" in result

    def test_risk_swot_returns_risk_swot_data(self):
        result = risk_swot(make_state())
        assert "risk_swot_data" in result

    def test_rfq_draft_returns_list(self):
        result = rfq_draft(make_state())
        assert "rfq_drafts" in result
        assert isinstance(result["rfq_drafts"], list)

    def test_proposal_returns_proposal_doc(self):
        result = proposal(make_state())
        assert "proposal_doc" in result

    def test_pitch_returns_pitch_doc(self):
        result = pitch(make_state())
        assert "pitch_doc" in result

    def test_landing_returns_url(self):
        result = landing(make_state())
        assert "landing_url" in result
        assert result["landing_url"] is not None

    def test_linkedin_returns_draft(self):
        result = linkedin(make_state())
        assert "linkedin_draft" in result
        assert result["linkedin_draft"] is not None


# ---------------------------------------------------------------------------
# Gate nodes — pause and await human approval
# ---------------------------------------------------------------------------

GATE_PARAMS = [
    (gate1, "gate1"),
    (gate2, "gate2"),
    (gate3, "gate3"),
    (gate4, "gate4"),
    (gate5, "gate5"),
]


class TestGateNodes:
    @pytest.mark.parametrize("gate_fn,gate_id", GATE_PARAMS)
    def test_gate_sets_awaiting_human_when_not_approved(self, gate_fn, gate_id):
        result = gate_fn(make_state())
        assert result["awaiting_human"] is True, (
            f"{gate_id} must set awaiting_human=True when not approved"
        )
        assert result["gate_name"] is not None
        assert gate_id in result["gate_name"]

    @pytest.mark.parametrize("gate_fn,gate_id", GATE_PARAMS)
    def test_gate_clears_awaiting_human_when_approved(self, gate_fn, gate_id, monkeypatch):
        import graph.nodes as nodes_module
        monkeypatch.setattr(nodes_module, "_check_gate_approval", lambda *_: True)
        result = gate_fn(make_state())
        assert result["awaiting_human"] is False
        assert result["gate_name"] is None
        assert gate_id in result["completed_nodes"]


# ---------------------------------------------------------------------------
# All 18 nodes present
# ---------------------------------------------------------------------------

class TestNodeInventory:
    def test_all_18_nodes_in_graph_nodes_module(self):
        import graph.nodes as n
        expected = {
            "research", "standards", "components",
            "gate1", "cad", "ecad", "pcb",
            "gate2", "bom_impact", "risk_swot", "rfq_draft",
            "gate3", "proposal", "pitch",
            "gate4", "landing", "linkedin",
            "gate5",
        }
        actual = {
            name for name in dir(n)
            if callable(getattr(n, name)) and not name.startswith("_")
        }
        missing = expected - actual
        assert not missing, f"Missing nodes in graph/nodes.py: {missing}"

    def test_node_sequence_length(self):
        assert len(NODE_SEQUENCE) == 18

    def test_node_sequence_order(self):
        assert NODE_SEQUENCE[0] == "research"
        assert NODE_SEQUENCE[-1] == "gate5"
        assert NODE_SEQUENCE.index("gate1") < NODE_SEQUENCE.index("cad")
        assert NODE_SEQUENCE.index("gate2") < NODE_SEQUENCE.index("bom_impact")
        assert NODE_SEQUENCE.index("gate3") < NODE_SEQUENCE.index("proposal")
        assert NODE_SEQUENCE.index("gate4") < NODE_SEQUENCE.index("landing")


# ---------------------------------------------------------------------------
# Graph compilation and execution
# ---------------------------------------------------------------------------

class TestGraphCompilation:
    def test_graph_compiles_without_error(self):
        graph = build_graph()
        assert graph is not None

    def test_graph_runs_until_first_gate(self):
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = graph.invoke(make_state(), config=config)
        assert result["awaiting_human"] is True
        assert result["gate_name"] is not None
        assert "gate1" in result["gate_name"]
        # Pre-gate nodes should be in completed_nodes
        for node in ("research", "standards", "components"):
            assert node in result["completed_nodes"], f"{node} not in completed_nodes"

    def test_graph_resumes_past_gate_when_approved(self, monkeypatch):
        import graph.nodes as nodes_module
        monkeypatch.setattr(nodes_module, "_check_gate_approval", lambda *_: True)
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = graph.invoke(make_state(), config=config)
        # With all gates approved the pipeline runs to completion
        assert result["awaiting_human"] is False
        assert "gate5" in result["completed_nodes"]


# ---------------------------------------------------------------------------
# run.py CLI
# ---------------------------------------------------------------------------

class TestRunCLI:
    def test_help_exits_zero(self):
        import subprocess
        import sys
        proc = subprocess.run(
            [sys.executable, "-m", "graph.run", "--help"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        assert "--intent" in proc.stdout
        assert "--resume-from" in proc.stdout

    def test_list_nodes_exits_zero(self):
        import subprocess
        import sys
        proc = subprocess.run(
            [sys.executable, "-m", "graph.run", "--list-nodes"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        assert "research" in proc.stdout
        assert "gate5" in proc.stdout
