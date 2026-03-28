# Massive

## Critical: Reuse Prior Results

Follow-up questions ("what's the current price?", "show me the chart") should use data from earlier tool responses before making new calls. If you already fetched candles or a snapshot, surface that data directly.

## Tool Selection

| Intent | Tool |
|--------|------|
| Price chart / historical prices | `get_candles(ticker, from_date, to_date)` |
| Current price + day stats | `get_snapshot(ticker)` |
| SMA, EMA, RSI, MACD | `get_technical_indicator(ticker, indicator_type)` |
| Find SEC filings (10-K, 8-K, etc.) | `get_sec_filing(ticker, filing_type)` |
| Read filing text (risk factors, etc.) | `get_sec_filing_section(filing_id, section)` |
| Company info (name, SIC, employees) | `get_ticker_details(ticker)` |
| Market movers (top gainers/losers) | `get_top_movers(direction)` |

## Stock Symbols

Use uppercase US ticker symbols: `AAPL`, `MSFT`, `GOOGL`, `TSLA`.

## Technical Indicators

`get_technical_indicator` supports four types:
- **sma** — Simple Moving Average (default window: 50)
- **ema** — Exponential Moving Average (default window: 50)
- **rsi** — Relative Strength Index (default window: 14)
- **macd** — Moving Average Convergence Divergence (returns value, signal, histogram)

Use `limit=1` (default) for the latest value. Increase `limit` for a time series.

## SEC Filing Sections

Common sections for `get_sec_filing_section`:
- `risk_factors` — Risk factors from 10-K/10-Q
- `business` — Business description
- `mda` — Management's Discussion and Analysis
- `financial_statements` — Financial statements

`get_sec_filing_section` queries by ticker and section directly (no filing ID needed).
Use `filing_type` to specify 10-K or 8-K. Returns the latest filing's section by default.

## Multi-Step Workflows

**"What's the price of X?"**:
1. `get_snapshot(ticker)` for current price + day stats

**"Show me a chart of X"**:
1. `get_candles(ticker, from_date, to_date)` with appropriate date range

**"Technical analysis of X"**:
1. `get_candles(ticker, from_date, to_date)` for price history
2. `get_technical_indicator(ticker, "sma", window=50)` for SMA-50
3. `get_technical_indicator(ticker, "rsi", window=14)` for RSI-14

**"What are the risk factors for X?"**:
1. `get_sec_filing_section(ticker, "risk_factors")` to read the latest 10-K risk factors directly

**"Company overview of X"**:
1. `get_ticker_details(ticker)` for company info
2. `get_snapshot(ticker)` for current price

**"What's moving in the market?"**:
1. `get_top_movers("gainers")` for top gainers
2. `get_top_movers("losers")` for top losers

**"How has X performed since [date]?"**:
1. `get_candles(ticker, from_date, to_date)` for price history over the period
2. Compare first and last candle for total return

## Candle Timespans

`get_candles` supports: `minute`, `hour`, `day`, `week`, `month`, `quarter`, `year`.

Use `multiplier` to aggregate (e.g. multiplier=5, timespan=minute for 5-minute candles).

Massive Starter tier provides 5 years of history with unlimited API calls.
