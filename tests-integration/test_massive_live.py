"""
Live integration tests against the real Massive API (formerly Polygon.io).

Requires MASSIVE_API_KEY in environment.
Verifies URL construction, query params, and response parsing against the real API.
"""

import json

import pytest
from fastmcp import Client


@pytest.mark.asyncio
async def test_get_candles_live(mcp_server):
    """get_candles returns real OHLCV data with correct field mapping."""
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_candles",
            {
                "ticker": "AAPL",
                "from_date": "2025-01-02",
                "to_date": "2025-01-10",
                "timespan": "day",
            },
        )

        data = json.loads(result.data)
        assert "error" not in data, f"API error: {data.get('error')}"
        assert data["ticker"] == "AAPL"
        assert data["count"] > 0

        candle = data["candles"][0]
        assert candle["open"] is not None
        assert candle["high"] is not None
        assert candle["low"] is not None
        assert candle["close"] is not None
        assert candle["volume"] is not None
        assert candle["high"] >= candle["low"]


@pytest.mark.asyncio
async def test_get_snapshot_live(mcp_server):
    """get_snapshot returns current price data with day and prev_day."""
    async with Client(mcp_server) as client:
        result = await client.call_tool("get_snapshot", {"ticker": "AAPL"})

        data = json.loads(result.data)
        assert "error" not in data, f"API error: {data.get('error')}"
        assert data["ticker"] == "AAPL"
        assert data["day"]["open"] is not None
        assert data["prev_day"]["close"] is not None


@pytest.mark.asyncio
async def test_get_technical_indicator_sma_live(mcp_server):
    """get_technical_indicator returns a real SMA value."""
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_technical_indicator",
            {
                "ticker": "AAPL",
                "indicator_type": "sma",
                "window": 50,
                "limit": 1,
            },
        )

        data = json.loads(result.data)
        assert "error" not in data, f"API error: {data.get('error')}"
        assert data["indicator"] == "sma"
        assert data["count"] == 1
        assert isinstance(data["values"][0]["value"], (int, float))


@pytest.mark.asyncio
async def test_get_technical_indicator_rsi_live(mcp_server):
    """get_technical_indicator returns a real RSI value in 0-100 range."""
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_technical_indicator",
            {
                "ticker": "AAPL",
                "indicator_type": "rsi",
                "window": 14,
                "limit": 1,
            },
        )

        data = json.loads(result.data)
        assert "error" not in data, f"API error: {data.get('error')}"
        assert data["indicator"] == "rsi"
        assert 0 <= data["values"][0]["value"] <= 100


@pytest.mark.asyncio
async def test_get_technical_indicator_macd_live(mcp_server):
    """get_technical_indicator returns MACD with value, signal, and histogram."""
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_technical_indicator",
            {
                "ticker": "AAPL",
                "indicator_type": "macd",
                "limit": 1,
            },
        )

        data = json.loads(result.data)
        assert "error" not in data, f"API error: {data.get('error')}"
        assert data["indicator"] == "macd"
        macd = data["values"][0]
        assert "value" in macd
        assert "signal" in macd
        assert "histogram" in macd


@pytest.mark.asyncio
async def test_get_ticker_details_live(mcp_server):
    """get_ticker_details returns real company reference data."""
    async with Client(mcp_server) as client:
        result = await client.call_tool("get_ticker_details", {"ticker": "AAPL"})

        data = json.loads(result.data)
        assert "error" not in data, f"API error: {data.get('error')}"
        assert data["ticker"] == "AAPL"
        assert data["name"] is not None
        assert "apple" in data["name"].lower()
        assert data["market_cap"] is not None
        assert data["sic_code"] is not None


@pytest.mark.asyncio
async def test_get_top_movers_live(mcp_server):
    """get_top_movers returns a list of gainers with tickers and prices."""
    async with Client(mcp_server) as client:
        result = await client.call_tool("get_top_movers", {"direction": "gainers"})

        data = json.loads(result.data)
        assert "error" not in data, f"API error: {data.get('error')}"
        assert data["direction"] == "gainers"
        assert data["count"] > 0

        mover = data["movers"][0]
        assert mover["ticker"] is not None
        assert mover["change_pct"] is not None


@pytest.mark.asyncio
async def test_get_sec_filing_live(mcp_server):
    """get_sec_filing returns SEC filing index for a major ticker."""
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_sec_filing",
            {
                "ticker": "AAPL",
                "filing_type": "10-K",
                "limit": 3,
            },
        )

        data = json.loads(result.data)
        assert "error" not in data, f"API error: {data.get('error')}"
        assert data["ticker"] == "AAPL"
        assert data["count"] > 0

        filing = data["filings"][0]
        assert filing["id"] is not None
        assert filing["type"] is not None
        assert filing["filing_date"] is not None
