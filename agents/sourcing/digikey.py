"""DigiKey API client with OAuth2 client-credentials flow."""
import os
import time
import requests
from typing import Any

DIGIKEY_TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
DIGIKEY_API_BASE = "https://api.digikey.com/Search/v3"
USD_TO_INR = 83.5


class DigiKeyClient:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.client_id = client_id or os.environ["DIGIKEY_CLIENT_ID"]
        self.client_secret = client_secret or os.environ["DIGIKEY_CLIENT_SECRET"]
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self.session = requests.Session()

    def _ensure_token(self) -> None:
        if self._token and time.time() < self._token_expiry - 60:
            return
        resp = self.session.post(
            DIGIKEY_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600)

    def _headers(self) -> dict:
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "X-DIGIKEY-Client-Id": self.client_id,
            "X-DIGIKEY-Locale-Site": "IN",
            "X-DIGIKEY-Locale-Language": "en",
            "X-DIGIKEY-Locale-Currency": "INR",
            "Content-Type": "application/json",
        }

    def search_parts(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        url = f"{DIGIKEY_API_BASE}/Products/Keyword"
        payload = {
            "Keywords": keyword,
            "RecordCount": limit,
            "RecordStartPosition": 0,
            "Filters": {},
            "Sort": {"SortOption": "SortByUnitPrice", "Direction": "Ascending"},
            "RequestedQuantity": 1,
            "ShipToCountryCode": "IN",
        }
        resp = self.session.post(url, json=payload, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        products = data.get("Products", []) or []
        return [self._normalize(p) for p in products]

    def get_product_details(self, digi_key_part_number: str) -> dict[str, Any] | None:
        url = f"{DIGIKEY_API_BASE}/Products/{digi_key_part_number}"
        resp = self.session.get(url, headers=self._headers(), timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._normalize(resp.json().get("Product", resp.json()))

    @staticmethod
    def _normalize(p: dict) -> dict[str, Any]:
        unit_price = p.get("UnitPrice", 0.0) or 0.0
        price_inr = round(unit_price * USD_TO_INR, 2) if unit_price else 0.0

        lead_time_str = str(p.get("ManufacturerLeadWeeks", "0") or "0")
        try:
            lead_time_days = int(float(lead_time_str) * 7)
        except ValueError:
            lead_time_days = 999

        ships_to_india = lead_time_days < 30

        return {
            "source": "digikey",
            "part_number": p.get("ManufacturerPartNumber", ""),
            "digi_key_part_number": p.get("DigiKeyPartNumber", ""),
            "description": p.get("ProductDescription", ""),
            "manufacturer": (p.get("Manufacturer") or {}).get("Value", ""),
            "stock_india": p.get("QuantityAvailable", 0) or 0,
            "ships_to_india": ships_to_india,
            "lead_time_days": lead_time_days,
            "price_usd": unit_price,
            "price_inr": price_inr,
            "price_breaks": [
                {
                    "quantity": pb.get("BreakQuantity", 1),
                    "price_usd": pb.get("UnitPrice", 0.0),
                    "price_inr": round((pb.get("UnitPrice", 0.0) or 0) * USD_TO_INR, 2),
                }
                for pb in (p.get("StandardPricing", []) or [])
            ],
            "datasheet_url": p.get("PrimaryDatasheet", ""),
            "product_url": p.get("ProductUrl", ""),
        }
