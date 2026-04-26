import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { exec } from "child_process";
import { promisify } from "util";

const execPromise = promisify(exec);

/**
 * Custom MCP Server for fetching SEC 13F filings.
 */
const server = new Server(
  {
    name: "sec-fetcher",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * Define the tools available on this server.
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "fetch_sec_13f",
        description: "Fetches a 13F XML file from the SEC EDGAR database using a specific User-Agent.",
        inputSchema: {
          type: "object",
          properties: {
            url: {
              type: "string",
              description: "The full URL to the SEC XML file (e.g., primary_doc.xml)",
            },
            output_filename: {
              type: "string",
              description: "The name of the file to save locally (e.g., '2025-12-31_primary.xml')",
            },
          },
          required: ["url", "output_filename"],
        },
      },
    ],
  };
});

/**
 * Handle tool calls.
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "fetch_sec_13f") {
    const { url, output_filename } = request.params.arguments;
    const userAgent = "YulinChen chenyulin.ca@email.com";
    
    // Command exactly as requested by the user
    const cmd = `curl -s -H "User-Agent: ${userAgent}" -o "${output_filename}" "${url}"`;
    
    try {
      await execPromise(cmd);
      return {
        content: [
          {
            type: "text",
            text: `Successfully fetched and saved to ${output_filename}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error fetching XML: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
  throw new Error(`Tool not found: ${request.params.name}`);
});

/**
 * Start the server using Stdio transport.
 */
const transport = new StdioServerTransport();
await server.connect(transport);
console.error("SEC Fetcher MCP server running on stdio");
