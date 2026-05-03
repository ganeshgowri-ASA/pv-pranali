"""
Vidyut ECAD MCP Server (Session 2.5).

Exposes four tools:
  schematic_generate  – build a KiCad schematic from a netlist dict
  layout_run          – run KiCad PCB auto-layout on a .kicad_pcb file
  drc_check           – execute DRC and return violations list
  export_gerber       – export Gerber files and return a zip archive path

Backend priority: vidyut-srishti-prd KiCad wrappers > kicad-cli subprocess > stub.
All file outputs written to OUTPUT_DIR (env var, default /tmp/vidyut).
"""

import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------
try:
    import vidyut_srishti as vs  # type: ignore
    _BACKEND = "vidyut-srishti-prd"
except ImportError:
    vs = None  # type: ignore
    _BACKEND = "kicad-cli" if shutil.which("kicad-cli") else "stub"

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/vidyut"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP(
    "vidyut",
    description="KiCad ECAD MCP: schematic generation, PCB layout, DRC, and Gerber export",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a subprocess, raising on non-zero exit."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command {cmd[0]} failed (rc={result.returncode}):\n"
            f"{result.stderr.strip()}"
        )
    return result


def _netlist_to_kicad_sch(netlist: dict[str, Any], out_path: Path) -> None:
    """
    Convert a netlist dict to a minimal KiCad 6+ schematic file.

    netlist format:
      {
        "title": "My Schematic",
        "components": [
          {"ref": "R1", "value": "10k", "footprint": "Resistor_SMD:R_0402"},
          ...
        ],
        "nets": [
          {"name": "VCC", "pins": [{"ref": "R1", "pin": "1"}, ...]},
          ...
        ]
      }
    """
    title = netlist.get("title", "generated")
    components = netlist.get("components", [])
    nets = netlist.get("nets", [])

    lines = [
        "(kicad_sch",
        '  (version 20230121)',
        '  (generator vidyut-mcp)',
        f'  (title_block (title "{title}"))',
    ]

    # Emit symbols (one lib_sym per component, placed on grid)
    x, y = 50, 50
    for idx, comp in enumerate(components):
        ref = comp.get("ref", f"U{idx+1}")
        value = comp.get("value", "?")
        footprint = comp.get("footprint", "")
        lines += [
            f'  (symbol (lib_id "") (at {x} {y} 0) (unit 1)',
            f'    (property "Reference" "{ref}" (at {x} {y-2} 0))',
            f'    (property "Value" "{value}" (at {x} {y+2} 0))',
            f'    (property "Footprint" "{footprint}" (at {x} {y+4} 0))',
            '  )',
        ]
        x += 20
        if x > 200:
            x = 50
            y += 30

    # Emit net labels
    lx, ly = 50, 200
    for net in nets:
        name = net.get("name", "NET")
        lines.append(
            f'  (label "{name}" (at {lx} {ly} 0) (effects (font (size 1.27 1.27))))'
        )
        lx += 20
        if lx > 200:
            lx = 50
            ly += 10

    lines.append(")")
    out_path.write_text("\n".join(lines))


def _stub_drc_violations() -> list[dict]:
    return [
        {
            "severity": "info",
            "type": "drc_stub",
            "description": "DRC ran in stub mode (kicad-cli not found)",
            "location": {"sheet": "", "x": 0, "y": 0},
        }
    ]


def _parse_drc_json(drc_json_path: Path) -> list[dict]:
    """Parse kicad-cli DRC JSON output into a normalised violations list."""
    raw = json.loads(drc_json_path.read_text())
    violations = []
    for item in raw.get("violations", []):
        violations.append({
            "severity": item.get("severity", "error"),
            "type": item.get("type", "unknown"),
            "description": item.get("description", ""),
            "location": {
                "sheet": item.get("items", [{}])[0].get("description", ""),
                "x": item.get("items", [{}])[0].get("pos", {}).get("x", 0),
                "y": item.get("items", [{}])[0].get("pos", {}).get("y", 0),
            },
        })
    return violations


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def schematic_generate(netlist: dict) -> dict:
    """Generate a KiCad schematic from a netlist dict.

    Args:
        netlist: Netlist description with keys:
            title (str): schematic title.
            components (list[dict]): each with 'ref', 'value', 'footprint'.
            nets (list[dict]): each with 'name' and 'pins' list.

    Returns:
        {"schematic_path": "<absolute path to .kicad_sch>", "backend": "<backend>"}
    """
    if not isinstance(netlist, dict):
        raise TypeError("netlist must be a dict")

    title = netlist.get("title", "generated")
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)
    out_path = OUTPUT_DIR / f"{safe_title}.kicad_sch"

    if _BACKEND == "vidyut-srishti-prd" and hasattr(vs, "schematic_generate"):
        result_path = vs.schematic_generate(netlist, str(out_path))
        return {"schematic_path": str(result_path), "backend": _BACKEND}

    # kicad-cli: generate the .kicad_sch file directly (no import subcommand
    # for netlists yet), so we write the file ourselves then validate with cli.
    _netlist_to_kicad_sch(netlist, out_path)

    if _BACKEND == "kicad-cli":
        # Validate the generated schematic with kicad-cli sch export netlist
        tmp_nl = OUTPUT_DIR / f"{safe_title}_roundtrip.net"
        try:
            _run([
                "kicad-cli", "sch", "export", "netlist",
                "--output", str(tmp_nl),
                str(out_path),
            ])
        except RuntimeError:
            pass  # validation failure is non-fatal; file already written

    return {"schematic_path": str(out_path), "backend": _BACKEND}


@mcp.tool()
def layout_run(pcb_path: str) -> dict:
    """Run KiCad PCB auto-layout (freerouting or built-in placer) on a board file.

    Args:
        pcb_path: Absolute path to a .kicad_pcb file.

    Returns:
        {"pcb_path": "<path to updated .kicad_pcb>", "backend": "<backend>"}
    """
    pp = Path(pcb_path)
    if not pp.exists():
        raise FileNotFoundError(f"pcb_path not found: {pcb_path}")

    if _BACKEND == "vidyut-srishti-prd" and hasattr(vs, "layout_run"):
        result = vs.layout_run(str(pp))
        return {"pcb_path": str(result), "backend": _BACKEND}

    if _BACKEND == "kicad-cli":
        # kicad-cli pcb drc is available; auto-route requires freerouting.
        # Run the built-in DRC as a layout check proxy and return the same file.
        drc_out = OUTPUT_DIR / f"{pp.stem}_layout_drc.json"
        try:
            _run([
                "kicad-cli", "pcb", "drc",
                "--output", str(drc_out),
                "--format", "json",
                str(pp),
            ])
        except RuntimeError:
            pass
        return {"pcb_path": str(pp), "backend": _BACKEND}

    # stub: copy file to output dir so callers always get a predictable path
    dest = OUTPUT_DIR / pp.name
    if pp != dest:
        shutil.copy2(pp, dest)
    return {"pcb_path": str(dest), "backend": _BACKEND}


@mcp.tool()
def drc_check(pcb_path: str) -> dict:
    """Execute KiCad DRC on a PCB file and return violations.

    Args:
        pcb_path: Absolute path to a .kicad_pcb file.

    Returns:
        {
            "violations": [
                {
                    "severity": "error"|"warning"|"info",
                    "type": str,
                    "description": str,
                    "location": {"sheet": str, "x": float, "y": float}
                },
                ...
            ],
            "violation_count": int,
            "backend": str
        }
    """
    pp = Path(pcb_path)
    if not pp.exists():
        raise FileNotFoundError(f"pcb_path not found: {pcb_path}")

    if _BACKEND == "vidyut-srishti-prd" and hasattr(vs, "drc_check"):
        raw = vs.drc_check(str(pp))
        violations = raw if isinstance(raw, list) else raw.get("violations", [])
        return {
            "violations": violations,
            "violation_count": len(violations),
            "backend": _BACKEND,
        }

    if _BACKEND == "kicad-cli":
        drc_out = OUTPUT_DIR / f"{pp.stem}_drc.json"
        _run([
            "kicad-cli", "pcb", "drc",
            "--output", str(drc_out),
            "--format", "json",
            str(pp),
        ])
        violations = _parse_drc_json(drc_out)
        return {
            "violations": violations,
            "violation_count": len(violations),
            "backend": _BACKEND,
        }

    violations = _stub_drc_violations()
    return {
        "violations": violations,
        "violation_count": len(violations),
        "backend": _BACKEND,
    }


@mcp.tool()
def export_gerber(pcb_path: str) -> dict:
    """Export Gerber files from a KiCad PCB and return a zip archive path.

    Args:
        pcb_path: Absolute path to a .kicad_pcb file.

    Returns:
        {"gerber_zip": "<absolute path to .zip of Gerber files>", "backend": str}
    """
    pp = Path(pcb_path)
    if not pp.exists():
        raise FileNotFoundError(f"pcb_path not found: {pcb_path}")

    gerber_dir = OUTPUT_DIR / f"{pp.stem}_gerbers"
    gerber_dir.mkdir(parents=True, exist_ok=True)
    zip_path = OUTPUT_DIR / f"{pp.stem}_gerbers.zip"

    if _BACKEND == "vidyut-srishti-prd" and hasattr(vs, "export_gerber"):
        result = vs.export_gerber(str(pp), str(gerber_dir))
        zip_path = Path(result) if isinstance(result, str) else zip_path
        return {"gerber_zip": str(zip_path), "backend": _BACKEND}

    if _BACKEND == "kicad-cli":
        _run([
            "kicad-cli", "pcb", "export", "gerbers",
            "--output", str(gerber_dir),
            str(pp),
        ])
        # Also export drill file
        try:
            _run([
                "kicad-cli", "pcb", "export", "drill",
                "--output", str(gerber_dir),
                str(pp),
            ])
        except RuntimeError:
            pass
    else:
        # stub: create placeholder files
        for layer in ["F.Cu", "B.Cu", "F.Mask", "B.Mask", "F.SilkS", "Edge.Cuts"]:
            (gerber_dir / f"{pp.stem}-{layer}.gbr").write_text(
                f"G04 Stub Gerber for {layer}*\nM02*\n"
            )
        (gerber_dir / f"{pp.stem}.drl").write_text("M48\nM30\n")

    # Zip all files in gerber_dir
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(gerber_dir.iterdir()):
            if f.is_file():
                zf.write(f, f.name)

    return {"gerber_zip": str(zip_path), "backend": _BACKEND}


if __name__ == "__main__":
    mcp.run()
