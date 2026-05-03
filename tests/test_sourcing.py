"""Unit tests for agents/sourcing with mocked API responses."""
from unittest.mock import MagicMock, patch

from agents.sourcing.mouser import MouserClient
from agents.sourcing.digikey import DigiKeyClient
from agents.sourcing.india_filter import filter_for_india

# ── Shared fixture data ────────────────────────────────────────────────────

MOUSER_SEARCH_RESPONSE = {
    "SearchResults": {
        "Parts": [
            {
                "ManufacturerPartNumber": "LM358DR",
                "MouserPartNumber": "595-LM358DR",
                "Description": "Op Amp Dual GP ±16V/32V 8-Pin SOIC",
                "Manufacturer": "Texas Instruments",
                "AvailabilityInStock": 1500,
                "Availability": "1,500 In Stock",
                "PriceBreaks": [
                    {"Quantity": 1, "Price": "$0.22"},
                    {"Quantity": 10, "Price": "$0.18"},
                ],
                "DataSheetUrl": "https://example.com/lm358.pdf",
                "ProductDetailUrl": "https://mouser.com/lm358",
            }
        ]
    }
}

DIGIKEY_SEARCH_RESPONSE = {
    "Products": [
        {
            "ManufacturerPartNumber": "LM358DR",
            "DigiKeyPartNumber": "296-1395-1-ND",
            "ProductDescription": "IC OPAMP GP 1.1MHZ DUAL 8SOIC",
            "Manufacturer": {"Value": "Texas Instruments"},
            "QuantityAvailable": 50000,
            "ManufacturerLeadWeeks": 2,
            "UnitPrice": 0.21,
            "StandardPricing": [
                {"BreakQuantity": 1, "UnitPrice": 0.21},
                {"BreakQuantity": 10, "UnitPrice": 0.17},
            ],
            "PrimaryDatasheet": "https://example.com/lm358.pdf",
            "ProductUrl": "https://digikey.in/lm358",
        }
    ]
}


# ── MouserClient ───────────────────────────────────────────────────────────

class TestMouserClient:
    def _client(self):
        return MouserClient(api_key="test-key")

    def test_search_parts_returns_normalized_list(self):
        client = self._client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOUSER_SEARCH_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client.session, "post", return_value=mock_resp):
            results = client.search_parts("LM358")

        assert len(results) == 1
        part = results[0]
        assert part["source"] == "mouser"
        assert part["part_number"] == "LM358DR"
        assert part["manufacturer"] == "Texas Instruments"
        assert part["stock_india"] == 1500
        assert len(part["price_breaks"]) == 2
        assert part["price_inr"] > 0

    def test_search_parts_passes_api_key(self):
        client = self._client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOUSER_SEARCH_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
            client.search_parts("LM358")

        assert mock_post.call_args.kwargs["params"]["apiKey"] == "test-key"

    def test_get_price_breaks_returns_list(self):
        client = self._client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOUSER_SEARCH_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client.session, "post", return_value=mock_resp):
            breaks = client.get_price_breaks("LM358DR")

        assert isinstance(breaks, list)
        assert breaks[0]["quantity"] == 1
        assert breaks[0]["price_inr"] > 0

    def test_get_price_breaks_empty_when_no_results(self):
        client = self._client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"SearchResults": {"Parts": []}}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client.session, "post", return_value=mock_resp):
            breaks = client.get_price_breaks("NONEXISTENT")

        assert breaks == []

    def test_normalize_handles_missing_price(self):
        part = {
            "ManufacturerPartNumber": "X",
            "MouserPartNumber": "Y",
            "Description": "",
            "Manufacturer": "",
            "AvailabilityInStock": 0,
            "Availability": "",
            "PriceBreaks": [],
        }
        result = MouserClient._normalize(part)
        assert result["price_usd"] == 0.0
        assert result["price_inr"] == 0.0


# ── DigiKeyClient ──────────────────────────────────────────────────────────

class TestDigiKeyClient:
    def _client(self):
        return DigiKeyClient(client_id="test-id", client_secret="test-secret")

    def _mock_token(self, client):
        client._token = "mock-token"
        client._token_expiry = float("inf")

    def test_search_parts_returns_normalized_list(self):
        client = self._client()
        self._mock_token(client)
        mock_resp = MagicMock()
        mock_resp.json.return_value = DIGIKEY_SEARCH_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client.session, "post", return_value=mock_resp):
            results = client.search_parts("LM358")

        assert len(results) == 1
        part = results[0]
        assert part["source"] == "digikey"
        assert part["part_number"] == "LM358DR"
        assert part["ships_to_india"] is True
        assert part["lead_time_days"] == 14
        assert part["price_inr"] > 0

    def test_oauth2_token_fetched_on_first_call(self):
        client = self._client()
        token_resp = MagicMock()
        token_resp.json.return_value = {"access_token": "tok-123", "expires_in": 3600}
        token_resp.raise_for_status = MagicMock()
        search_resp = MagicMock()
        search_resp.json.return_value = DIGIKEY_SEARCH_RESPONSE
        search_resp.raise_for_status = MagicMock()

        with patch.object(client.session, "post", side_effect=[token_resp, search_resp]):
            client.search_parts("LM358")

        assert client._token == "tok-123"

    def test_get_product_details_returns_part(self):
        client = self._client()
        self._mock_token(client)
        product_data = DIGIKEY_SEARCH_RESPONSE["Products"][0]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"Product": product_data}
        mock_resp.raise_for_status = MagicMock()
        mock_resp.status_code = 200

        with patch.object(client.session, "get", return_value=mock_resp):
            part = client.get_product_details("296-1395-1-ND")

        assert part is not None
        assert part["digi_key_part_number"] == "296-1395-1-ND"

    def test_get_product_details_returns_none_for_404(self):
        client = self._client()
        self._mock_token(client)
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch.object(client.session, "get", return_value=mock_resp):
            result = client.get_product_details("NONEXISTENT")

        assert result is None

    def test_normalize_lead_time_conversion(self):
        p = {"ManufacturerLeadWeeks": 4, "QuantityAvailable": 100, "UnitPrice": 1.0}
        result = DigiKeyClient._normalize(p)
        assert result["lead_time_days"] == 28
        assert result["ships_to_india"] is True

    def test_normalize_long_lead_time_not_india(self):
        p = {"ManufacturerLeadWeeks": 6, "QuantityAvailable": 100, "UnitPrice": 1.0}
        result = DigiKeyClient._normalize(p)
        assert result["lead_time_days"] == 42
        assert result["ships_to_india"] is False


# ── filter_for_india ───────────────────────────────────────────────────────

class TestFilterForIndia:
    def _mouser_part(self, stock=100, price_inr=18.0):
        return {
            "source": "mouser",
            "part_number": "LM358DR",
            "stock_india": stock,
            "price_inr": price_inr,
            "price_usd": price_inr / 83.5,
            "lead_time_days": None,
        }

    def _digikey_part(self, ships=True, lead_days=14, price_inr=17.5):
        return {
            "source": "digikey",
            "part_number": "LM358DR",
            "stock_india": 50000,
            "ships_to_india": ships,
            "lead_time_days": lead_days,
            "price_inr": price_inr,
            "price_usd": price_inr / 83.5,
        }

    def test_mouser_in_stock_passes(self):
        result = filter_for_india([self._mouser_part(stock=100)])
        assert len(result) == 1

    def test_mouser_out_of_stock_filtered(self):
        result = filter_for_india([self._mouser_part(stock=0)])
        assert len(result) == 0

    def test_digikey_ships_and_fast_passes(self):
        result = filter_for_india([self._digikey_part(ships=True, lead_days=14)])
        assert len(result) == 1

    def test_digikey_no_ship_filtered(self):
        result = filter_for_india([self._digikey_part(ships=False, lead_days=14)])
        assert len(result) == 0

    def test_digikey_long_lead_time_filtered(self):
        result = filter_for_india([self._digikey_part(ships=True, lead_days=45)])
        assert len(result) == 0

    def test_ranked_by_price_inr_ascending(self):
        parts = [
            self._mouser_part(price_inr=25.0),
            self._digikey_part(price_inr=17.5),
        ]
        result = filter_for_india(parts)
        assert len(result) == 2
        assert result[0]["price_inr"] < result[1]["price_inr"]

    def test_zero_price_parts_go_last(self):
        parts = [
            self._mouser_part(price_inr=0.0),
            self._digikey_part(price_inr=17.5),
        ]
        result = filter_for_india(parts)
        assert result[0]["price_inr"] == 17.5
        assert result[-1]["price_inr"] == 0.0

    def test_output_fields_present(self):
        result = filter_for_india([self._digikey_part()])
        assert len(result) == 1
        part = result[0]
        assert "part_number" in part
        assert "price_inr" in part
        assert "stock_india" in part
        assert "lead_time_days" in part
