"""
SuryaPrajna MCP Server (Session 2.4).

Exposes four tools:
  iec_lookup        – return clause text for an IEC PV standard
  fmea_run          – compute Risk Priority Numbers for a component list
  reliability_calc  – estimate MTBF for a system at operating conditions
  get_derating_curve – return voltage/power derating data vs temperature

Backend priority: suryaprajna package > built-in lookup tables > stubs.
"""

import math
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------
try:
    import suryaprajna as sp  # type: ignore
    _BACKEND = "suryaprajna"
except ImportError:
    sp = None  # type: ignore
    _BACKEND = "builtin"

mcp = FastMCP(
    "suryaprajna",
    description=(
        "IEC standard lookups, FMEA analysis, and reliability calculations "
        "for PV test equipment"
    ),
)

# ---------------------------------------------------------------------------
# Built-in IEC lookup tables (PV-relevant standards)
# ---------------------------------------------------------------------------

_IEC_DB: dict[str, dict[str, str]] = {
    "IEC61215": {
        "title": "Terrestrial photovoltaic (PV) modules – Design qualification and type approval",
        "4.1": "Scope – establishes requirements for the design qualification and type approval of terrestrial PV modules.",
        "4.2": "Normative references – lists IEC 60068, IEC 60904 series, IEC 61730 as key references.",
        "5": "Terms and definitions – peak power, Isc, Voc, Impp, Vmpp, fill factor, temperature coefficients.",
        "6": "General requirements – test sequence MQT 01–MQT 22 covering UV, thermal cycling, humidity-freeze, damp heat, mechanical load.",
        "6.1": "Visual inspection (MQT 01) – examination for cracks, delamination, bubbles, cell mismatch.",
        "6.2": "Maximum power determination (MQT 02) – STC: 1000 W/m², AM1.5, 25 °C.",
        "6.3": "Insulation test (MQT 03) – ≥ 50 MΩ at 500 V DC.",
        "6.4": "Wet leakage current (MQT 15) – immersion test ≤ 10 mA at system voltage.",
        "6.5": "Thermal cycling (MQT 11) – 200 cycles −40 °C to +85 °C.",
        "6.6": "Humidity freeze (MQT 12) – 10 cycles; RH 85%, −40 °C freeze.",
        "6.7": "Damp heat (MQT 13) – 1000 h at 85 °C / 85% RH.",
        "6.8": "Mechanical load (MQT 16) – ±2400 Pa static load for 1 h.",
        "7": "Test report – minimum content for Type Approval certificate.",
    },
    "IEC61730": {
        "title": "Photovoltaic (PV) module safety qualification",
        "1": "Part 1: Requirements for construction.",
        "2": "Part 2: Requirements for testing – MST 01–MST 54 covering cut susceptibility, bypass diode, insulation.",
        "2.1": "MST 01 Visual inspection – baseline before all tests.",
        "2.2": "MST 11 Insulation test – DC Hi-Pot at 2×(Vsys + 1000) V.",
        "2.3": "MST 16 Bypass diode thermal test – 1 h bypass current at 75 °C ± 5 °C.",
        "2.4": "MST 26 Hail test – 25 mm ice ball at 23 m/s impact.",
        "2.5": "MST 32 Ground continuity – ≤ 0.1 Ω between accessible conductive parts and ground.",
    },
    "IEC60904": {
        "title": "Photovoltaic devices – measurement of photovoltaic current-voltage characteristics",
        "1": "Part 1: Measurement of photovoltaic current-voltage characteristics.",
        "1.1": "Clause 5 – STC: irradiance 1000 W/m², cell temperature 25 °C, AM1.5G spectrum.",
        "1.2": "Clause 6 – measurement uncertainty ≤ 2% for Isc, ≤ 1% for Voc, ≤ 3% for Pmax.",
        "3": "Part 3: Measurement principles for terrestrial PV solar devices with reference spectral irradiance data.",
        "7": "Part 7: Computation of spectral mismatch correction for measurements of photovoltaic devices.",
        "9": "Part 9: Calibration of reference solar devices – traceability to WRR.",
    },
    "IEC62446": {
        "title": "Grid connected photovoltaic systems – minimum requirements for system documentation, commissioning tests and inspection",
        "1": "Part 1: Grid connected systems – documentation, commissioning tests and inspections.",
        "1.1": "Clause 5 – system documentation requirements: as-built drawing, string layout, cable schedule.",
        "1.2": "Clause 6 – commissioning tests: Voc per string, Isc per string, insulation resistance, functional tests.",
        "1.3": "Clause 7 – periodic inspection intervals and checklist items.",
    },
    "IEC62941": {
        "title": "Terrestrial photovoltaic (PV) modules – Guideline for increased confidence in PV module design qualification and type approval testing",
        "1": "Scope – enhanced stress testing beyond IEC 61215 baseline.",
        "5": "Extended thermal cycling – up to 600 cycles option.",
        "6": "Extended damp heat – up to 2000 h option.",
    },
    "IEC61853": {
        "title": "Photovoltaic (PV) module performance testing and energy rating",
        "1": "Part 1: Irradiance and temperature performance measurements and power rating.",
        "2": "Part 2: Spectral responsivity, incidence angle and module operating temperature measurements.",
        "3": "Part 3: Energy rating of PV modules.",
        "4": "Part 4: Standard method for PV module energy production estimation.",
    },
}

# Severity scale: 1–10
_FMEA_SEVERITY: dict[str, int] = {
    "capacitor": 6,
    "resistor": 3,
    "inductor": 5,
    "mosfet": 8,
    "igbt": 8,
    "diode": 6,
    "relay": 7,
    "contactor": 7,
    "fuse": 5,
    "pcb": 7,
    "connector": 6,
    "transformer": 8,
    "sensor": 6,
    "microcontroller": 8,
    "fpga": 9,
    "default": 5,
}

# Occurrence scale: 1–10 (based on component failure rate class)
_FMEA_OCCURRENCE: dict[str, int] = {
    "capacitor": 4,
    "resistor": 2,
    "inductor": 3,
    "mosfet": 5,
    "igbt": 5,
    "diode": 3,
    "relay": 6,
    "contactor": 6,
    "fuse": 2,
    "pcb": 3,
    "connector": 4,
    "transformer": 4,
    "sensor": 5,
    "microcontroller": 4,
    "fpga": 4,
    "default": 4,
}

# Detectability scale: 1 (easy to detect) – 10 (impossible to detect)
_FMEA_DETECTABILITY: dict[str, int] = {
    "capacitor": 5,
    "resistor": 4,
    "inductor": 6,
    "mosfet": 4,
    "igbt": 4,
    "diode": 4,
    "relay": 3,
    "contactor": 3,
    "fuse": 2,
    "pcb": 7,
    "connector": 3,
    "transformer": 5,
    "sensor": 4,
    "microcontroller": 6,
    "fpga": 7,
    "default": 5,
}

# Base MTBF (hours) at 25 °C, nominal stress – MIL-HDBK-217F inspired
_BASE_MTBF_H: dict[str, float] = {
    "capacitor": 1_000_000,
    "resistor": 5_000_000,
    "inductor": 2_000_000,
    "mosfet": 800_000,
    "igbt": 700_000,
    "diode": 1_500_000,
    "relay": 500_000,
    "contactor": 300_000,
    "fuse": 3_000_000,
    "pcb": 2_000_000,
    "connector": 1_200_000,
    "transformer": 600_000,
    "sensor": 900_000,
    "microcontroller": 1_000_000,
    "fpga": 900_000,
    "default": 1_000_000,
}

# Derating curves: {component_type: [(temp_C, derating_factor), ...]}
_DERATING_CURVES: dict[str, list[tuple[float, float]]] = {
    "capacitor": [
        (25, 1.0), (50, 0.95), (70, 0.85), (85, 0.70), (105, 0.50), (125, 0.30)
    ],
    "resistor": [
        (25, 1.0), (70, 1.0), (85, 0.90), (100, 0.75), (125, 0.50), (155, 0.10)
    ],
    "mosfet": [
        (25, 1.0), (50, 0.95), (75, 0.80), (100, 0.60), (125, 0.40), (150, 0.20)
    ],
    "igbt": [
        (25, 1.0), (50, 0.95), (75, 0.80), (100, 0.60), (125, 0.40), (150, 0.20)
    ],
    "diode": [
        (25, 1.0), (50, 0.95), (75, 0.85), (100, 0.65), (125, 0.45), (150, 0.20)
    ],
    "inductor": [
        (25, 1.0), (50, 0.95), (75, 0.85), (100, 0.70), (125, 0.50)
    ],
    "default": [
        (25, 1.0), (50, 0.90), (75, 0.75), (100, 0.55), (125, 0.35)
    ],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    return s.strip().upper().replace("-", "").replace(" ", "").replace("_", "")


def _lookup_iec(standard: str, clause: str | None) -> dict[str, Any]:
    key = _norm(standard)
    match = None
    for k in _IEC_DB:
        if _norm(k) == key:
            match = k
            break
    if match is None:
        return {"found": False, "standard": standard, "clauses": {}}

    entry = _IEC_DB[match]
    if clause:
        c = clause.strip()
        text = entry.get(c) or entry.get(c.lstrip("0")) or None
        return {
            "found": text is not None,
            "standard": match,
            "title": entry.get("title", ""),
            "clause": c,
            "text": text or f"Clause {c} not in built-in table.",
        }
    return {
        "found": True,
        "standard": match,
        "title": entry.get("title", ""),
        "clauses": {k: v for k, v in entry.items() if k != "title"},
    }


def _component_key(name: str) -> str:
    n = name.lower()
    for k in _FMEA_SEVERITY:
        if k in n:
            return k
    return "default"


def _arrhenius_factor(temp_c: float, ea_ev: float = 0.7) -> float:
    k_b = 8.617e-5  # eV/K
    t_ref = 298.15  # 25 °C
    t_op = temp_c + 273.15
    return math.exp(ea_ev / k_b * (1 / t_ref - 1 / t_op))


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def iec_lookup(standard: str, clause: str = "") -> dict:
    """Look up IEC PV standard clause text.

    Args:
        standard: Standard identifier, e.g. "IEC61215", "IEC 61730", "IEC60904".
        clause:   Optional clause number, e.g. "6.2", "5". Omit to list all clauses.

    Returns:
        {
          "found": bool,
          "standard": str,
          "title": str,
          "clause": str,          # only when clause provided
          "text": str,            # only when clause provided
          "clauses": {str: str},  # only when no clause provided
        }
    """
    if sp is not None and hasattr(sp, "iec_lookup"):
        return sp.iec_lookup(standard, clause)
    return _lookup_iec(standard, clause or None)


@mcp.tool()
def fmea_run(components: list, temperature_c: float = 25.0) -> dict:
    """Run FMEA and compute Risk Priority Numbers for a component list.

    Args:
        components: List of component dicts. Each item must have at minimum:
                    {"name": str}.  Optional keys:
                    "quantity" (int, default 1),
                    "severity" (int 1-10, overrides default),
                    "occurrence" (int 1-10, overrides default),
                    "detectability" (int 1-10, overrides default).
        temperature_c: Operating temperature in °C for occurrence scaling (default 25).

    Returns:
        {
          "temperature_c": float,
          "results": [
            {
              "name": str,
              "quantity": int,
              "severity": int,
              "occurrence": int,
              "detectability": int,
              "rpn": int,           # severity × occurrence × detectability
              "risk_level": str,    # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
            }, ...
          ],
          "system_rpn": int,
          "critical_components": [str],
        }
    """
    if sp is not None and hasattr(sp, "fmea_run"):
        return sp.fmea_run(components, temperature_c)

    if not isinstance(components, list) or len(components) == 0:
        raise ValueError("components must be a non-empty list of dicts")

    # Temperature derating factor on occurrence (Arrhenius)
    arr = _arrhenius_factor(temperature_c)
    occ_scale = min(arr, 3.0)  # cap at 3× to stay within 1–10 range

    results = []
    for comp in components:
        if not isinstance(comp, dict):
            raise TypeError(f"Each component must be a dict, got {type(comp)}")
        name = comp.get("name", "unknown")
        qty = int(comp.get("quantity", 1))
        ckey = _component_key(name)

        sev = int(comp.get("severity", _FMEA_SEVERITY[ckey]))
        raw_occ = int(comp.get("occurrence", _FMEA_OCCURRENCE[ckey]))
        occ = max(1, min(10, round(raw_occ * occ_scale)))
        det = int(comp.get("detectability", _FMEA_DETECTABILITY[ckey]))

        sev = max(1, min(10, sev))
        occ = max(1, min(10, occ))
        det = max(1, min(10, det))

        rpn = sev * occ * det
        if rpn >= 500:
            risk = "CRITICAL"
        elif rpn >= 200:
            risk = "HIGH"
        elif rpn >= 80:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        results.append({
            "name": name,
            "quantity": qty,
            "severity": sev,
            "occurrence": occ,
            "detectability": det,
            "rpn": rpn,
            "risk_level": risk,
        })

    results.sort(key=lambda x: x["rpn"], reverse=True)
    system_rpn = sum(r["rpn"] for r in results)
    critical = [r["name"] for r in results if r["risk_level"] in ("HIGH", "CRITICAL")]

    return {
        "temperature_c": temperature_c,
        "results": results,
        "system_rpn": system_rpn,
        "critical_components": critical,
    }


@mcp.tool()
def reliability_calc(
    components: list,
    temperature_c: float = 25.0,
    mission_time_h: float = 8760.0,
) -> dict:
    """Estimate system MTBF and reliability for a list of components.

    Uses series reliability model (weakest-link). Failure rates are derived
    from MIL-HDBK-217F base values scaled by an Arrhenius temperature factor.

    Args:
        components: List of component dicts with keys:
                    "name" (str, required),
                    "quantity" (int, default 1),
                    "base_mtbf_h" (float, optional – overrides built-in value).
        temperature_c:  Operating temperature in °C (default 25).
        mission_time_h: Mission time in hours for R(t) calculation (default 8760 = 1 year).

    Returns:
        {
          "temperature_c": float,
          "mission_time_h": float,
          "component_results": [
            {
              "name": str,
              "quantity": int,
              "base_mtbf_h": float,
              "derated_mtbf_h": float,
              "failure_rate_per_h": float,
            }, ...
          ],
          "system_mtbf_h": float,
          "system_mtbf_years": float,
          "system_failure_rate_per_h": float,
          "reliability_at_mission_time": float,  # R(t) = e^(-t/MTBF)
        }
    """
    if sp is not None and hasattr(sp, "reliability_calc"):
        return sp.reliability_calc(components, temperature_c, mission_time_h)

    if not isinstance(components, list) or len(components) == 0:
        raise ValueError("components must be a non-empty list of dicts")

    arr = _arrhenius_factor(temperature_c)
    total_lambda = 0.0
    comp_results = []

    for comp in components:
        if not isinstance(comp, dict):
            raise TypeError(f"Each component must be a dict, got {type(comp)}")
        name = comp.get("name", "unknown")
        qty = int(comp.get("quantity", 1))
        ckey = _component_key(name)
        base_mtbf = float(comp.get("base_mtbf_h", _BASE_MTBF_H[ckey]))

        # Derate MTBF by Arrhenius factor (higher temp → lower MTBF)
        derated_mtbf = base_mtbf / arr
        lam = qty / derated_mtbf
        total_lambda += lam

        comp_results.append({
            "name": name,
            "quantity": qty,
            "base_mtbf_h": round(base_mtbf, 2),
            "derated_mtbf_h": round(derated_mtbf, 2),
            "failure_rate_per_h": lam,
        })

    system_mtbf_h = 1.0 / total_lambda if total_lambda > 0 else float("inf")
    system_mtbf_years = system_mtbf_h / 8760.0
    r_t = math.exp(-mission_time_h * total_lambda)

    return {
        "temperature_c": temperature_c,
        "mission_time_h": mission_time_h,
        "component_results": comp_results,
        "system_mtbf_h": round(system_mtbf_h, 2),
        "system_mtbf_years": round(system_mtbf_years, 3),
        "system_failure_rate_per_h": total_lambda,
        "reliability_at_mission_time": round(r_t, 6),
    }


@mcp.tool()
def get_derating_curve(component_type: str) -> dict:
    """Return voltage/power derating factors vs temperature for a component type.

    Args:
        component_type: Component class, e.g. "capacitor", "mosfet", "resistor",
                        "igbt", "diode", "inductor". Falls back to "default".

    Returns:
        {
          "component_type": str,
          "curve": [
            {"temperature_c": float, "derating_factor": float}, ...
          ],
          "note": str,
        }
    """
    if sp is not None and hasattr(sp, "get_derating_curve"):
        return sp.get_derating_curve(component_type)

    ctype = component_type.strip().lower()
    curve_data = _DERATING_CURVES.get(ctype, _DERATING_CURVES["default"])
    used_type = ctype if ctype in _DERATING_CURVES else "default"

    return {
        "component_type": used_type,
        "curve": [
            {"temperature_c": t, "derating_factor": f}
            for t, f in curve_data
        ],
        "note": (
            "Derating factor is applied to rated voltage/power. "
            "Values sourced from IEC and MIL-HDBK-217F guidelines."
        ),
    }


if __name__ == "__main__":
    mcp.run()
