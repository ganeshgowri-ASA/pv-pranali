"""ECAD agent: KiCad single-line diagram (SLD) and control wiring schematic."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from graph.state import PipelineState


# ---------------------------------------------------------------------------
# MCP helper
# ---------------------------------------------------------------------------

def _call_vidyut_schematic_generate(params: Dict[str, Any]) -> Dict[str, Any]:
    """Call vidyut MCP server schematic_generate tool.

    Falls back to a stub dict if the MCP server is unavailable so that
    the rest of the pipeline can continue in offline / test environments.
    """
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def _run() -> str:
            server_params = StdioServerParameters(
                command="python",
                args=["-m", "mcp_servers.vidyut"],
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("schematic_generate", params)
                    return result.content[0].text if result.content else "{}"

        raw = asyncio.run(_run())
        return json.loads(raw) if isinstance(raw, str) else raw  # type: ignore[arg-type]
    except Exception as exc:  # server offline, not installed, etc.
        return {"status": "stub", "error": str(exc), **params}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_sld(state: PipelineState) -> PipelineState:
    """Generate a KiCad SLD / control wiring schematic for the proposal.

    Calls the vidyut MCP ``schematic_generate`` tool and writes the result to
    ``output_dir``.  When the MCP server is unreachable a minimal placeholder
    ``.kicad_sch`` file is written so downstream nodes still have a valid path.

    Args:
        state: Current pipeline state.  Reads ``intent``, ``bom``,
               ``proposal_id``, and optional ``output_dir``.

    Returns:
        Updated state with ``ecad_artifacts['sld_path']`` set to the absolute
        path of the generated ``.kicad_sch`` file.
    """
    output_dir = Path(state.get("output_dir", "/tmp/pv_pranali_outputs"))  # type: ignore[arg-type]
    output_dir.mkdir(parents=True, exist_ok=True)

    proposal_id = state.get("proposal_id", "unknown")
    intent = state.get("intent", "")
    bom = state.get("bom", [])

    expected_path = output_dir / f"{proposal_id}_sld.kicad_sch"
    params: Dict[str, Any] = {
        "proposal_id": proposal_id,
        "intent": intent,
        "bom": bom,
        "output_path": str(expected_path),
    }

    mcp_result = _call_vidyut_schematic_generate(params)

    # Use MCP-returned path if present, otherwise fall back to expected path.
    sld_path = Path(mcp_result.get("output_path") or expected_path)

    # Ensure the file exists (creates a minimal stub when MCP is offline).
    if not sld_path.exists():
        sld_path.write_text(
            f"(kicad_sch (version 20231120) (generator pv_pranali_ecad)"
            f" (uuid {proposal_id}))\n"
        )

    existing: Dict[str, Any] = dict(state.get("ecad_artifacts", {}))
    existing["sld_path"] = str(sld_path)
    existing["sld_mcp_result"] = mcp_result

    return {
        **state,  # type: ignore[misc]
        "ecad_artifacts": existing,
        "current_node": "ecad",
        "completed_nodes": list(state.get("completed_nodes", [])) + ["ecad_sld"],
    }
