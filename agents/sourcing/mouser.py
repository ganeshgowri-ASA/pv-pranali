"""Mouser Electronics API client."""
import os
import requests
from typing import Any

MOUSER_API_BASE = "https://api.mouser.com/api/v1"
USD_TO_INR = 83.5


class MouserClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["MOUSER_API_KEY"]
        self.session = requests.Session()

    def search_parts(self, keyword: str, records: int = 10) -> list[dict[str, Any]]:
        url = f"{MOUSER_API_BASE}/search/keyword"
        payload = {
            "SearchByKeywordRequest": {
                "keyword": keyword,
                "records": records,
                "startingRecord": 0,
                "searchOptions": "",
                "searchWithYourSignUpLanguage": "",
            }
        }
        resp = self.session.post(
            url,
            json=payload,
            params={"apiKey": self.api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = data.get("SearchResults", {}).get("Parts", []) or []
        return [self._normalize(p) for p in parts]

    def get_price_breaks(self, mouser_part_number: str) -> list[dict[str, Any]]:
        parts = self.search_parts(mouser_part_number, records=1)
        if not parts:
            return []
        return parts[0].get("price_breaks", [])

    @staticmethod
    def _normalize(part: dict) -> dict[str, Any]:
        price_breaks = []
        for pb in part.get("PriceBreaks", []) or []:
            try:
                price_usd = float(
                    pb.get("Price", "0").replace("$", "").replace(",", "")
                )
            except (ValueError, AttributeError):
                price_usd = 0.0
            price_breaks.append({
                "quantity": pb.get("Quantity", 0),
                "price_usd": price_usd,
                "price_inr": round(price_usd * USD_TO_INR, 2),
            })

        stock_india = int(part.get("AvailabilityInStock", 0) or 0)

        return {
            "source": "mouser",
            "part_number": part.get("ManufacturerPartNumber", ""),
            "mouser_part_number": part.get("MouserPartNumber", ""),
            "description": part.get("Description", ""),
            "manufacturer": part.get("Manufacturer", ""),
            "stock_india": stock_india,
            "availability": part.get("Availability", ""),
            "price_breaks": price_breaks,
            "price_usd": price_breaks[0]["price_usd"] if price_breaks else 0.0,
            "price_inr": price_breaks[0]["price_inr"] if price_breaks else 0.0,
            "lead_time_days": None,
            "datasheet_url": part.get("DataSheetUrl", ""),
            "product_url": part.get("ProductDetailUrl", ""),
        }
