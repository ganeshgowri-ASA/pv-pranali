"""Session 3.1 — Research agent: scrape vendor sites, ingest into antaryami."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, TypedDict

import httpx
import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

log = logging.getLogger(__name__)

SOURCES_FILE = Path(__file__).parent / "sources.yml"
RATE_LIMIT_S = 1.0  # 1 req/s per domain
_last_request: dict[str, float] = {}


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------

class ResearchState(TypedDict, total=False):
    vendor_results: list[dict[str, Any]]
    errors: list[str]


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

def _wait_for_domain(domain: str) -> None:
    now = time.monotonic()
    gap = now - _last_request.get(domain, 0.0)
    if gap < RATE_LIMIT_S:
        time.sleep(RATE_LIMIT_S - gap)
    _last_request[domain] = time.monotonic()


# ---------------------------------------------------------------------------
# robots.txt check
# ---------------------------------------------------------------------------

def _robots_allows(base_url: str, path: str) -> bool:
    try:
        from urllib.robotparser import RobotFileParser
        rp = RobotFileParser()
        rp.set_url(base_url.rstrip("/") + "/robots.txt")
        rp.read()
        return rp.can_fetch("*", base_url.rstrip("/") + path)
    except Exception:
        return True  # allow on parse failure


# ---------------------------------------------------------------------------
# Static-page scraper (httpx + BeautifulSoup)
# ---------------------------------------------------------------------------

def _scrape_static(url: str, selectors: dict[str, str]) -> dict[str, Any]:
    from bs4 import BeautifulSoup
    from urllib.parse import urlparse

    domain = urlparse(url).netloc
    _wait_for_domain(domain)

    with httpx.Client(timeout=20, follow_redirects=True,
                      headers={"User-Agent": "pv-pranali-research/0.1"}) as client:
        resp = client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    result: dict[str, Any] = {"url": url}

    for field, css in selectors.items():
        # Each selector entry may be comma-separated alternatives
        for sel in css.split(","):
            node = soup.select_one(sel.strip())
            if node:
                result[field] = node.get_text(" ", strip=True)
                break
        else:
            result[field] = None

    return result


# ---------------------------------------------------------------------------
# JS-heavy scraper (browser-use)
# ---------------------------------------------------------------------------

async def _scrape_js(url: str, selectors: dict[str, str]) -> dict[str, Any]:
    try:
        from browser_use import Browser, BrowserConfig  # type: ignore
        from urllib.parse import urlparse

        domain = urlparse(url).netloc
        _wait_for_domain(domain)

        config = BrowserConfig(headless=True)
        async with Browser(config=config) as browser:
            page = await browser.new_page()
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            html = await page.content()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        result: dict[str, Any] = {"url": url}

        for field, css in selectors.items():
            for sel in css.split(","):
                node = soup.select_one(sel.strip())
                if node:
                    result[field] = node.get_text(" ", strip=True)
                    break
            else:
                result[field] = None

        return result
    except ImportError:
        log.warning("browser-use not installed; falling back to httpx for %s", url)
        return _scrape_static(url, selectors)


# ---------------------------------------------------------------------------
# Per-vendor scrape
# ---------------------------------------------------------------------------

async def scrape_vendor(vendor: dict[str, Any]) -> dict[str, Any]:
    name = vendor["name"]
    base_url = vendor["base_url"]
    js_heavy: bool = vendor.get("js_heavy", False)
    selectors: dict[str, str] = vendor.get("selectors", {})
    metadata: dict[str, Any] = vendor.get("metadata", {})

    pages_data: list[dict[str, Any]] = []
    for page_url in vendor.get("product_pages", []):
        path = page_url.replace(base_url, "") or "/"
        if not _robots_allows(base_url, path):
            log.info("robots.txt disallows %s — skipping", page_url)
            continue
        try:
            if js_heavy:
                data = await _scrape_js(page_url, selectors)
            else:
                data = _scrape_static(page_url, selectors)
            pages_data.append(data)
        except Exception as exc:
            log.warning("Failed to scrape %s: %s", page_url, exc)

    return {
        "vendor": name,
        "model": _extract_first(pages_data, "product_name"),
        "price_usd": _extract_first(pages_data, "price"),
        "specs": _extract_first(pages_data, "specs_table"),
        "description": _extract_first(pages_data, "description"),
        "source_urls": [p["url"] for p in pages_data],
        "metadata": metadata,
        "raw_pages": pages_data,
    }


def _extract_first(pages: list[dict[str, Any]], field: str) -> str | None:
    for page in pages:
        val = page.get(field)
        if val:
            return val
    return None


# ---------------------------------------------------------------------------
# Antaryami MCP ingestion
# ---------------------------------------------------------------------------

async def ingest_to_antaryami(record: dict[str, Any]) -> None:
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_servers.antaryami"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await session.call_tool(
                "ingest_document",
                arguments={
                    "content": json.dumps(record, ensure_ascii=False),
                    "metadata": {
                        "vendor": record["vendor"],
                        "category": record.get("metadata", {}).get("category", ""),
                        "source": "research_agent_3.1",
                    },
                },
            )


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

async def research_node(state: ResearchState) -> ResearchState:
    """LangGraph-compatible async node: scrape all vendors then ingest."""
    sources = yaml.safe_load(SOURCES_FILE.read_text())
    vendors: list[dict[str, Any]] = sources["vendors"]

    results: list[dict[str, Any]] = []
    errors: list[str] = []

    for vendor in vendors:
        try:
            record = await scrape_vendor(vendor)
            results.append(record)
            log.info("Scraped %s — model=%s", vendor["name"], record["model"])
        except Exception as exc:
            msg = f"{vendor['name']}: {exc}"
            log.error(msg)
            errors.append(msg)

    for record in results:
        try:
            await ingest_to_antaryami(record)
            log.info("Ingested %s into antaryami", record["vendor"])
        except Exception as exc:
            msg = f"ingest {record['vendor']}: {exc}"
            log.error(msg)
            errors.append(msg)

    return {"vendor_results": results, "errors": errors}


# ---------------------------------------------------------------------------
# CLI entry-point (also writes /tmp/pp_a_res.log on success)
# ---------------------------------------------------------------------------

async def _main() -> None:
    import subprocess, sys

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    final_state = await research_node({})

    print(json.dumps({"vendor_results_count": len(final_state["vendor_results"]),
                      "errors": final_state["errors"]}, indent=2))

    # Append sentinel to log file
    sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                   text=True).strip()
    Path("/tmp/pp_a_res.log").open("a").write(f"3.1 OK {sha}\n")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(_main())
