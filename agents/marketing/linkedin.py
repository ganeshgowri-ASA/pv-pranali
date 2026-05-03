"""LinkedIn draft post generator via Unipile API."""
from __future__ import annotations

import os

_MAX_LI_CHARS = 3000


def draft_linkedin_post(
    product_name: str,
    key_benefit: str = "",
    publish: bool = False,
    unipile_dsn: str | None = None,
) -> str:
    """Draft a LinkedIn post for the product.

    Args:
        product_name: Name of the PV tester product.
        key_benefit: Primary value proposition sentence.
        publish: If True, sends via Unipile API (HITL gate 4 must be passed).
        unipile_dsn: Override for the UNIPILE_DSN env var.

    Returns:
        Draft post text, always under 3000 chars.

    Raises:
        RuntimeError: If publish=True and UNIPILE_DSN is unset.
    """
    key_benefit = key_benefit or (
        f"{product_name} enables precise, IEC-compliant PV panel testing "
        "with a fully India-sourced BoM — cutting lead times by 60%."
    )

    post = _compose_post(product_name, key_benefit)
    assert len(post) < _MAX_LI_CHARS, f"Post exceeds {_MAX_LI_CHARS} chars"

    if publish:
        _send_via_unipile(post, unipile_dsn)

    return post


def _compose_post(product_name: str, key_benefit: str) -> str:
    return (
        f"Introducing the {product_name} — built for India's fast-growing solar market.\n\n"
        f"{key_benefit}\n\n"
        "Why it matters:\n"
        "✅ IEC 61215 / IEC 61853 compliant out of the box\n"
        "✅ Sourced from Mouser, DigiKey & Robu India — no import delays\n"
        "✅ Open-architecture: MCP + LangGraph pipeline you can audit and extend\n"
        "✅ Automated proposal generation: intent → pitch deck in < 6 hours\n\n"
        f"We designed {product_name} as part of the PV-Pranali multi-agent system — "
        "a platform that takes a single line of intent and produces a complete customer "
        "proposal, BoM, CAD, PCB, and marketing collateral.\n\n"
        "Interested in a demo or want to collaborate? Drop a comment or DM me.\n\n"
        "#SolarEnergy #PVTesting #MadeInIndia #OpenSource #AIAgents #LangGraph #MCP"
    )


def _send_via_unipile(post: str, dsn: str | None) -> None:
    dsn = dsn or os.environ.get("UNIPILE_DSN")
    if not dsn:
        raise RuntimeError(
            "UNIPILE_DSN environment variable is not set. "
            "Cannot publish without a valid Unipile DSN."
        )

    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError(
            "httpx is required for publishing. Install: pip install httpx"
        ) from exc

    resp = httpx.post(
        f"{dsn}/api/v1/linkedin/posts",
        json={"text": post},
        timeout=30,
    )
    resp.raise_for_status()
