"""
Karaveda MCP Server (Session 2.7).

Exposes four tools:
  hsn_lookup          – description + GST/BCD rates for an HSN code
  gst_calc            – CGST / SGST / IGST breakdown on a value
  customs_calc        – BCD + SWS on a CIF import value
  landed_cost_summary – full FOB → landed cost breakdown

Tax data is loaded from tax_tables.py (karaveda HSN table);
no rates are hard-coded in this file.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running as `python server.py` from any CWD
sys.path.insert(0, str(Path(__file__).parent))

from tax_tables import lookup  # noqa: E402

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "karaveda",
    description=(
        "GST calculation and customs duty computation for "
        "imported PV test-equipment components"
    ),
)


# ---------------------------------------------------------------------------
# Tool: hsn_lookup
# ---------------------------------------------------------------------------

@mcp.tool()
def hsn_lookup(hsn_code: str) -> dict:
    """Return the description and tax rates for an HSN code.

    Args:
        hsn_code: 4- or 8-digit HSN code (spaces/dots ignored).

    Returns:
        {
          "hsn_code":    str,
          "description": str,
          "gst_rate":    float,   # %
          "bcd_rate":    float,   # Basic Customs Duty %
          "sws_rate":    float,   # Social Welfare Surcharge on BCD %
        }
    """
    return lookup(hsn_code)


# ---------------------------------------------------------------------------
# Tool: gst_calc
# ---------------------------------------------------------------------------

@mcp.tool()
def gst_calc(
    hsn_code: str,
    assessable_value: float,
    supply_type: str = "inter_state",
) -> dict:
    """Calculate GST (IGST or CGST+SGST) on an assessable value.

    Args:
        hsn_code:         4- or 8-digit HSN code.
        assessable_value: Transaction value in INR (or same currency).
        supply_type:      "inter_state" → IGST only;
                          "intra_state" → CGST + SGST split.

    Returns:
        {
          "hsn_code":          str,
          "description":       str,
          "gst_rate":          float,
          "assessable_value":  float,
          "supply_type":       str,
          "igst":              float,
          "cgst":              float,
          "sgst":              float,
          "total_gst":         float,
        }
    """
    if assessable_value < 0:
        raise ValueError("assessable_value must be >= 0")
    supply_type = supply_type.lower().strip()
    if supply_type not in ("inter_state", "intra_state"):
        raise ValueError("supply_type must be 'inter_state' or 'intra_state'")

    entry = lookup(hsn_code)
    rate = entry["gst_rate"]  # e.g. 18.0
    total_gst = round(assessable_value * rate / 100, 2)

    if supply_type == "inter_state":
        igst, cgst, sgst = total_gst, 0.0, 0.0
    else:  # intra_state
        igst = 0.0
        half = round(total_gst / 2, 2)
        cgst = half
        sgst = round(total_gst - half, 2)  # absorbs any rounding penny

    return {
        "hsn_code": entry["hsn_code"],
        "description": entry["description"],
        "gst_rate": rate,
        "assessable_value": assessable_value,
        "supply_type": supply_type,
        "igst": igst,
        "cgst": cgst,
        "sgst": sgst,
        "total_gst": total_gst,
    }


# ---------------------------------------------------------------------------
# Tool: customs_calc
# ---------------------------------------------------------------------------

@mcp.tool()
def customs_calc(hsn_code: str, cif_value: float) -> dict:
    """Calculate BCD and Social Welfare Surcharge for an import.

    BCD = Basic Customs Duty on CIF value.
    SWS = 10 % on BCD (Social Welfare Surcharge).

    Args:
        hsn_code:  4- or 8-digit HSN code.
        cif_value: CIF value (Cost + Insurance + Freight) in INR.

    Returns:
        {
          "hsn_code":               str,
          "description":            str,
          "cif_value":              float,
          "bcd_rate":               float,
          "bcd_amount":             float,
          "sws_rate":               float,
          "sws_amount":             float,
          "total_customs":          float,
          "assessable_value_gst":   float,   # CIF + BCD + SWS
        }
    """
    if cif_value < 0:
        raise ValueError("cif_value must be >= 0")

    entry = lookup(hsn_code)
    bcd_rate = entry["bcd_rate"]
    sws_rate = entry["sws_rate"]

    bcd_amount = round(cif_value * bcd_rate / 100, 2)
    sws_amount = round(bcd_amount * sws_rate / 100, 2)
    total_customs = round(bcd_amount + sws_amount, 2)
    assessable_value_gst = round(cif_value + total_customs, 2)

    return {
        "hsn_code": entry["hsn_code"],
        "description": entry["description"],
        "cif_value": cif_value,
        "bcd_rate": bcd_rate,
        "bcd_amount": bcd_amount,
        "sws_rate": sws_rate,
        "sws_amount": sws_amount,
        "total_customs": total_customs,
        "assessable_value_gst": assessable_value_gst,
    }


# ---------------------------------------------------------------------------
# Tool: landed_cost_summary
# ---------------------------------------------------------------------------

@mcp.tool()
def landed_cost_summary(
    hsn_code: str,
    fob_value: float,
    freight: float,
    insurance: float,
    supply_type: str = "inter_state",
) -> dict:
    """Compute the full landed cost for an imported component.

    Sequence:
        CIF = FOB + freight + insurance
        BCD = CIF × bcd_rate
        SWS = BCD × sws_rate (10 %)
        Assessable value for GST = CIF + BCD + SWS
        IGST = assessable_value_gst × gst_rate  (inter-state import)
        Landed cost = CIF + BCD + SWS + IGST

    For intra-state domestic supply the IGST line is replaced with
    CGST + SGST; the total tax burden is identical.

    Args:
        hsn_code:    4- or 8-digit HSN code.
        fob_value:   FOB value in INR (or any consistent currency).
        freight:     Freight charges.
        insurance:   Insurance charges.
        supply_type: "inter_state" or "intra_state".

    Returns:
        Full breakdown dict with all intermediate values and landed_cost.
    """
    for label, val in (("fob_value", fob_value), ("freight", freight), ("insurance", insurance)):
        if val < 0:
            raise ValueError(f"{label} must be >= 0")

    entry = lookup(hsn_code)
    bcd_rate = entry["bcd_rate"]
    sws_rate = entry["sws_rate"]
    gst_rate = entry["gst_rate"]

    cif_value = round(fob_value + freight + insurance, 2)
    bcd_amount = round(cif_value * bcd_rate / 100, 2)
    sws_amount = round(bcd_amount * sws_rate / 100, 2)
    total_customs = round(bcd_amount + sws_amount, 2)
    assessable_value_gst = round(cif_value + total_customs, 2)
    total_gst = round(assessable_value_gst * gst_rate / 100, 2)

    supply_type = supply_type.lower().strip()
    if supply_type == "intra_state":
        half = round(total_gst / 2, 2)
        igst, cgst, sgst = 0.0, half, round(total_gst - half, 2)
    else:
        igst, cgst, sgst = total_gst, 0.0, 0.0

    landed_cost = round(cif_value + total_customs + total_gst, 2)

    return {
        "hsn_code": entry["hsn_code"],
        "description": entry["description"],
        "supply_type": supply_type,
        # --- input values ---
        "fob_value": fob_value,
        "freight": freight,
        "insurance": insurance,
        # --- customs ---
        "cif_value": cif_value,
        "bcd_rate": bcd_rate,
        "bcd_amount": bcd_amount,
        "sws_rate": sws_rate,
        "sws_amount": sws_amount,
        "total_customs": total_customs,
        # --- GST ---
        "assessable_value_gst": assessable_value_gst,
        "gst_rate": gst_rate,
        "igst": igst,
        "cgst": cgst,
        "sgst": sgst,
        "total_gst": total_gst,
        # --- summary ---
        "landed_cost": landed_cost,
    }


if __name__ == "__main__":
    mcp.run()
