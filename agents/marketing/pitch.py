"""Pitch deck generator using vidyalaya MCP create_pptx tool."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_pitch_deck(
    product_name: str,
    product_description: str,
    output_dir: str = "/tmp",
    mcp_client: Any = None,
) -> str:
    """Generate a pitch deck PPTX for the given PV tester product.

    Args:
        product_name: Short name of the product (e.g. "EL Tester").
        product_description: One-paragraph product description.
        output_dir: Directory to save the generated PPTX.
        mcp_client: Optional pre-configured MCP client. If None, falls back
                    to python-pptx.

    Returns:
        Absolute path to the generated .pptx file.
    """
    slides = _build_slide_spec(product_name, product_description)
    output_path = str(
        Path(output_dir) / f"{product_name.replace(' ', '_')}_pitch.pptx"
    )

    if mcp_client is not None:
        result = mcp_client.call_tool(
            "mcp-vidyalaya",
            "create_pptx",
            {
                "slides": slides,
                "output_path": output_path,
                "template": "corporate",
            },
        )
        return result.get("path", output_path)

    return _build_pptx_fallback(slides, output_path)


def _build_slide_spec(product_name: str, description: str) -> list[dict]:
    return [
        {
            "layout": "title",
            "title": product_name,
            "subtitle": "PV Test Equipment — Product Pitch",
        },
        {
            "layout": "bullets",
            "title": "Product Overview",
            "bullets": [description],
        },
        {
            "layout": "bullets",
            "title": "Problem Statement",
            "bullets": [
                "Manual PV panel testing is slow and error-prone",
                "Existing equipment is expensive and India-import constrained",
                "No integrated BoM-to-proposal pipeline exists",
            ],
        },
        {
            "layout": "bullets",
            "title": "Our Solution",
            "bullets": [
                f"{product_name}: built from India-sourced components",
                "End-to-end automated proposal generation",
                "Open architecture via MCP + LangGraph",
            ],
        },
        {
            "layout": "bullets",
            "title": "Market Opportunity",
            "bullets": [
                "India PV installation: ~18 GW/year (2025)",
                "Growing demand for IEC-compliant test gear",
                "Captive R&D labs + EPC contractors as primary buyers",
            ],
        },
        {
            "layout": "bullets",
            "title": "Business Model",
            "bullets": [
                "Hardware kit sales (manufactured-to-order)",
                "Annual calibration + service contracts",
                "Software-as-a-service: automated proposal engine",
            ],
        },
        {
            "layout": "bullets",
            "title": "Traction & Roadmap",
            "bullets": [
                "Phase 0–2 complete: MCP infrastructure + BoM automation",
                "Q3 2026: First EL Tester prototype delivery",
                "Q4 2026: Sun Simulator Class AAA GA",
            ],
        },
        {
            "layout": "closing",
            "title": "Thank You",
            "subtitle": "Contact: ganeshgowri@example.com",
        },
    ]


def _build_pptx_fallback(slides: list[dict], output_path: str) -> str:
    """Build PPTX with python-pptx when MCP is unavailable."""
    try:
        from pptx import Presentation
    except ImportError as exc:
        raise RuntimeError(
            "python-pptx is required for fallback. Install: pip install python-pptx"
        ) from exc

    prs = Presentation()
    title_layout = prs.slide_layouts[0]
    body_layout = prs.slide_layouts[1]

    for spec in slides:
        if spec.get("layout") in ("title", "closing"):
            slide = prs.slides.add_slide(title_layout)
            slide.shapes.title.text = spec.get("title", "")
            if len(slide.placeholders) > 1:
                slide.placeholders[1].text = spec.get("subtitle", "")
        else:
            slide = prs.slides.add_slide(body_layout)
            slide.shapes.title.text = spec.get("title", "")
            tf = slide.placeholders[1].text_frame
            tf.clear()
            for bullet in spec.get("bullets", []):
                p = tf.add_paragraph()
                p.text = bullet
                p.level = 0

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)
    return output_path
