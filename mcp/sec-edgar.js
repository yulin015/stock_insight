import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import https from "https";

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

/**
 * Helper to fetch JSON from URL
 */
function fetchJson(url) {
  console.error(`Fetching: ${url}`);
  return new Promise((resolve, reject) => {
    https.get(url, {
      headers: { "User-Agent": USER_AGENT }
    }, (res) => {
      if (res.statusCode !== 200) {
        res.resume(); // Consume response data to free up memory
        reject(new Error(`HTTP ${res.statusCode}: Failed to fetch ${url}`));
        return;
      }
      let data = "";
      res.on("data", (chunk) => { data += chunk; });
      res.on("end", () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error(`Failed to parse response from ${url}: ${e.message}`));
        }
      });
    }).on("error", (err) => {
      reject(err);
    });
  });
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
      const primaryData = await fetchJson(`https://data.sec.gov/submissions/CIK${paddedCik}.json`);
      const results = [];
      
      const processRecent = (recent) => {
        for (let i = 0; i < recent.accessionNumber.length; i++) {
          if (formFilter && recent.form[i].toUpperCase() !== formFilter) continue;
          
          results.push({
            accession: recent.accessionNumber[i],
            form: recent.form[i],
            filingDate: recent.filingDate[i],
            reportDate: recent.reportDate[i],
            primaryDocument: recent.primaryDocument[i],
            url: `https://www.sec.gov/Archives/edgar/data/${parseInt(cik)}/${recent.accessionNumber[i].replace(/-/g, '')}/${recent.primaryDocument[i]}`
          });
          if (results.length >= limit) return true;
        }
        return false;
      };

      // Process most recent
      if (processRecent(primaryData.filings.recent)) {
        return { content: [{ type: "text", text: JSON.stringify(results, null, 2) }] };
      }

      // Process historical files if available
      const historicalFiles = primaryData.filings.files || [];
      for (const file of historicalFiles) {
        const historicalData = await fetchJson(`https://data.sec.gov/submissions/${file.name}`);
        // Historical files are flat, not nested under filings.recent
        if (processRecent(historicalData)) {
          break;
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
