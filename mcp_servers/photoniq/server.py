"""PhotonIQ MCP server — BOM impact analysis and cost-to-manufacture estimation.

Tools exposed:
  bom_impact        – cost each BOM line via Mouser/DigiKey, return INR totals
  ctm_estimate      – add overhead percentages (PRD §G5 / §KPI) on top of BOM cost
  price_lookup      – query live Mouser/DigiKey price for a single part
  availability_check – return stock count and lead-time for a part

Required env vars:
  MOUSER_API_KEY   – Mouser Search API key
  DIGIKEY_CLIENT_ID, DIGIKEY_CLIENT_SECRET – DigiKey OAuth2 credentials
  DIGIKEY_ACCESS_TOKEN – pre-obtained bearer token (or set above pair for auto-refresh)

Optional:
  USD_TO_INR       – static override exchange rate (e.g. "83.5")
                     When absent the server fetches live rate from open.er-api.com.

Run: python -m mcp_servers.photoniq.server
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# CTM overhead percentages as defined in PRD (Section 5 / G5)
# All values are applied sequentially on top of component cost.
# ---------------------------------------------------------------------------
CTM_OVERHEADS: dict[str, float] = {
    "assembly_labor_pct": 15.0,       # PCB assembly + wiring labor
    "manufacturing_overhead_pct": 20.0,  # facility, equipment depreciation
    "quality_testing_pct": 8.0,       # IEC 61215 / IEC 62108 test runs
    "gst_pct": 18.0,                  # India GST on manufactured goods
    "profit_margin_pct": 15.0,        # target margin
}

MOUSER_SEARCH_URL = "https://api.mouser.com/api/v1/search/keyword"
DIGIKEY_SEARCH_URL = "https://api.digikey.com/products/v4/search/keyword"
ER_API_URL = "https://open.er-api.com/v6/latest/USD"

mcp = FastMCP("photoniq")


# ---------------------------------------------------------------------------
# Exchange rate helpers
# ---------------------------------------------------------------------------

_rate_cache: dict[str, Any] = {"rate": None, "fetched_at": 0.0}
_RATE_TTL = 3600  # seconds


def _inr_rate() -> tuple[float, str]:
    """Return (usd_to_inr_rate, iso_timestamp). Caches for 1 h."""
    static = os.getenv("USD_TO_INR")
    if static:
        return float(static), datetime.now(timezone.utc).isoformat()

    now = time.monotonic()
    if _rate_cache["rate"] and now - _rate_cache["fetched_at"] < _RATE_TTL:
        return _rate_cache["rate"], _rate_cache["ts"]

    try:
        resp = httpx.get(ER_API_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rate = float(data["rates"]["INR"])
    except Exception:
        rate = 83.5  # fallback if API unreachable

    ts = datetime.now(timezone.utc).isoformat()
    _rate_cache.update({"rate": rate, "fetched_at": now, "ts": ts})
    return rate, ts


# ---------------------------------------------------------------------------
# Supplier API helpers
# ---------------------------------------------------------------------------

def _mouser_price(part_number: str, qty: int = 1) -> dict[str, Any] | None:
    """Return cheapest Mouser price break for part_number at qty."""
    api_key = os.getenv("MOUSER_API_KEY", "")
    if not api_key:
        return None
    payload = {
        "SearchByKeywordRequest": {
            "keyword": part_number,
            "records": 5,
            "startingRecord": 0,
            "searchOptions": "InStock",
            "searchWithYourSignUpLanguage": "false",
        }
    }
    try:
        resp = httpx.post(
            MOUSER_SEARCH_URL,
            params={"apiKey": api_key},
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        parts = resp.json().get("SearchResults", {}).get("Parts", [])
        if not parts:
            return None
        part = parts[0]
        breaks = part.get("PriceBreaks", [])
        unit_price_usd = None
        for brk in sorted(breaks, key=lambda b: int(b.get("Quantity", 0))):
            if int(brk.get("Quantity", 0)) <= qty:
                raw = brk.get("Price", "").replace("$", "").replace(",", "")
                try:
                    unit_price_usd = float(raw)
                except ValueError:
                    pass
        if unit_price_usd is None and breaks:
            raw = breaks[0].get("Price", "").replace("$", "").replace(",", "")
            try:
                unit_price_usd = float(raw)
            except ValueError:
                pass
        return {
            "source": "mouser",
            "part_number": part.get("ManufacturerPartNumber", part_number),
            "description": part.get("Description", ""),
            "unit_price_usd": unit_price_usd,
            "stock": int(part.get("AvailabilityInStock", 0) or 0),
            "lead_time_weeks": part.get("LeadTime", "N/A"),
        }
    except Exception:
        return None


def _digikey_price(part_number: str, qty: int = 1) -> dict[str, Any] | None:
    """Return DigiKey price for part_number at qty."""
    token = os.getenv("DIGIKEY_ACCESS_TOKEN", "")
    client_id = os.getenv("DIGIKEY_CLIENT_ID", "")
    if not token or not client_id:
        return None
    headers = {
        "Authorization": f"Bearer {token}",
        "X-DIGIKEY-Client-Id": client_id,
        "X-DIGIKEY-Locale-Site": "IN",
        "X-DIGIKEY-Locale-Currency": "USD",
        "Content-Type": "application/json",
    }
    payload = {"Keywords": part_number, "RecordCount": 5, "RecordStartPos": 0}
    try:
        resp = httpx.post(
            DIGIKEY_SEARCH_URL,
            headers=headers,
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        products = resp.json().get("Products", [])
        if not products:
            return None
        prod = products[0]
        breaks = prod.get("StandardPricing", [])
        unit_price_usd = None
        for brk in sorted(breaks, key=lambda b: b.get("BreakQuantity", 0)):
            if brk.get("BreakQuantity", 0) <= qty:
                unit_price_usd = brk.get("UnitPrice")
        if unit_price_usd is None and breaks:
            unit_price_usd = breaks[0].get("UnitPrice")
        return {
            "source": "digikey",
            "part_number": prod.get("ManufacturerPartNumber", part_number),
            "description": prod.get("ProductDescription", ""),
            "unit_price_usd": unit_price_usd,
            "stock": prod.get("QuantityAvailable", 0),
            "lead_time_weeks": prod.get("ManufacturerLeadWeeks", "N/A"),
        }
    except Exception:
        return None


def _best_price(part_number: str, qty: int = 1) -> dict[str, Any]:
    """Try Mouser then DigiKey; return best (lowest) unit price result."""
    candidates = [
        r for r in [_mouser_price(part_number, qty), _digikey_price(part_number, qty)]
        if r and r.get("unit_price_usd") is not None
    ]
    if not candidates:
        return {
            "source": "unavailable",
            "part_number": part_number,
            "description": "",
            "unit_price_usd": None,
            "stock": 0,
            "lead_time_weeks": "N/A",
        }
    return min(candidates, key=lambda c: c["unit_price_usd"])


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@mcp.tool()
def bom_impact(
    bom: list[dict[str, Any]],
    preferred_source: str = "auto",
) -> dict[str, Any]:
    """Compute total and per-line BOM cost in INR using live supplier pricing.

    Args:
        bom: List of line items. Each item must have:
             - part_number (str)  – manufacturer or distributor part number
             - qty (int)          – quantity required
             Optional per line:
             - description (str)  – human label (passed through)
             - reference (str)    – schematic ref (e.g. "C1, R3")
        preferred_source: "mouser", "digikey", or "auto" (cheapest, default).

    Returns:
        {
          "currency": "INR",
          "exchange_rate_usd_to_inr": float,
          "exchange_rate_timestamp": str (ISO-8601),
          "total_inr": float,
          "lines": [
            {
              "part_number": str,
              "description": str,
              "reference": str,
              "qty": int,
              "source": str,
              "unit_price_usd": float | None,
              "unit_price_inr": float | None,
              "line_total_inr": float | None,
              "stock": int,
              "lead_time_weeks": str,
            }, ...
          ],
          "lines_with_missing_price": int,
        }
    """
    rate, rate_ts = _inr_rate()
    lines_out: list[dict[str, Any]] = []
    total_inr = 0.0
    missing = 0

    for item in bom:
        pn = str(item.get("part_number", "")).strip()
        qty = int(item.get("qty", 1))

        if preferred_source == "mouser":
            result = _mouser_price(pn, qty) or _best_price(pn, qty)
        elif preferred_source == "digikey":
            result = _digikey_price(pn, qty) or _best_price(pn, qty)
        else:
            result = _best_price(pn, qty)

        usd = result.get("unit_price_usd")
        if usd is not None:
            unit_inr = usd * rate
            line_inr = unit_inr * qty
            total_inr += line_inr
        else:
            unit_inr = None
            line_inr = None
            missing += 1

        lines_out.append({
            "part_number": result["part_number"],
            "description": item.get("description", result.get("description", "")),
            "reference": item.get("reference", ""),
            "qty": qty,
            "source": result["source"],
            "unit_price_usd": usd,
            "unit_price_inr": round(unit_inr, 4) if unit_inr is not None else None,
            "line_total_inr": round(line_inr, 2) if line_inr is not None else None,
            "stock": result.get("stock", 0),
            "lead_time_weeks": result.get("lead_time_weeks", "N/A"),
        })

    return {
        "currency": "INR",
        "exchange_rate_usd_to_inr": rate,
        "exchange_rate_timestamp": rate_ts,
        "total_inr": round(total_inr, 2),
        "lines": lines_out,
        "lines_with_missing_price": missing,
    }


@mcp.tool()
def ctm_estimate(
    bom: list[dict[str, Any]],
    overrides: dict[str, float] | None = None,
    preferred_source: str = "auto",
) -> dict[str, Any]:
    """Cost-to-manufacture = BOM cost + PRD-defined overhead percentages.

    Overheads applied (each % on running subtotal):
      assembly_labor_pct     15 %  (PCB + wiring labor)
      manufacturing_overhead_pct  20 %  (facility / equipment)
      quality_testing_pct     8 %  (IEC test runs)
      gst_pct               18 %  (India GST)
      profit_margin_pct      15 %  (target margin)

    Args:
        bom:              Same format as bom_impact.
        overrides:        Optional dict of {overhead_key: pct} to override defaults.
        preferred_source: "mouser", "digikey", or "auto".

    Returns:
        {
          "currency": "INR",
          "exchange_rate_usd_to_inr": float,
          "exchange_rate_timestamp": str,
          "bom_cost_inr": float,
          "overheads_applied": {overhead_key: pct, ...},
          "overhead_breakdown_inr": {overhead_key: inr_amount, ...},
          "ctm_inr": float,
          "bom_detail": <same as bom_impact output>,
        }
    """
    bom_result = bom_impact(bom, preferred_source=preferred_source)
    overheads = {**CTM_OVERHEADS, **(overrides or {})}

    running = bom_result["total_inr"]
    breakdown: dict[str, float] = {}
    for key, pct in overheads.items():
        delta = running * (pct / 100.0)
        breakdown[key] = round(delta, 2)
        running += delta

    return {
        "currency": "INR",
        "exchange_rate_usd_to_inr": bom_result["exchange_rate_usd_to_inr"],
        "exchange_rate_timestamp": bom_result["exchange_rate_timestamp"],
        "bom_cost_inr": bom_result["total_inr"],
        "overheads_applied": overheads,
        "overhead_breakdown_inr": breakdown,
        "ctm_inr": round(running, 2),
        "bom_detail": bom_result,
    }


@mcp.tool()
def price_lookup(
    part_number: str,
    qty: int = 1,
    source: str = "auto",
) -> dict[str, Any]:
    """Fetch live unit price for a single part from Mouser or DigiKey.

    Args:
        part_number: Manufacturer or distributor part number.
        qty:         Quantity (used to select the correct price break).
        source:      "mouser", "digikey", or "auto" (cheapest).

    Returns:
        {
          "part_number": str,
          "description": str,
          "source": str,
          "qty": int,
          "unit_price_usd": float | None,
          "unit_price_inr": float | None,
          "currency": "INR",
          "exchange_rate_usd_to_inr": float,
          "exchange_rate_timestamp": str,
          "stock": int,
          "lead_time_weeks": str,
        }
    """
    rate, rate_ts = _inr_rate()

    if source == "mouser":
        result = _mouser_price(part_number, qty) or _best_price(part_number, qty)
    elif source == "digikey":
        result = _digikey_price(part_number, qty) or _best_price(part_number, qty)
    else:
        result = _best_price(part_number, qty)

    usd = result.get("unit_price_usd")
    return {
        "part_number": result["part_number"],
        "description": result.get("description", ""),
        "source": result["source"],
        "qty": qty,
        "unit_price_usd": usd,
        "unit_price_inr": round(usd * rate, 4) if usd is not None else None,
        "currency": "INR",
        "exchange_rate_usd_to_inr": rate,
        "exchange_rate_timestamp": rate_ts,
        "stock": result.get("stock", 0),
        "lead_time_weeks": result.get("lead_time_weeks", "N/A"),
    }


@mcp.tool()
def availability_check(
    part_number: str,
    required_qty: int = 1,
    source: str = "auto",
) -> dict[str, Any]:
    """Return stock count and lead time for a part from Mouser or DigiKey.

    Args:
        part_number:  Manufacturer or distributor part number.
        required_qty: Quantity you need (used to determine if stock is sufficient).
        source:       "mouser", "digikey", or "auto".

    Returns:
        {
          "part_number": str,
          "description": str,
          "source": str,
          "stock": int,
          "lead_time_weeks": str,
          "required_qty": int,
          "in_stock": bool,
          "shortfall": int,  # 0 if stock >= required_qty
        }
    """
    if source == "mouser":
        result = _mouser_price(part_number, required_qty) or _best_price(part_number, required_qty)
    elif source == "digikey":
        result = _digikey_price(part_number, required_qty) or _best_price(part_number, required_qty)
    else:
        result = _best_price(part_number, required_qty)

    stock = result.get("stock", 0)
    shortfall = max(0, required_qty - stock)
    return {
        "part_number": result["part_number"],
        "description": result.get("description", ""),
        "source": result["source"],
        "stock": stock,
        "lead_time_weeks": result.get("lead_time_weeks", "N/A"),
        "required_qty": required_qty,
        "in_stock": shortfall == 0,
        "shortfall": shortfall,
    }


if __name__ == "__main__":
    mcp.run()
