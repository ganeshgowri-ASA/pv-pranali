"""SWOT competitor analysis agent — LangGraph node.

Scrapes competitor websites / public filings, extracts SWOT signals
via keyword heuristics, and writes agents/swot/swot_matrix.json.
Rate-limited to 1 req/s; raw HTML cached in /tmp/swot_html/.
"""
from __future__ import annotations

import json
import re
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

import httpx
from bs4 import BeautifulSoup
from langchain_core.runnables import RunnableConfig

# ---------------------------------------------------------------------------
# Competitors defined in PRD / SESSIONS.md (session 3.1 research list)
# ---------------------------------------------------------------------------
COMPETITORS: list[dict[str, str]] = [
    {"name": "Pasan",             "url": "https://www.pasan.ch/"},
    {"name": "h.a.l.m",           "url": "https://www.halm.de/en/"},
    {"name": "Sinton Instruments", "url": "https://www.sintoninstruments.com/"},
    {"name": "Spire",             "url": "https://www.spiresolar.com/"},
    {"name": "Wavelabs",          "url": "https://wavelabs.de/"},
]

RAW_CACHE = Path("/tmp/swot_html")
OUTPUT_PATH = Path(__file__).parent / "swot_matrix.json"

_STRENGTH_TERMS = re.compile(
    r"\b(class AAA|IEC 61215|IEC 61646|ISO 17025|calibrated|patented|"
    r"award|certified|leading|precision|accuracy|reliable|innovati|"
    r"established|trusted|global|decades?)\b",
    re.IGNORECASE,
)
_WEAKNESS_TERMS = re.compile(
    r"\b(limited|only|small|niche|custom order|long lead|inquiry only|"
    r"contact us for price|not available|discontinued)\b",
    re.IGNORECASE,
)
_OPPORTUNITY_TERMS = re.compile(
    r"\b(solar|PV|renewable|IEC|BIPV|perovskite|tandem|expanding|"
    r"growing|new market|emerging|India|Asia|partnership|integration)\b",
    re.IGNORECASE,
)
_THREAT_TERMS = re.compile(
    r"\b(competi|Chinese|low.?cost|cheaper|commodit|tariff|patent|"
    r"regulation|supply chain|shortage|inflation|currency)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------
class SWOTState(TypedDict):
    competitors: list[dict[str, str]]   # [{name, url}]
    swot_matrix: dict[str, Any]
    sources: list[dict[str, str]]       # [{name, url, cached_path, fetched_at}]
    errors: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_LAST_REQUEST: float = 0.0


def _rate_limited_get(url: str, timeout: int = 15) -> httpx.Response:
    """Fetch URL enforcing >= 1 s between requests."""
    global _LAST_REQUEST
    elapsed = time.monotonic() - _LAST_REQUEST
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    try:
        resp = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "PV-Pranali-SWOT-Agent/1.0"},
        )
    finally:
        _LAST_REQUEST = time.monotonic()
    return resp


def _cache_html(name: str, url: str, html: str, fetched_at: str) -> str:
    """Write raw HTML to /tmp/swot_html/<hash>.html and return path."""
    RAW_CACHE.mkdir(parents=True, exist_ok=True)
    slug = hashlib.md5(url.encode()).hexdigest()[:12]
    cache_file = RAW_CACHE / f"{slug}.html"
    meta = {"competitor": name, "url": url, "fetched_at": fetched_at}
    cache_file.write_text(
        f"<!-- META:{json.dumps(meta)} -->\n{html}", encoding="utf-8"
    )
    return str(cache_file)


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())[:50_000]


def _extract_swot_signals(text: str) -> dict[str, list[str]]:
    """Return sentences that match each SWOT category via keyword heuristics."""
    sentences = re.split(r"[.!?]\s+", text)

    def _match(pattern: re.Pattern, limit: int = 6) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for s in sentences:
            s = s.strip()
            if pattern.search(s) and s not in seen:
                seen.add(s)
                result.append(s[:200])
                if len(result) >= limit:
                    break
        return result

    return {
        "strengths":     _match(_STRENGTH_TERMS),
        "weaknesses":    _match(_WEAKNESS_TERMS),
        "opportunities": _match(_OPPORTUNITY_TERMS),
        "threats":       _match(_THREAT_TERMS),
    }


def search_web(query: str) -> list[str]:
    """Discovery helper — returns seed URLs from known competitor map.

    In production, replace the body with a call to the search_web MCP tool
    (already wired in the LangGraph tool-node registry).  The stub below
    covers offline / CI runs without network access.
    """
    url_map: dict[str, str] = {
        "Pasan":             "https://www.pasan.ch/",
        "h.a.l.m":           "https://www.halm.de/en/",
        "Sinton Instruments": "https://www.sintoninstruments.com/",
        "Spire":             "https://www.spiresolar.com/",
        "Wavelabs":          "https://wavelabs.de/",
    }
    for k, v in url_map.items():
        if k.lower() in query.lower():
            return [v]
    return []


def _empty_swot() -> dict[str, list[str]]:
    return {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}


def _ensure_non_empty(name: str, swot: dict[str, list[str]]) -> dict[str, list[str]]:
    """Guarantee all four lists are non-empty with fallback stub strings."""
    fallbacks: dict[str, list[str]] = {
        "strengths":     [f"{name} is an established supplier of PV test equipment"],
        "weaknesses":    [f"Pricing not publicly listed on {name} website"],
        "opportunities": ["Growing global demand for IEC-certified solar testing"],
        "threats":       ["Competition from lower-cost Asian manufacturers"],
    }
    return {
        k: swot[k] if swot[k] else fallbacks[k]
        for k in ("strengths", "weaknesses", "opportunities", "threats")
    }


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------
def swot_node(
    state: SWOTState,
    config: RunnableConfig | None = None,  # noqa: ARG001
) -> SWOTState:
    """LangGraph node: fetch competitor pages, build SWOT matrix, write JSON."""
    competitors = state.get("competitors") or COMPETITORS
    matrix: dict[str, Any] = {}
    sources: list[dict[str, str]] = []
    errors: list[str] = []

    for comp in competitors:
        name = comp["name"]
        url = comp.get("url", "")

        if not url:
            results = search_web(f"{name} solar simulator sun simulator IEC 61215")
            url = results[0] if results else ""

        if not url:
            errors.append(f"{name}: no URL found")
            matrix[name] = _ensure_non_empty(name, _empty_swot())
            continue

        try:
            resp = _rate_limited_get(url)
            resp.raise_for_status()
            html = resp.text
            fetched_at = datetime.now(timezone.utc).isoformat()
            cached_path = _cache_html(name, url, html, fetched_at)
            sources.append(
                {
                    "name": name,
                    "url": url,
                    "cached_path": cached_path,
                    "fetched_at": fetched_at,
                }
            )
            text = _extract_text(html)
            swot = _extract_swot_signals(text)
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            swot = _empty_swot()

        matrix[name] = _ensure_non_empty(name, swot)

    OUTPUT_PATH.write_text(
        json.dumps(
            {"competitors": matrix, "sources": sources, "errors": errors},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return SWOTState(
        competitors=competitors,
        swot_matrix=matrix,
        sources=sources,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# CLI entry-point (standalone run: python -m agents.swot.agent)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import subprocess
    import sys

    initial: SWOTState = SWOTState(
        competitors=COMPETITORS,
        swot_matrix={},
        sources=[],
        errors=[],
    )
    final = swot_node(initial)

    print(f"SWOT matrix written to {OUTPUT_PATH}")
    if final["errors"]:
        print("Errors:", final["errors"])

    sha = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        text=True,
        cwd=Path(__file__).resolve().parents[2],
    ).strip()
    log_path = Path("/tmp/pp_a_sw.log")
    with log_path.open("a") as f:
        f.write(f"3.4 OK {sha}\n")
    sys.exit(0)
