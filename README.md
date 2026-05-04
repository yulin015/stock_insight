# Stock Insight Pro

A professional stock analysis dashboard for monitoring portfolio performance and market sectors.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for the MCP server)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yulin015/stock_insight.git
   cd stock_insight
   ```

2. **Install Python dependencies:**
   - **Windows:**
     ```bash
     python -m pip install -r requirements.txt
     ```
   - **macOS/Linux:**
     ```bash
     pip install -r requirements.txt
     ```

3. **Install Node.js dependencies (Optional - for MCP server):**
   ```bash
   cd mcp
   npm install
   cd ..
   ```

## Running the Application

### 1. Start the Web Dashboard
Navigate to the `src` directory and run the web server:

- **Windows:**
  ```bash
  python src/web_server.py
  ```
- **macOS/Linux:**
  ```bash
  python3 src/web_server.py
  ```

The dashboard will be available at [http://127.0.0.1:5001](http://127.0.0.1:5001).

### 2. Start the Monitoring Loop (Optional)
To run the background monitoring service:

- **Windows:**
  ```bash
  python src/main.py
  ```
- **macOS/Linux:**
  ```bash
  python3 src/main.py
  ```

## Project Structure

- `src/`: Main application code (Web server, monitoring loop, templates).
- `libs/`: Core stock analysis logic and data processing.
- `repository/`: Local data cache (CSV and JSON files).
- `mcp/`: Model Context Protocol server for SEC 13F data fetching.
- `skills/`: AI agent skill definitions and processing scripts.

## Cross-Platform Support

This project is designed to run on Windows, macOS, and Linux. It uses `os.path` for robust file path handling across different operating systems.
