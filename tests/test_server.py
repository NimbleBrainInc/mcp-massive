"""Tests for massive MCP server functionality."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import Client


class TestSkillResource:
    """Test the skill resource and server instructions."""

    @pytest.mark.asyncio
    async def test_initialize_returns_instructions(self, mcp_server):
        """Server instructions reference the skill resource."""
        async with Client(mcp_server) as client:
            result = await client.initialize()
            assert result.instructions is not None
            assert "skill://massive/usage" in result.instructions

    @pytest.mark.asyncio
    async def test_skill_resource_listed(self, mcp_server):
        """skill://massive/usage appears in resource listing."""
        async with Client(mcp_server) as client:
            resources = await client.list_resources()
            uris = [str(r.uri) for r in resources]
            assert "skill://massive/usage" in uris

    @pytest.mark.asyncio
    async def test_skill_resource_readable(self, mcp_server):
        """Reading the skill resource returns the full skill content."""
        async with Client(mcp_server) as client:
            contents = await client.read_resource("skill://massive/usage")
            text = contents[0].text if hasattr(contents[0], "text") else str(contents[0])
            assert "Tool Selection" in text
            assert "get_candles" in text
            assert "get_snapshot" in text


@pytest.mark.asyncio
async def test_tools_list(mcp_server):
    """Test that all 7 tools are properly registered."""
    async with Client(mcp_server) as client:
        tools = await client.list_tools()

        assert len(tools) == 7
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "get_candles",
            "get_snapshot",
            "get_technical_indicator",
            "get_sec_filing",
            "get_sec_filing_section",
            "get_ticker_details",
            "get_top_movers",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

        candles_tool = next(t for t in tools if t.name == "get_candles")
        assert "OHLCV" in candles_tool.description

        snapshot_tool = next(t for t in tools if t.name == "get_snapshot")
        assert "snapshot" in snapshot_tool.description.lower()


@pytest.mark.asyncio
async def test_get_candles_missing_params(mcp_server):
    """Test calling get_candles without required parameters."""
    async with Client(mcp_server) as client:
        try:
            await client.call_tool("get_candles", {})
            raise AssertionError("Should have raised an exception")
        except Exception as e:
            assert "ticker" in str(e).lower() or "required" in str(e).lower()


@pytest.mark.asyncio
async def test_invalid_tool(mcp_server):
    """Test calling invalid tool."""
    async with Client(mcp_server) as client:
        try:
            await client.call_tool("invalid_tool", {})
            raise AssertionError("Should have raised an exception")
        except Exception as e:
            assert "invalid_tool" in str(e).lower() or "not found" in str(e).lower()


# --- Mocked tool tests ---


@patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key"})
@patch("mcp_massive.server.httpx.get")
@pytest.mark.asyncio
async def test_get_candles_with_mock(mock_get, mcp_server):
    """Test get_candles with mocked HTTP response."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {
                "o": 150.0,
                "h": 155.0,
                "l": 149.0,
                "c": 153.0,
                "v": 1000000,
                "vw": 152.5,
                "t": 1711929600000,
                "n": 5000,
            },
            {
                "o": 153.0,
                "h": 156.0,
                "l": 152.0,
                "c": 154.5,
                "v": 900000,
                "vw": 154.0,
                "t": 1712016000000,
                "n": 4500,
            },
        ],
        "resultsCount": 2,
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_candles",
            {
                "ticker": "AAPL",
                "from_date": "2026-03-01",
                "to_date": "2026-03-27",
            },
        )

        data = json.loads(result.data)
        assert data["ticker"] == "AAPL"
        assert data["count"] == 2
        assert data["candles"][0]["open"] == 150.0
        assert data["candles"][0]["close"] == 153.0
        assert data["candles"][0]["volume"] == 1000000
        assert "retrieved_at" in data


@patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key"})
@patch("mcp_massive.server.httpx.get")
@pytest.mark.asyncio
async def test_get_snapshot_with_mock(mock_get, mcp_server):
    """Test get_snapshot with mocked HTTP response."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "ticker": {
            "ticker": "AAPL",
            "lastTrade": {"p": 175.50},
            "todaysChange": 2.30,
            "todaysChangePerc": 1.33,
            "day": {"o": 173.0, "h": 176.0, "l": 172.5, "c": 175.5, "v": 45000000, "vw": 174.8},
            "prevDay": {"o": 172.0, "h": 174.0, "l": 171.0, "c": 173.2, "v": 40000000, "vw": 172.5},
        }
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    async with Client(mcp_server) as client:
        result = await client.call_tool("get_snapshot", {"ticker": "AAPL"})

        data = json.loads(result.data)
        assert data["ticker"] == "AAPL"
        assert data["price"] == 175.50
        assert data["change"] == 2.30
        assert data["change_pct"] == 1.33
        assert data["day"]["open"] == 173.0
        assert data["prev_day"]["close"] == 173.2
        assert "retrieved_at" in data


@patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key"})
@patch("mcp_massive.server.httpx.get")
@pytest.mark.asyncio
async def test_get_technical_indicator_sma(mock_get, mcp_server):
    """Test get_technical_indicator with SMA type."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": {
            "values": [
                {"timestamp": 1711929600000, "value": 172.35},
            ]
        }
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_technical_indicator",
            {
                "ticker": "AAPL",
                "indicator_type": "sma",
                "window": 50,
            },
        )

        data = json.loads(result.data)
        assert data["ticker"] == "AAPL"
        assert data["indicator"] == "sma"
        assert data["window"] == 50
        assert data["count"] == 1
        assert data["values"][0]["value"] == 172.35


@patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key"})
@patch("mcp_massive.server.httpx.get")
@pytest.mark.asyncio
async def test_get_technical_indicator_macd(mock_get, mcp_server):
    """Test get_technical_indicator with MACD type returns signal and histogram."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": {
            "values": [
                {"timestamp": 1711929600000, "value": 1.25, "signal": 0.80, "histogram": 0.45},
            ]
        }
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_technical_indicator",
            {
                "ticker": "AAPL",
                "indicator_type": "macd",
            },
        )

        data = json.loads(result.data)
        assert data["indicator"] == "macd"
        assert data["window"] is None
        assert data["values"][0]["value"] == 1.25
        assert data["values"][0]["signal"] == 0.80
        assert data["values"][0]["histogram"] == 0.45


@pytest.mark.asyncio
async def test_get_technical_indicator_invalid_type(mcp_server):
    """Test get_technical_indicator rejects invalid indicator types."""
    with patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key"}):
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "get_technical_indicator",
                {
                    "ticker": "AAPL",
                    "indicator_type": "invalid",
                },
            )

            data = json.loads(result.data)
            assert "error" in data
            assert "invalid" in data["error"].lower()


@patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key"})
@patch("mcp_massive.server.httpx.get")
@pytest.mark.asyncio
async def test_get_sec_filing_with_mock(mock_get, mcp_server):
    """Test get_sec_filing returns filing index."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {
                "id": "filing_001",
                "ticker": "AAPL",
                "filing_date": "2026-02-01",
                "type": "10-K",
                "source_filing_url": "https://sec.gov/filing/001",
            },
            {
                "id": "filing_002",
                "ticker": "AAPL",
                "filing_date": "2025-11-01",
                "type": "10-Q",
                "source_filing_url": "https://sec.gov/filing/002",
            },
        ]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_sec_filing",
            {
                "ticker": "AAPL",
                "filing_type": "10-K",
            },
        )

        data = json.loads(result.data)
        assert data["ticker"] == "AAPL"
        assert data["filing_type"] == "10-K"
        assert data["count"] == 2
        assert data["filings"][0]["id"] == "filing_001"
        assert data["filings"][0]["type"] == "10-K"
        assert "retrieved_at" in data


@patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key"})
@patch("mcp_massive.server.httpx.get")
@pytest.mark.asyncio
async def test_get_sec_filing_section_with_mock(mock_get, mcp_server):
    """Test get_sec_filing_section returns parsed text."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "text": "The company faces significant risks including market volatility..."
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_sec_filing_section",
            {
                "filing_id": "filing_001",
                "section": "risk_factors",
            },
        )

        data = json.loads(result.data)
        assert data["filing_id"] == "filing_001"
        assert data["section"] == "risk_factors"
        assert "market volatility" in data["text"]
        assert "retrieved_at" in data


@patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key"})
@patch("mcp_massive.server.httpx.get")
@pytest.mark.asyncio
async def test_get_ticker_details_with_mock(mock_get, mcp_server):
    """Test get_ticker_details returns company reference data."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "market_cap": 2800000000000,
            "sic_code": "3571",
            "sic_description": "Electronic Computers",
            "description": "Apple designs, manufactures, and markets consumer electronics.",
            "homepage_url": "https://apple.com",
            "total_employees": 164000,
            "list_date": "1980-12-12",
            "locale": "us",
            "market": "stocks",
        }
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    async with Client(mcp_server) as client:
        result = await client.call_tool("get_ticker_details", {"ticker": "AAPL"})

        data = json.loads(result.data)
        assert data["ticker"] == "AAPL"
        assert data["name"] == "Apple Inc."
        assert data["market_cap"] == 2800000000000
        assert data["sic_code"] == "3571"
        assert data["total_employees"] == 164000
        assert "retrieved_at" in data


@patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key"})
@patch("mcp_massive.server.httpx.get")
@pytest.mark.asyncio
async def test_get_top_movers_gainers(mock_get, mcp_server):
    """Test get_top_movers returns top gainers."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "tickers": [
            {"ticker": "NVDA", "day": {"c": 950.0, "v": 30000000}, "todaysChangePerc": 8.5},
            {"ticker": "AMD", "day": {"c": 180.0, "v": 25000000}, "todaysChangePerc": 5.2},
        ]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    async with Client(mcp_server) as client:
        result = await client.call_tool("get_top_movers", {"direction": "gainers"})

        data = json.loads(result.data)
        assert data["direction"] == "gainers"
        assert data["count"] == 2
        assert data["movers"][0]["ticker"] == "NVDA"
        assert data["movers"][0]["price"] == 950.0
        assert data["movers"][0]["change_pct"] == 8.5
        assert "retrieved_at" in data


@pytest.mark.asyncio
async def test_get_top_movers_invalid_direction(mcp_server):
    """Test get_top_movers rejects invalid direction."""
    with patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key"}):
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_top_movers", {"direction": "sideways"})

            data = json.loads(result.data)
            assert "error" in data
            assert "sideways" in data["error"].lower()


# --- Missing API key tests ---


@pytest.mark.asyncio
async def test_get_candles_no_api_key(mcp_server):
    """Test get_candles returns error without API key."""
    with patch.dict(os.environ, {}, clear=True):
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "get_candles",
                {
                    "ticker": "AAPL",
                    "from_date": "2026-03-01",
                    "to_date": "2026-03-27",
                },
            )
            data = json.loads(result.data)
            assert "error" in data
            assert "MASSIVE_API_KEY" in data["error"]


@pytest.mark.asyncio
async def test_get_snapshot_no_api_key(mcp_server):
    """Test get_snapshot returns error without API key."""
    with patch.dict(os.environ, {}, clear=True):
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_snapshot", {"ticker": "AAPL"})
            data = json.loads(result.data)
            assert "error" in data
            assert "MASSIVE_API_KEY" in data["error"]


@pytest.mark.asyncio
async def test_get_ticker_details_no_api_key(mcp_server):
    """Test get_ticker_details returns error without API key."""
    with patch.dict(os.environ, {}, clear=True):
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_ticker_details", {"ticker": "AAPL"})
            data = json.loads(result.data)
            assert "error" in data
            assert "MASSIVE_API_KEY" in data["error"]


@pytest.mark.asyncio
async def test_get_sec_filing_no_api_key(mcp_server):
    """Test get_sec_filing returns error without API key."""
    with patch.dict(os.environ, {}, clear=True):
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_sec_filing", {"ticker": "AAPL"})
            data = json.loads(result.data)
            assert "error" in data
            assert "MASSIVE_API_KEY" in data["error"]
