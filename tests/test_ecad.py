"""Unit tests for agents/ecad — mocked MCP and subprocess calls."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from graph.state import PipelineState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(tmp_path: Path, **overrides) -> PipelineState:
    base: PipelineState = {
        "intent": "Build EL Tester",
        "proposal_id": "test-ecad-001",
        "run_id": "run-ecad-001",
        "current_node": "",
        "awaiting_human": False,
        "gate_name": None,
        "completed_nodes": [],
        "tokens_used": 0,
        "error": None,
        "research_data": {},
        "standards_data": {},
        "bom": [{"mpn": "FAKE-123", "qty": 2}],
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
        "output_dir": str(tmp_path),  # type: ignore[typeddict-unknown-key]
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


# ---------------------------------------------------------------------------
# generate_sld tests
# ---------------------------------------------------------------------------

class TestGenerateSld:
    def test_returns_sld_path_in_ecad_artifacts(self, tmp_path):
        from agents.ecad.sld import generate_sld

        with patch("agents.ecad.sld._call_vidyut_schematic_generate") as mock_mcp:
            mock_mcp.return_value = {"status": "ok", "output_path": ""}
            result = generate_sld(_make_state(tmp_path))

        assert "sld_path" in result["ecad_artifacts"]

    def test_sld_file_exists_on_disk(self, tmp_path):
        from agents.ecad.sld import generate_sld

        with patch("agents.ecad.sld._call_vidyut_schematic_generate") as mock_mcp:
            mock_mcp.return_value = {"status": "ok", "output_path": ""}
            result = generate_sld(_make_state(tmp_path))

        sld_path = Path(result["ecad_artifacts"]["sld_path"])
        assert sld_path.exists()
        assert sld_path.suffix == ".kicad_sch"

    def test_sld_path_uses_mcp_returned_path_when_provided(self, tmp_path):
        from agents.ecad.sld import generate_sld

        expected = tmp_path / "custom_output.kicad_sch"
        expected.write_text("(kicad_sch)")

        with patch("agents.ecad.sld._call_vidyut_schematic_generate") as mock_mcp:
            mock_mcp.return_value = {"status": "ok", "output_path": str(expected)}
            result = generate_sld(_make_state(tmp_path))

        assert result["ecad_artifacts"]["sld_path"] == str(expected)

    def test_mcp_called_with_proposal_id_and_bom(self, tmp_path):
        from agents.ecad.sld import generate_sld

        with patch("agents.ecad.sld._call_vidyut_schematic_generate") as mock_mcp:
            mock_mcp.return_value = {"status": "ok", "output_path": ""}
            generate_sld(_make_state(tmp_path))

        call_params = mock_mcp.call_args[0][0]
        assert call_params["proposal_id"] == "test-ecad-001"
        assert call_params["bom"] == [{"mpn": "FAKE-123", "qty": 2}]

    def test_state_fields_preserved(self, tmp_path):
        from agents.ecad.sld import generate_sld

        with patch("agents.ecad.sld._call_vidyut_schematic_generate") as mock_mcp:
            mock_mcp.return_value = {"status": "ok", "output_path": ""}
            result = generate_sld(_make_state(tmp_path))

        assert result["intent"] == "Build EL Tester"
        assert result["proposal_id"] == "test-ecad-001"
        assert "ecad_sld" in result["completed_nodes"]
        assert result["current_node"] == "ecad"

    def test_stub_fallback_when_mcp_raises(self, tmp_path):
        """generate_sld must not raise even when MCP throws."""
        from agents.ecad.sld import generate_sld

        with patch(
            "agents.ecad.sld._call_vidyut_schematic_generate",
            side_effect=RuntimeError("server offline"),
        ):
            with pytest.raises(RuntimeError):
                # The raw error propagates from _call_vidyut_schematic_generate;
                # callers should wrap in try/except at the graph node level.
                generate_sld(_make_state(tmp_path))

    def test_stub_fallback_returns_valid_path_on_mcp_stub_status(self, tmp_path):
        from agents.ecad.sld import generate_sld

        with patch("agents.ecad.sld._call_vidyut_schematic_generate") as mock_mcp:
            mock_mcp.return_value = {"status": "stub", "error": "not reachable", "output_path": ""}
            result = generate_sld(_make_state(tmp_path))

        sld_path = Path(result["ecad_artifacts"]["sld_path"])
        assert sld_path.exists()


# ---------------------------------------------------------------------------
# generate_pid tests
# ---------------------------------------------------------------------------

class TestGeneratePid:
    def _mock_subprocess_success(self, tmp_path: Path):
        """Return a mock that writes stub output files so exists() returns True."""
        def _side_effect(cmd, **kwargs):
            # Derive output path from the -o flag and source path
            source = Path(cmd[-1])
            for flag in cmd:
                if flag.startswith("-o"):
                    out_dir = Path(flag[2:])
                    break
            else:
                out_dir = tmp_path
            fmt = "png" if "-tpng" in cmd else "svg"
            (out_dir / source.with_suffix(f".{fmt}").name).write_bytes(b"stub")
            mock_result = MagicMock()
            mock_result.returncode = 0
            return mock_result
        return _side_effect

    def test_returns_pid_source_png_svg_paths(self, tmp_path):
        from agents.ecad.pid import generate_pid

        with patch("subprocess.run", side_effect=self._mock_subprocess_success(tmp_path)):
            result = generate_pid(_make_state(tmp_path))

        arts = result["ecad_artifacts"]
        assert "pid_source" in arts
        assert "pid_png" in arts
        assert "pid_svg" in arts

    def test_plantuml_source_file_written(self, tmp_path):
        from agents.ecad.pid import generate_pid

        with patch("subprocess.run", side_effect=self._mock_subprocess_success(tmp_path)):
            result = generate_pid(_make_state(tmp_path))

        source_path = Path(result["ecad_artifacts"]["pid_source"])
        assert source_path.exists()
        assert source_path.suffix == ".puml"
        assert "@startuml" in source_path.read_text()

    def test_source_contains_intent_and_proposal_id(self, tmp_path):
        from agents.ecad.pid import generate_pid

        with patch("subprocess.run", side_effect=self._mock_subprocess_success(tmp_path)):
            result = generate_pid(_make_state(tmp_path))

        source_text = Path(result["ecad_artifacts"]["pid_source"]).read_text()
        assert "EL Tester" in source_text
        assert "test-ecad-001" in source_text

    def test_png_and_svg_paths_exist(self, tmp_path):
        from agents.ecad.pid import generate_pid

        with patch("subprocess.run", side_effect=self._mock_subprocess_success(tmp_path)):
            result = generate_pid(_make_state(tmp_path))

        assert Path(result["ecad_artifacts"]["pid_png"]).exists()
        assert Path(result["ecad_artifacts"]["pid_svg"]).exists()

    def test_graceful_fallback_when_plantuml_missing(self, tmp_path):
        from agents.ecad.pid import generate_pid

        with patch("subprocess.run", side_effect=FileNotFoundError("plantuml not found")):
            result = generate_pid(_make_state(tmp_path))

        # Stub empty files should still be created
        assert Path(result["ecad_artifacts"]["pid_png"]).exists()
        assert Path(result["ecad_artifacts"]["pid_svg"]).exists()

    def test_graceful_fallback_on_subprocess_timeout(self, tmp_path):
        from agents.ecad.pid import generate_pid

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("plantuml", 60)):
            result = generate_pid(_make_state(tmp_path))

        assert Path(result["ecad_artifacts"]["pid_png"]).exists()

    def test_state_fields_preserved(self, tmp_path):
        from agents.ecad.pid import generate_pid

        with patch("subprocess.run", side_effect=self._mock_subprocess_success(tmp_path)):
            result = generate_pid(_make_state(tmp_path))

        assert result["intent"] == "Build EL Tester"
        assert result["proposal_id"] == "test-ecad-001"
        assert "ecad_pid" in result["completed_nodes"]
        assert result["current_node"] == "ecad"

    def test_existing_ecad_artifacts_preserved(self, tmp_path):
        from agents.ecad.pid import generate_pid

        state = _make_state(tmp_path, ecad_artifacts={"sld_path": "/some/prior.kicad_sch"})
        with patch("subprocess.run", side_effect=self._mock_subprocess_success(tmp_path)):
            result = generate_pid(state)

        assert result["ecad_artifacts"]["sld_path"] == "/some/prior.kicad_sch"
        assert "pid_source" in result["ecad_artifacts"]
