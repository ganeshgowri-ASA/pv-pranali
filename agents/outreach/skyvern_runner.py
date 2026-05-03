"""Outreach agent: submit RFQ contact-form drafts to vendor websites (gate3)."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

_LOG_PATH = Path(__file__).parent / "submission_log.jsonl"
_TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class SubmissionResult:
    status: str          # "dry_run" | "submitted" | "error"
    url: str
    timestamp: str
    vendor: str
    detail: str = ""


class SkyvernRunner:
    """Submit RFQ drafts via Skyvern browser-automation.

    Dry-run mode is the default; pass ``dry_run=False`` (or use CLI ``--live``)
    only after gate-3 HITL approval.
    """

    def __init__(self, skyvern_api_url: str = "", api_key: str = "") -> None:
        self.skyvern_api_url = skyvern_api_url
        self.api_key = api_key
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=False,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit_rfq(
        self,
        vendor: dict[str, Any],
        rfq_data: dict[str, Any],
        dry_run: bool = True,
    ) -> SubmissionResult:
        """Render RFQ body and submit (or log-only in dry-run mode).

        Args:
            vendor: dict with keys ``name`` (str) and ``contact_url`` (str).
            rfq_data: dict passed into rfq_base.j2 template.
            dry_run: When True (default), log intent without submitting.

        Returns:
            SubmissionResult with status, url, and ISO timestamp.
        """
        url = vendor.get("contact_url", "")
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            body = self._render_template(vendor, rfq_data)
        except Exception as exc:
            result = SubmissionResult(
                status="error",
                url=url,
                timestamp=timestamp,
                vendor=vendor.get("name", ""),
                detail=f"template render failed: {exc}",
            )
            self._log(result)
            return result

        if dry_run:
            logger.info("[DRY-RUN] Would submit RFQ to %s — no request sent", url)
            result = SubmissionResult(
                status="dry_run",
                url=url,
                timestamp=timestamp,
                vendor=vendor.get("name", ""),
                detail=body,
            )
        else:
            result = self._live_submit(url, vendor, rfq_data, body, timestamp)

        self._log(result)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render_template(
        self, vendor: dict[str, Any], rfq_data: dict[str, Any]
    ) -> str:
        tmpl = self._jinja_env.get_template("rfq_base.j2")
        return tmpl.render(vendor=vendor, **rfq_data)

    def _live_submit(
        self,
        url: str,
        vendor: dict[str, Any],
        rfq_data: dict[str, Any],
        body: str,
        timestamp: str,
    ) -> SubmissionResult:
        """Call Skyvern API to fill and submit the vendor contact form."""
        try:
            import httpx  # runtime-only; not required in dry-run mode
        except ImportError:
            return SubmissionResult(
                status="error",
                url=url,
                timestamp=timestamp,
                vendor=vendor.get("name", ""),
                detail="httpx not installed; cannot submit live",
            )

        payload = {
            "url": url,
            "navigation_goal": "Fill and submit the RFQ contact form.",
            "data_extraction_goal": "Confirm form submission.",
            "navigation_payload": {
                "message": body,
                **rfq_data,
            },
        }
        headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}
        try:
            resp = httpx.post(
                f"{self.skyvern_api_url}/api/v1/tasks",
                json=payload,
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
            task_id = resp.json().get("task_id", "")
            return SubmissionResult(
                status="submitted",
                url=url,
                timestamp=timestamp,
                vendor=vendor.get("name", ""),
                detail=f"task_id={task_id}",
            )
        except Exception as exc:
            return SubmissionResult(
                status="error",
                url=url,
                timestamp=timestamp,
                vendor=vendor.get("name", ""),
                detail=str(exc),
            )

    def _log(self, result: SubmissionResult) -> None:
        entry = {
            "vendor": result.vendor,
            "url": result.url,
            "status": result.status,
            "timestamp": result.timestamp,
            "detail": result.detail,
        }
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        logger.info(
            "submission logged | vendor=%s status=%s url=%s",
            result.vendor,
            result.status,
            result.url,
        )


# ---------------------------------------------------------------------------
# CLI entry-point (python -m agents.outreach.skyvern_runner --live)
# ---------------------------------------------------------------------------

def _main() -> None:
    import argparse, sys

    parser = argparse.ArgumentParser(description="Submit RFQ via Skyvern")
    parser.add_argument("--live", action="store_true", help="Disable dry-run and submit for real")
    parser.add_argument("--vendor-url", required=True)
    parser.add_argument("--vendor-name", required=True)
    parser.add_argument("--product", required=True)
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--skyvern-url", default="http://localhost:8000")
    parser.add_argument("--api-key", default="")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    runner = SkyvernRunner(skyvern_api_url=args.skyvern_url, api_key=args.api_key)
    vendor = {"name": args.vendor_name, "contact_url": args.vendor_url}
    rfq_data = {"product": args.product, "quantity": args.quantity}

    result = runner.submit_rfq(vendor, rfq_data, dry_run=not args.live)
    print(json.dumps({"status": result.status, "url": result.url, "timestamp": result.timestamp}))
    sys.exit(0 if result.status != "error" else 1)


if __name__ == "__main__":
    _main()
