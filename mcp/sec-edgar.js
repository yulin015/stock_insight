import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

/**
 * Custom MCP Server for SEC EDGAR interaction.
 */
const server = new Server(
  {
    name: "sec-edgar",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

const USER_AGENT = process.env.EDGAR_IDENTITY || "Yulin Chen chenyulin.ca@gmail.com";
const SEC_DATA_BASE = "https://data.sec.gov";

/**
 * Fetch JSON via global fetch (follows redirects, checks status + content-type).
 */
async function fetchJson(url) {
  const res = await fetch(url, {
    headers: { "User-Agent": USER_AGENT, "Accept": "application/json" },
    redirect: "follow",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status} from ${url}: ${body.slice(0, 200)}`);
  }
  const ctype = res.headers.get("content-type") || "";
  if (!ctype.toLowerCase().includes("json")) {
    const body = await res.text();
    throw new Error(`Expected JSON from ${url} but got "${ctype}": ${body.slice(0, 200)}`);
  }
  return res.json();
}

/**
 * Yield each submissions page (newest-first) for a CIK. The primary
 * submissions JSON exposes `filings.recent`; older filings live in
 * separate paginated files listed under `filings.files`.
 */
async function* iterFilingPages(paddedCik) {
  const primary = await fetchJson(`${SEC_DATA_BASE}/submissions/CIK${paddedCik}.json`);
  yield primary.filings.recent;
  for (const page of primary.filings.files || []) {
    yield await fetchJson(`${SEC_DATA_BASE}/submissions/${page.name}`);
  }
}

/**
 * Define tools.
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "get_cik",
        description: "Get the CIK for a given ticker symbol.",
        inputSchema: {
          type: "object",
          properties: {
            ticker: { type: "string", description: "The stock ticker symbol (e.g., AAPL)" },
          },
          required: ["ticker"],
        },
      },
      {
        name: "list_recent_filings",
        description: "List recent filings for a company by CIK or ticker.",
        inputSchema: {
          type: "object",
          properties: {
            ticker: { type: "string", description: "The stock ticker symbol" },
            cik: { type: "string", description: "The 10-digit CIK (optional if ticker is provided)" },
            form: { type: "string", description: "Optional: Filter by form type (e.g., '10-K', '10-Q', '13F')" },
            limit: { type: "number", description: "Number of filings to return (default 10, max 100)" },
          },
        },
      },
    ],
  };
});

/**
 * Handle tool calls.
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "get_cik") {
    const ticker = args.ticker.toUpperCase();
    try {
      const data = await fetchJson("https://www.sec.gov/files/company_tickers.json");
      const entry = Object.values(data).find(c => c.ticker === ticker);
      if (entry) {
        return {
          content: [{ type: "text", text: `CIK for ${ticker} is ${entry.cik_str.toString().padStart(10, '0')} (${entry.title})` }],
        };
      }
      return { content: [{ type: "text", text: `Ticker ${ticker} not found.` }], isError: true };
    } catch (error) {
      return { content: [{ type: "text", text: `Error: ${error.message}` }], isError: true };
    }
  }

  if (name === "list_recent_filings") {
    let cik = args.cik;
    const ticker = args.ticker?.toUpperCase();
    const formFilter = args.form?.toUpperCase();
    const limit = args.limit || 10;

    if (!cik && ticker) {
      const data = await fetchJson("https://www.sec.gov/files/company_tickers.json");
      const entry = Object.values(data).find(c => c.ticker === ticker);
      if (entry) {
        cik = entry.cik_str.toString().padStart(10, '0');
      } else {
        return { content: [{ type: "text", text: `Ticker ${ticker} not found.` }], isError: true };
      }
    }

    if (!cik) {
      return { content: [{ type: "text", text: "Either ticker or cik must be provided." }], isError: true };
    }

    const paddedCik = cik.toString().padStart(10, '0');
    try {
      const results = [];
      pages: for await (const page of iterFilingPages(paddedCik)) {
        for (let i = 0; i < page.accessionNumber.length; i++) {
          if (formFilter && page.form[i].toUpperCase() !== formFilter) {
            continue;
          }
          results.push({
            accession: page.accessionNumber[i],
            form: page.form[i],
            filingDate: page.filingDate[i],
            primaryDocument: page.primaryDocument[i],
            url: `https://www.sec.gov/Archives/edgar/data/${parseInt(cik)}/${page.accessionNumber[i].replace(/-/g, '')}/${page.primaryDocument[i]}`
          });
          if (results.length >= limit) break pages;
        }
      }

      return {
        content: [{ type: "text", text: JSON.stringify(results, null, 2) }],
      };
    } catch (error) {
      return { content: [{ type: "text", text: `Error fetching filings: ${error.message}` }], isError: true };
    }
  }

  throw new Error(`Tool not found: ${name}`);
});

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("SEC EDGAR MCP server running on stdio");
