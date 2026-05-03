"""India availability filter and ranker for BOM candidates."""
from typing import Any

USD_TO_INR = 83.5


def filter_for_india(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filter parts for India availability and return ranked by price_inr ascending.

    Rules:
    - Mouser: stock_india > 0 (in Mouser India warehouse)
    - DigiKey: ships_to_india=True AND lead_time_days < 30

    Returns list of dicts with at minimum:
      part_number, source, price_inr, price_usd, stock_india, lead_time_days
    """
    eligible: list[dict[str, Any]] = []

    for part in parts:
        source = part.get("source", "")
        if source == "mouser":
            if (part.get("stock_india") or 0) > 0:
                eligible.append(_ensure_inr(part))
        elif source == "digikey":
            lead = part.get("lead_time_days", 999)
            if part.get("ships_to_india", False) and (lead is not None) and lead < 30:
                eligible.append(_ensure_inr(part))

    return sorted(
        eligible,
        key=lambda p: p["price_inr"] if p.get("price_inr", 0) > 0 else float("inf"),
    )


def _ensure_inr(part: dict[str, Any]) -> dict[str, Any]:
    if not part.get("price_inr") and part.get("price_usd"):
        return {**part, "price_inr": round(part["price_usd"] * USD_TO_INR, 2)}
    return part
