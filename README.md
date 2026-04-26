# stock_insight

# Stock Insight SEC Fetcher & Analyzer

This project provides tools to fetch SEC 13F filings, process the XML data into aggregated JSON, and analyze stock performance. It is designed to work with the **Antigravity IDE** using the Model Context Protocol (MCP).

## Features
- **MCP SEC Fetcher**: A custom MCP server to download 13F XMLs with the required SEC User-Agent.
- **13F Processor Skill**: An AI-powered skill to aggregate holdings by CUSIP and convert XML to JSON.
- **Stock Analysis Library**: Python utilities for analyzing price drops from All-Time Highs.

## Installation

### 1. Prerequisites
- **Node.js** (v20+)
- **Python** (v3.9+)
- **curl** (Available in your system PATH)

### 2. Python Dependencies
Install the required Python libraries:
```bash
pip install -r requirements.txt
```

### 3. MCP Server Setup (Node.js)
The project includes a local MCP server for fetching data.
```bash
cd mcp
npm install
```

### 4. Configure Antigravity IDE
To enable the `sec-fetcher` tool, ensure your project has the local MCP configuration:

1. Create/verify `.vscode/mcp.json` in the project root:
```json
{
  "mcpServers": {
    "sec-fetcher": {
      "command": "node",
      "args": ["${workspaceFolder}/mcp/sec-fetcher.js"]
    }
  }
}
```
2. Open the **MCP Servers** panel in Antigravity and click **Refresh**.

### 5. AI Skills Setup
The `skills/` directory contains AI instruction sets. Make sure this folder is indexed by your agent to enable automatic 13F processing.

## Project Structure
- `mcp/`: Contains the MCP server implementation.
- `skills/`: AI Skills and processing scripts.
- `libs/`: Core Python analysis libraries.
- `repository/`: Data storage for fetched 13F filings and CSVs.
- `tmp/`: Temporary storage for raw downloads.

## Usage
Once configured, you can tell the AI:
- *"Fetch the 13F from [URL] and save as [filename]."*
- *"Summarize the 13F files in repository/13f/CIK_1067983/."*

## License
MIT

