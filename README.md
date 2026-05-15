# Stock Insight Pro

A professional stock analysis dashboard for monitoring portfolio performance and market sectors. Combines a Flask web dashboard, a background market-monitoring loop, an SEC EDGAR filing portal, and an optional MCP server for SEC filings.

## Features

- **Web dashboard** (`src/web_server.py`) — Flask UI showing per-ticker metrics across short/mid/long/longExt terms, with annual-performance and cash-flow charts rendered by matplotlib.
- **Monitoring loop** (`src/main.py`) — long-running CLI that re-checks tickers every 60 seconds while the market is open and rebuilds the local CSV/JSON cache on startup.
- **EDGAR filing portal** (`src/edgar_test_server.py`) — secondary Flask app for browsing locally cached SEC 10-K/10-Q filings.
- **MCP server** (`mcp/sec-edgar.js`) — Model Context Protocol server exposing SEC EDGAR lookups (CIK lookup, recent filings) to MCP-compatible clients.
- **13F processor skill** (`skills/scripts/13f_processor.py`) — converts SEC 13F XML filings into aggregated JSON.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (only required for the MCP server)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yulin015/stock_insight.git
   cd stock_insight
   ```

2. **(Recommended) Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate          # macOS/Linux
   # .venv\Scripts\activate           # Windows (PowerShell/cmd)
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   Pinned dependencies: Flask 3.1.3, pandas 2.3.3, yfinance 1.1.0, matplotlib 3.9.4, numpy 2.0.2, lxml 6.0.2, requests 2.32.5.

4. **Install Node.js dependencies (optional — MCP server only):**
   ```bash
   cd mcp
   npm install
   cd ..
   ```

## Configuration

- **Tickers** — edit `config/tkr.json`. Each entry has a `class` name, a list of `etf_tickers`, and a list of `tickers`. Both the web server and the monitoring loop load this file at startup.
- **EDGAR companies** — `config/edgar_company.json` drives the filing portal.
- **EDGAR User-Agent** — the MCP server reads `EDGAR_IDENTITY` from the environment (e.g. `export EDGAR_IDENTITY="Your Name your@email"`) to comply with SEC's User-Agent requirement.

## Running the Application

Run commands from the repository root. Use `python` on Windows and `python3` on macOS/Linux as appropriate.

### 1. Web Dashboard (primary app)
```bash
python3 src/web_server.py
```
- URL: http://127.0.0.1:5001
- On startup it calls `verify_and_rebuild_data(...)`, which downloads/refreshes price history into `repository/csv/<TICKER>.csv` and `repository/json/<TICKER>.json` for every ticker in `config/tkr.json`. First run may take a few minutes.
- Key routes:
  - `/` — class selector (categories from `tkr.json`)
  - `/class/<class_name>` — dashboard per class
  - `/api/metrics?class=<name>` — JSON metrics feed
  - `/api/annual_change_chart/<ticker>` — PNG annual performance chart
  - `/api/annual_cashflow_chart/<ticker>` and `/api/quarterly_cashflow_chart/<ticker>` — PNG cash-flow charts

### 2. Monitoring Loop (optional, background CLI)
```bash
python3 src/main.py
```
- Rebuilds the data cache, then loops forever: when the market is open it prints each ticker/term snapshot every 60s; when closed, it sweeps once and sleeps until market open.
- Stop with Ctrl-C.

### 3. EDGAR Filing Portal (optional)
```bash
python3 src/edgar_test_server.py
```
- URL: http://127.0.0.1:5005
- Browse cached filings from `repository/10KQ/<CIK>/`.

### 4. SEC EDGAR MCP Server (optional)
```bash
cd mcp
EDGAR_IDENTITY="Your Name your@email" node sec-edgar.js
```
- Speaks MCP over stdio; wire it into an MCP-compatible client (e.g. Claude Desktop) to expose `get_cik` and `list_recent_filings` tools.

### 5. 13F Processor (utility script)
```bash
python3 skills/scripts/13f_processor.py \
  --primary  <path/to/primary.xml> \
  --holding  <path/to/holding.xml> \
  --output   repository/13f/CIK_<CIK>/<period>.json
```

## Project Structure

```
stock_insight/
├── config/                       # tkr.json, edgar_company.json
├── libs/                         # stock_analysis_lib, edgar_parser_lib, edgar_analysis_lib
├── mcp/                          # Node.js MCP server (SEC EDGAR)
├── repository/                   # Local cache: csv/, json/, 10KQ/, 13f/ (auto-created)
├── skills/                       # 13F processor skill + scripts/
└── src/
    ├── web_server.py             # Flask dashboard (port 5001)
    ├── main.py                   # Monitoring loop / data refresher
    ├── edgar_test_server.py      # EDGAR filing portal (port 5005)
    ├── static/
    └── templates/                # main.html, index.html, filing_portal.html
```

## Cross-Platform Notes

- File paths use `os.path` throughout, so the app runs on Windows, macOS, and Linux.
- The data cache directories (`repository/csv`, `repository/json`) are created on first run.
- yfinance fetches over the network — make sure outbound HTTPS is allowed.

## Troubleshooting

- **`ticker list file ... not found`** — confirm `config/tkr.json` exists at the repo root.
- **Empty charts / 404 from `/api/...`** — the ticker's data may not have downloaded yet; check `repository/csv/<TICKER>.csv` and re-run `python3 src/main.py` to force a rebuild.
- **Port already in use** — change the `app.run(... port=...)` line in `src/web_server.py` (5001) or `src/edgar_test_server.py` (5005), or stop the conflicting process.
- **SEC requests rejected** — set `EDGAR_IDENTITY` to a real name + contact email before running the MCP server.
