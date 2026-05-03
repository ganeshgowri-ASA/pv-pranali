"""ECAD agent: PlantUML P&ID diagram generation."""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path
from typing import Any, Dict, List

from graph.state import PipelineState


# ---------------------------------------------------------------------------
# PlantUML source template
# ---------------------------------------------------------------------------

_PID_TEMPLATE = textwrap.dedent("""\
    @startuml
    skinparam monochrome true
    skinparam defaultFontSize 12
    title P&ID — {intent}

    component [Solar Array] as PV
    component [String Junction Box] as JB
    component [DC Combiner] as DCB
    component [Inverter / Converter] as INV
    component [AC Distribution Panel] as ACP
    component [Utility Grid] as GRID
    component [Data Acquisition System] as DAQ
    component [Safety Relay] as RELAY

    PV --> JB : DC Strings
    JB --> DCB : Parallel Strings
    DCB --> INV : DC Bus
    INV --> ACP : AC Output
    ACP --> GRID : Grid Tie
    INV ..> DAQ : Modbus/SCPI
    DAQ ..> RELAY : Interlock
    RELAY ..> INV : E-Stop

    note right of INV
      Proposal: {proposal_id}
    end note
    @enduml
""")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_plantuml_source(intent: str, proposal_id: str, bom: List[Any]) -> str:  # noqa: ARG001
    return _PID_TEMPLATE.format(intent=intent or "PV Test Equipment", proposal_id=proposal_id)


def _render_plantuml(source_path: Path, output_dir: Path) -> Dict[str, str]:
    """Invoke ``plantuml`` via subprocess for PNG and SVG export.

    If plantuml is not installed or the process fails, empty stub files are
    written so callers always receive valid (existing) paths.
    """
    results: Dict[str, str] = {}
    for fmt, flag in (("png", "-tpng"), ("svg", "-tsvg")):
        out_path = output_dir / source_path.with_suffix(f".{fmt}").name
        try:
            proc = subprocess.run(
                ["plantuml", flag, f"-o{output_dir}", str(source_path)],
                capture_output=True,
                timeout=60,
            )
            if proc.returncode != 0 or not out_path.exists():
                out_path.write_bytes(b"")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            out_path.write_bytes(b"")
        results[fmt] = str(out_path)
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pid(state: PipelineState) -> PipelineState:
    """Generate a PlantUML P&ID diagram (PNG + SVG) for the proposal.

    The PlantUML source is written to ``output_dir`` alongside the rendered
    outputs for reproducibility.  Rendering is attempted via the system
    ``plantuml`` binary; stub empty files are written when it is absent.

    Args:
        state: Current pipeline state.  Reads ``intent``, ``bom``,
               ``proposal_id``, and optional ``output_dir``.

    Returns:
        Updated state with:
          - ``ecad_artifacts['pid_source']`` — path to ``.puml`` source
          - ``ecad_artifacts['pid_png']``    — path to PNG output
          - ``ecad_artifacts['pid_svg']``    — path to SVG output
    """
    output_dir = Path(state.get("output_dir", "/tmp/pv_pranali_outputs"))  # type: ignore[arg-type]
    output_dir.mkdir(parents=True, exist_ok=True)

    proposal_id = state.get("proposal_id", "unknown")
    intent = state.get("intent", "")
    bom = state.get("bom", [])

    source = _build_plantuml_source(intent, proposal_id, bom)
    source_path = output_dir / f"{proposal_id}_pid.puml"
    source_path.write_text(source)

    rendered = _render_plantuml(source_path, output_dir)

    existing: Dict[str, Any] = dict(state.get("ecad_artifacts", {}))
    existing["pid_source"] = str(source_path)
    existing["pid_png"] = rendered.get("png", "")
    existing["pid_svg"] = rendered.get("svg", "")

    return {
        **state,  # type: ignore[misc]
        "ecad_artifacts": existing,
        "current_node": "ecad",
        "completed_nodes": list(state.get("completed_nodes", [])) + ["ecad_pid"],
    }
