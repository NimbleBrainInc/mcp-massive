#!/usr/bin/env python3
"""
Massive MCP Server - FastMCP Implementation
Financial market data, technical indicators, and SEC filings service powered by Massive API
(formerly Polygon.io)
"""

import json
import os
from datetime import UTC, datetime
from importlib.resources import files

import httpx
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# Create FastMCP server
mcp = FastMCP(
    "Massive MCP Server",
    instructions=(
        "Before using Massive tools, read the skill://massive/usage resource "
        "for tool selection guidance and multi-step workflow patterns."
    ),
)

SKILL_CONTENT = files("mcp_massive").joinpath("SKILL.md").read_text()

BASE_URL = "https://api.massive.com"


@mcp.resource("skill://massive/usage")
def massive_skill() -> str:
    """How to effectively use Massive tools: tool selection, indicators, multi-step workflows."""
    return SKILL_CONTENT


def _get_api_key() -> str:
    """Get the Massive API key from environment."""
    api_key = os.getenv("MASSIVE_API_KEY")
    if not api_key:
        raise ValueError("MASSIVE_API_KEY environment variable is required")
    return api_key


def _request(path: str, params: dict | None = None) -> dict:
    """Make an authenticated GET request to the Polygon API."""
    api_key = _get_api_key()
    params = params or {}
    params["apiKey"] = api_key
    resp = httpx.get(f"{BASE_URL}{path}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def get_candles(
    ticker: str,
    from_date: str,
    to_date: str,
    timespan: str = "day",
    multiplier: int = 1,
    adjusted: bool = True,
    limit: int = 5000,
) -> str:
    """Get OHLCV price candles for a ticker over a date range.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL)
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        timespan: Candle size: minute, hour, day, week, month, quarter, year
        multiplier: Size of the timespan multiplier (e.g. 5 with minute = 5-minute candles)
        adjusted: Whether results are adjusted for splits (default true)
        limit: Max number of results (default 5000)
    """
    try:
        path = (
            f"/v2/aggs/ticker/{ticker.upper()}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        )
        data = _request(path, {"adjusted": str(adjusted).lower(), "limit": limit, "sort": "asc"})

        candles = []
        for bar in data.get("results", []):
            candles.append(
                {
                    "open": bar.get("o"),
                    "high": bar.get("h"),
                    "low": bar.get("l"),
                    "close": bar.get("c"),
                    "volume": bar.get("v"),
                    "vwap": bar.get("vw"),
                    "timestamp": bar.get("t"),
                    "transactions": bar.get("n"),
                }
            )

        result = {
            "ticker": ticker.upper(),
            "timespan": timespan,
            "multiplier": multiplier,
            "from_date": from_date,
            "to_date": to_date,
            "count": len(candles),
            "candles": candles,
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error fetching candles for {ticker}: {e}",
                "ticker": ticker.upper(),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )


@mcp.tool
def get_snapshot(ticker: str) -> str:
    """Get current price snapshot and day stats for a single ticker.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL)
    """
    try:
        data = _request(f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}")
        snap = data.get("ticker", {})

        day = snap.get("day", {})
        prev = snap.get("prevDay", {})

        result = {
            "ticker": snap.get("ticker", ticker.upper()),
            "price": snap.get("lastTrade", {}).get("p"),
            "change": snap.get("todaysChange"),
            "change_pct": snap.get("todaysChangePerc"),
            "volume": day.get("v"),
            "day": {
                "open": day.get("o"),
                "high": day.get("h"),
                "low": day.get("l"),
                "close": day.get("c"),
                "volume": day.get("v"),
                "vwap": day.get("vw"),
            },
            "prev_day": {
                "open": prev.get("o"),
                "high": prev.get("h"),
                "low": prev.get("l"),
                "close": prev.get("c"),
                "volume": prev.get("v"),
                "vwap": prev.get("vw"),
            },
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error fetching snapshot for {ticker}: {e}",
                "ticker": ticker.upper(),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )


@mcp.tool
def get_technical_indicator(
    ticker: str,
    indicator_type: str = "sma",
    window: int | None = None,
    timespan: str = "day",
    limit: int = 1,
) -> str:
    """Get a technical indicator (SMA, EMA, RSI, or MACD) for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL)
        indicator_type: One of: sma, ema, rsi, macd
        window: Lookback window (default 50 for SMA/EMA, 14 for RSI, ignored for MACD)
        timespan: Candle timespan: minute, hour, day, week, month, quarter, year
        limit: Number of data points to return (default 1 = latest only)
    """
    try:
        indicator_type = indicator_type.lower()
        if indicator_type not in ("sma", "ema", "rsi", "macd"):
            return json.dumps(
                {
                    "error": f"Invalid indicator_type '{indicator_type}'. Must be one of: sma, ema, rsi, macd",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                indent=2,
            )

        if window is None:
            window = 14 if indicator_type == "rsi" else 50

        params = {"timespan": timespan, "limit": limit, "sort": "desc"}
        if indicator_type != "macd":
            params["window"] = window

        data = _request(f"/v1/indicators/{indicator_type}/{ticker.upper()}", params)

        values = []
        for val in data.get("results", {}).get("values", []):
            entry = {"timestamp": val.get("timestamp")}
            if indicator_type == "macd":
                entry["value"] = val.get("value")
                entry["signal"] = val.get("signal")
                entry["histogram"] = val.get("histogram")
            else:
                entry["value"] = val.get("value")
            values.append(entry)

        result = {
            "ticker": ticker.upper(),
            "indicator": indicator_type,
            "window": window if indicator_type != "macd" else None,
            "timespan": timespan,
            "count": len(values),
            "values": values,
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error fetching {indicator_type} for {ticker}: {e}",
                "ticker": ticker.upper(),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )


@mcp.tool
def get_sec_filing(
    ticker: str,
    filing_type: str = "",
    limit: int = 10,
) -> str:
    """Search SEC filings for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL)
        filing_type: Filter by form type: 10-K, 10-Q, 8-K, etc. (empty = all types)
        limit: Max results to return (default 10)
    """
    try:
        params: dict = {"ticker": ticker.upper(), "limit": limit}
        if filing_type:
            params["form_type"] = filing_type

        data = _request("/stocks/filings/vX/index", params)

        filings = []
        for f in data.get("results", []):
            filings.append(
                {
                    "ticker": f.get("ticker"),
                    "issuer_name": f.get("issuer_name"),
                    "form_type": f.get("form_type"),
                    "filing_date": f.get("filing_date"),
                    "accession_number": f.get("accession_number"),
                    "filing_url": f.get("filing_url"),
                    "cik": f.get("cik"),
                }
            )

        result = {
            "ticker": ticker.upper(),
            "filing_type": filing_type or "all",
            "count": len(filings),
            "filings": filings,
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error fetching SEC filings for {ticker}: {e}",
                "ticker": ticker.upper(),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )


@mcp.tool
def get_sec_filing_section(
    ticker: str,
    section: str,
    filing_type: str = "10-K",
    limit: int = 1,
) -> str:
    """Read a specific section of an SEC filing (AI-parsed text).

    Args:
        ticker: Stock ticker symbol (e.g. AAPL)
        section: Section to read, e.g. risk_factors, business, mda, financial_statements
        filing_type: Filing type: 10-K or 8-K (default: 10-K)
        limit: Number of results (default 1 = latest filing)
    """
    try:
        path = f"/stocks/filings/{filing_type}/vX/sections"
        data = _request(path, {"ticker": ticker.upper(), "section": section, "limit": limit})

        sections = []
        for s in data.get("results", []):
            sections.append(
                {
                    "ticker": s.get("ticker"),
                    "section": s.get("section"),
                    "filing_date": s.get("filing_date"),
                    "text": s.get("text", ""),
                }
            )

        result = {
            "ticker": ticker.upper(),
            "section": section,
            "filing_type": filing_type,
            "count": len(sections),
            "sections": sections,
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error fetching section '{section}' for {ticker}: {e}",
                "ticker": ticker.upper(),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )


@mcp.tool
def get_ticker_details(ticker: str) -> str:
    """Get company reference data for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL)
    """
    try:
        data = _request(f"/v3/reference/tickers/{ticker.upper()}")
        r = data.get("results", {})

        result = {
            "ticker": r.get("ticker", ticker.upper()),
            "name": r.get("name"),
            "market_cap": r.get("market_cap"),
            "sic_code": r.get("sic_code"),
            "sic_description": r.get("sic_description"),
            "description": r.get("description"),
            "homepage_url": r.get("homepage_url"),
            "total_employees": r.get("total_employees"),
            "list_date": r.get("list_date"),
            "locale": r.get("locale"),
            "market": r.get("market"),
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error fetching ticker details for {ticker}: {e}",
                "ticker": ticker.upper(),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )


@mcp.tool
def get_top_movers(direction: str = "gainers") -> str:
    """Get top gaining or losing stocks.

    Args:
        direction: Either 'gainers' or 'losers' (default: gainers)
    """
    try:
        direction = direction.lower()
        if direction not in ("gainers", "losers"):
            return json.dumps(
                {
                    "error": f"Invalid direction '{direction}'. Must be 'gainers' or 'losers'",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                indent=2,
            )

        data = _request(f"/v2/snapshot/locale/us/markets/stocks/{direction}")

        movers = []
        for snap in data.get("tickers", []):
            day = snap.get("day", {})
            movers.append(
                {
                    "ticker": snap.get("ticker"),
                    "price": day.get("c"),
                    "change_pct": snap.get("todaysChangePerc"),
                    "volume": day.get("v"),
                }
            )

        result = {
            "direction": direction,
            "count": len(movers),
            "movers": movers,
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error fetching top {direction}: {e}",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request):
    return JSONResponse({"status": "healthy"})


# ASGI entrypoint (nimbletools-core container deployment)
app = mcp.http_app()

# Stdio entrypoint (mpak / Claude Desktop)
if __name__ == "__main__":
    mcp.run()
