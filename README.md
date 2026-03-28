# MCP Massive Server

[![mpak](https://img.shields.io/badge/mpak-registry-blue)](https://mpak.dev/packages/@nimblebraininc/mcp-massive?utm_source=github&utm_medium=readme&utm_campaign=mcp-massive)
[![NimbleBrain](https://img.shields.io/badge/NimbleBrain-nimblebrain.ai-purple)](https://nimblebrain.ai?utm_source=github&utm_medium=readme&utm_campaign=mcp-massive)
[![Discord](https://img.shields.io/badge/Discord-community-5865F2)](https://nimblebrain.ai/discord?utm_source=github&utm_medium=readme&utm_campaign=mcp-massive)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Financial market data, technical indicators, and SEC filings service powered by the [Massive API](https://massive.com) (formerly Polygon.io). Provides OHLCV candles, real-time snapshots, SMA/EMA/RSI/MACD indicators, SEC filing search and AI-parsed text, and market movers.

**[View on mpak registry](https://mpak.dev/packages/@nimblebraininc/mcp-massive?utm_source=github&utm_medium=readme&utm_campaign=mcp-massive)** | **Built by [NimbleBrain](https://nimblebrain.ai?utm_source=github&utm_medium=readme&utm_campaign=mcp-massive)**

## Tools

- **get_candles** — OHLCV price candles for a ticker over a date range
- **get_snapshot** — Current price snapshot and day stats
- **get_technical_indicator** — SMA, EMA, RSI, or MACD for a ticker
- **get_sec_filing** — Search SEC filings by ticker and type
- **get_sec_filing_section** — Read AI-parsed text from a specific filing section
- **get_ticker_details** — Company reference data (name, SIC, market cap, employees)
- **get_top_movers** — Top gaining or losing stocks

## Configuration

### Required Environment Variables

- `MASSIVE_API_KEY` — Your Massive API key from [massive.com/dashboard](https://massive.com/dashboard/api-keys)

## Development

### Requirements

- Python 3.13+
- FastMCP 2.14.1+
- uv (for dependency management)
- Massive API key (Starter tier recommended, $29/mo)

### Setup

```bash
# Install dependencies
uv sync

# Set your API key
export MASSIVE_API_KEY="your_api_key_here"

# Run tests
make test

# Run all checks (format, lint, test)
make check

# Run server locally
make run
```

### Available Make Targets

```bash
make help          # Show all targets
make check         # Format check + lint + test
make test          # Run unit tests
make test-e2e      # Run e2e MCPB container tests
make run           # Run in stdio mode
make run-http      # Run HTTP server with uvicorn
make bump VERSION=0.2.0  # Bump version across all files
```

## Massive API

This server uses the [Massive API](https://massive.com) (formerly Polygon.io). The Stocks Starter tier ($29/mo) provides:

- 5 years of OHLCV history (minute to yearly resolution)
- Unlimited API calls
- Real-time snapshots and technical indicators
- SEC filings with AI-parsed text sections
- Market movers (top gainers/losers)

## License

MIT
