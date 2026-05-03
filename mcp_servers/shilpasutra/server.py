"""
ShilpaSutra MCP Server (Session 2.3).

Exposes four tools:
  cad_generate  – parametric CAD model from a spec dict
  step_export   – convert model file to STEP
  cfd_run       – submit async CFD simulation, returns job_id
  cfd_status    – poll job_id for progress / results

Backend priority: shilpasutra > cadquery > stub.
CFD jobs run in a daemon thread so the MCP call returns immediately.
"""

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------
try:
    import shilpasutra as ss  # type: ignore
    _BACKEND = "shilpasutra"
except ImportError:
    try:
        import cadquery as cq  # type: ignore
        _BACKEND = "cadquery"
    except ImportError:
        cq = None  # type: ignore
        _BACKEND = "stub"

OUTPUT_DIR = Path(os.environ.get("SHILPA_OUTPUT_DIR", "/tmp/shilpasutra"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_cfd_jobs: dict[str, dict[str, Any]] = {}
_cfd_lock = threading.Lock()

mcp = FastMCP(
    "shilpasutra",
    description="CAD generation, STEP export, and CFD simulation via ShilpaSutra",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _model_path(name: str) -> Path:
    return OUTPUT_DIR / f"{name}.brep"


def _step_path(name: str) -> Path:
    return OUTPUT_DIR / f"{name}.step"


def _generate_cad(spec: dict[str, Any]) -> Path:
    name = spec.get("name", "model")
    shape_type = spec.get("shape", "box")

    if _BACKEND == "shilpasutra":
        model = ss.generate(spec)
        out = _model_path(name)
        ss.save(model, str(out))
        return out

    if _BACKEND == "cadquery":
        if shape_type == "cylinder":
            radius = float(spec.get("radius", 10))
            height = float(spec.get("height", 20))
            shape = cq.Workplane("XY").circle(radius).extrude(height)
        elif shape_type == "sphere":
            radius = float(spec.get("radius", 10))
            shape = cq.Workplane("XY").sphere(radius)
        else:  # box (default)
            length = float(spec.get("length", 10))
            width = float(spec.get("width", 10))
            height = float(spec.get("height", 10))
            shape = cq.Workplane("XY").box(length, width, height)
        out = _model_path(name)
        cq.exporters.export(shape, str(out), "BREP")
        return out

    # stub — JSON placeholder so callers still get a real path
    out = _model_path(name)
    out.write_text(json.dumps({"spec": spec, "stub": True}))
    return out


def _export_step_file(model_file: Path) -> Path:
    out = _step_path(model_file.stem)

    if _BACKEND == "shilpasutra":
        model = ss.load(str(model_file))
        ss.export_step(model, str(out))
        return out

    if _BACKEND == "cadquery":
        shape = cq.importers.importBrep(str(model_file))
        cq.exporters.export(shape, str(out), "STEP")
        return out

    # stub
    out.write_text(f"STEP stub for {model_file.name}")
    return out


def _update_progress(job_id: str, pct: int) -> None:
    with _cfd_lock:
        if job_id in _cfd_jobs:
            _cfd_jobs[job_id]["progress"] = pct


def _run_cfd_blocking(job_id: str, spec: dict[str, Any]) -> None:
    """Runs inside a daemon thread; updates _cfd_jobs in place."""
    try:
        with _cfd_lock:
            _cfd_jobs[job_id]["status"] = "running"

        if _BACKEND == "shilpasutra" and hasattr(ss, "cfd_run"):
            result = ss.cfd_run(
                spec,
                progress_cb=lambda p: _update_progress(job_id, p),
            )
        else:
            # Stub simulation: ramp progress 0→100 over ~5 s
            for pct in range(10, 101, 10):
                time.sleep(0.5)
                _update_progress(job_id, pct)
            result = {
                "drag_coefficient": 0.47,
                "lift_coefficient": 0.0,
                "pressure_drop_pa": 12.3,
                "mesh_cells": 50000,
                "converged": True,
                "backend": _BACKEND,
            }

        with _cfd_lock:
            _cfd_jobs[job_id]["status"] = "done"
            _cfd_jobs[job_id]["progress"] = 100
            _cfd_jobs[job_id]["result"] = result

    except Exception as exc:  # noqa: BLE001
        with _cfd_lock:
            _cfd_jobs[job_id]["status"] = "failed"
            _cfd_jobs[job_id]["error"] = str(exc)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def cad_generate(spec: dict) -> dict:
    """Generate a parametric CAD model from a spec dict.

    Args:
        spec: Parametric spec. Required key: 'name' (str). Optional:
              'shape' ('box'|'cylinder'|'sphere'), plus dimension keys
              length/width/height/radius (all floats, mm).

    Returns:
        {"model_path": "<absolute path to .brep file>", "backend": "<backend>"}
    """
    if not isinstance(spec, dict):
        raise TypeError("spec must be a dict")
    if "name" not in spec:
        spec = {"name": "model", **spec}

    path = _generate_cad(spec)
    return {"model_path": str(path), "backend": _BACKEND}


@mcp.tool()
def step_export(model_path: str) -> dict:
    """Convert a CAD model file to STEP format.

    Args:
        model_path: Absolute path returned by cad_generate.

    Returns:
        {"step_path": "<absolute path to .step file>"}
    """
    mp = Path(model_path)
    if not mp.exists():
        raise FileNotFoundError(f"model_path not found: {model_path}")
    out = _export_step_file(mp)
    return {"step_path": str(out)}


@mcp.tool()
def cfd_run(spec: dict) -> dict:
    """Submit an async CFD simulation job.

    Args:
        spec: CFD spec dict. Recognised keys: 'model_path' (str),
              'inlet_velocity_ms' (float), 'fluid' ('air'|'water'),
              'turbulence_model' ('k-epsilon'|'k-omega').

    Returns:
        {"job_id": "<uuid>", "status": "queued"}
    """
    if not isinstance(spec, dict):
        raise TypeError("spec must be a dict")

    job_id = str(uuid.uuid4())
    with _cfd_lock:
        _cfd_jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "result": None,
            "error": None,
        }

    thread = threading.Thread(
        target=_run_cfd_blocking, args=(job_id, spec), daemon=True
    )
    thread.start()
    return {"job_id": job_id, "status": "queued"}


@mcp.tool()
def cfd_status(job_id: str) -> dict:
    """Get progress and results for a CFD simulation job.

    Args:
        job_id: UUID string returned by cfd_run.

    Returns:
        {"job_id": ..., "status": "queued"|"running"|"done"|"failed",
         "progress": 0-100, "result": {...}|null, "error": str|null}
    """
    with _cfd_lock:
        if job_id not in _cfd_jobs:
            raise KeyError(f"Unknown job_id: {job_id}")
        return {"job_id": job_id, **_cfd_jobs[job_id]}


if __name__ == "__main__":
    mcp.run()
