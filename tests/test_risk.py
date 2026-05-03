"""Unit tests for agents/risk with mocked karaveda MCP responses."""
from __future__ import annotations

import csv
import io
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.risk.landed_cost import LandedCostResult, compute_landed_cost
from agents.risk.register import (
    RiskItem,
    build_risk_register,
    register_to_csv,
    register_to_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_mcp(bcd: float, sws: float, igst: float) -> MagicMock:
    """Return a mock MCP client whose call_tool() returns preset duty values."""
    client = MagicMock()
    client.call_tool = AsyncMock(
        side_effect=lambda tool, _kw: {
            "customs_calc": {"bcd": str(bcd), "sws": str(sws)},
            "gst_calc": {"igst": str(igst)},
        }[tool]
    )
    return client


# ---------------------------------------------------------------------------
# landed_cost tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compute_landed_cost_formula():
    fob, freight, insurance = 1_000.0, 200.0, 10.0
    bcd_val, sws_val, igst_val = 90.0, 9.0, 233.46
    result = await compute_landed_cost(
        fob, freight, insurance, "85414090", _mock_mcp(bcd_val, sws_val, igst_val)
    )

    assert isinstance(result, LandedCostResult)
    expected = fob + freight + insurance + bcd_val + sws_val + igst_val
    assert abs(result.total - expected) < 0.01
    assert result.bcd == bcd_val
    assert result.sws == sws_val
    assert result.igst == igst_val


@pytest.mark.asyncio
async def test_compute_landed_cost_calls_both_mcp_tools():
    mock = _mock_mcp(75.0, 7.5, 180.0)
    await compute_landed_cost(500.0, 100.0, 5.0, "85414090", mock)

    tools_called = [c.args[0] for c in mock.call_tool.call_args_list]
    assert "customs_calc" in tools_called
    assert "gst_calc" in tools_called


@pytest.mark.asyncio
async def test_no_hardcoded_rates():
    """Different MCP responses must produce different totals (rates not baked in)."""
    result_a = await compute_landed_cost(
        1_000.0, 200.0, 10.0, "85414090", _mock_mcp(75.0, 7.5, 180.0)
    )
    result_b = await compute_landed_cost(
        1_000.0, 200.0, 10.0, "85414090", _mock_mcp(150.0, 15.0, 360.0)
    )
    assert result_a.total != result_b.total


@pytest.mark.asyncio
async def test_landed_cost_json_serialisable():
    result = await compute_landed_cost(
        1_000.0, 200.0, 10.0, "85414090", _mock_mcp(75.0, 7.5, 180.0)
    )
    d = json.loads(result.to_json())
    assert "total" in d
    assert "bcd" in d
    assert "igst" in d


@pytest.mark.asyncio
async def test_landed_cost_csv_serialisable():
    result = await compute_landed_cost(
        1_000.0, 200.0, 10.0, "85414090", _mock_mcp(75.0, 7.5, 180.0)
    )
    rows = list(csv.DictReader(io.StringIO(result.to_csv())))
    assert len(rows) == 1
    assert "total" in rows[0]


# ---------------------------------------------------------------------------
# register tests
# ---------------------------------------------------------------------------

def test_register_has_at_least_10_items():
    assert len(build_risk_register()) >= 10


def test_register_covers_all_three_categories():
    cats = {i.category for i in build_risk_register()}
    assert "supply" in cats
    assert "regulatory" in cats
    assert "technical" in cats


def test_register_risk_score_is_product():
    for item in build_risk_register():
        assert item.risk_score == item.severity * item.likelihood


def test_register_severity_likelihood_bounds():
    for item in build_risk_register():
        assert isinstance(item, RiskItem)
        assert 1 <= item.severity <= 4, f"{item.id}: severity out of range"
        assert 1 <= item.likelihood <= 5, f"{item.id}: likelihood out of range"


def test_register_to_json():
    items = build_risk_register()
    data = json.loads(register_to_json(items))
    assert len(data) == len(items)
    assert "id" in data[0]
    assert "mitigation" in data[0]
    assert "risk_score" in data[0]


def test_register_to_csv():
    items = build_risk_register()
    rows = list(csv.DictReader(io.StringIO(register_to_csv(items))))
    assert len(rows) == len(items)
    assert "id" in rows[0]
    assert "risk_score" in rows[0]
    assert "mitigation" in rows[0]
