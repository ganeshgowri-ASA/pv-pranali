"""Landed cost computation via karaveda MCP tools.

Formula: total = FOB + freight + insurance + BCD + SWS + IGST
Rates are fetched dynamically from karaveda MCP — never hard-coded.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LandedCostResult:
    fob: float
    freight: float
    insurance: float
    bcd: float
    sws: float
    igst: float
    total: float
    currency: str = "INR"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_csv(self) -> str:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(self.to_dict().keys()))
        w.writeheader()
        w.writerow(self.to_dict())
        return buf.getvalue()


async def compute_landed_cost(
    fob: float,
    freight: float,
    insurance: float,
    hsn_code: str,
    mcp_client: Any,
) -> LandedCostResult:
    """Compute landed cost using karaveda MCP customs_calc and gst_calc.

    Args:
        fob:        Free-On-Board value in INR.
        freight:    International freight cost in INR.
        insurance:  Marine insurance cost in INR.
        hsn_code:   HSN/ITC-HS code for the imported item.
        mcp_client: Karaveda MCP client exposing async call_tool().

    Returns:
        LandedCostResult with all duty components and grand total.
    """
    cif = fob + freight + insurance

    # Basic Customs Duty and Social Welfare Surcharge from karaveda
    customs_result = await mcp_client.call_tool(
        "customs_calc",
        {"hsn_code": hsn_code, "cif_value": cif, "currency": "INR"},
    )
    bcd = float(customs_result["bcd"])
    sws = float(customs_result["sws"])  # 10% of BCD per CBIC schedule

    # IGST is levied on assessable value = CIF + BCD + SWS
    assessable = cif + bcd + sws
    gst_result = await mcp_client.call_tool(
        "gst_calc",
        {
            "hsn_code": hsn_code,
            "taxable_value": assessable,
            "transaction_type": "import",
        },
    )
    igst = float(gst_result["igst"])

    total = cif + bcd + sws + igst

    return LandedCostResult(
        fob=fob,
        freight=freight,
        insurance=insurance,
        bcd=bcd,
        sws=sws,
        igst=igst,
        total=total,
    )
