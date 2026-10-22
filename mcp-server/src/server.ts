/**
 * MCP server factory: exposes the AI-Node-Sentinel diagnostic runbooks as
 * Model Context Protocol tools so a coding/ops agent can pull curated,
 * versioned fault context instead of relying on parametric memory.
 *
 * Tools:
 *   search_runbooks  keyword search over the runbook set (titles + scores)
 *   get_runbook      full text of one runbook by id
 *   diagnose_hint    symptom text -> ranked runbooks with first steps
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  diagnoseHint,
  getRunbook,
  listRunbookIds,
  searchRunbooks,
} from "./runbooks.js";

function jsonContent(value: unknown): {
  content: { type: "text"; text: string }[];
} {
  return {
    content: [{ type: "text", text: JSON.stringify(value, null, 2) }],
  };
}

export function createServer(): McpServer {
  const server = new McpServer({
    name: "ai-node-sentinel-context",
    version: "0.1.0",
  });

  server.registerTool(
    "search_runbooks",
    {
      title: "Search diagnostic runbooks",
      description:
        "Search the AI-Node-Sentinel GPU diagnostic runbook set by keyword " +
        "(XID code, component, symptom term). Returns ranked matches with " +
        "id, title, severity, score, matched terms, and a summary. " +
        "Use get_runbook with a returned id to fetch the full text.",
      inputSchema: {
        query: z
          .string()
          .min(1)
          .describe("Keyword query, e.g. 'xid 79' or 'ecc memory'"),
        limit: z
          .number()
          .int()
          .min(1)
          .max(20)
          .optional()
          .describe("Max results to return (default 5)"),
      },
    },
    async ({ query, limit }) => {
      const hits = searchRunbooks(query, limit ?? 5);
      return jsonContent({ query, count: hits.length, results: hits });
    },
  );

  server.registerTool(
    "get_runbook",
    {
      title: "Get one runbook in full",
      description:
        "Return the full text of one AI-Node-Sentinel runbook by id: " +
        "summary, ordered steps, cautions, and evidence to collect. " +
        `Known ids: ${listRunbookIds().join(", ")}.`,
      inputSchema: {
        id: z.string().min(1).describe("Runbook id, e.g. 'xid-79-bus'"),
      },
    },
    async ({ id }) => {
      const rb = getRunbook(id);
      if (!rb) {
        return {
          isError: true,
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                {
                  error: `Unknown runbook id: ${id}`,
                  known_ids: listRunbookIds(),
                },
                null,
                2,
              ),
            },
          ],
        };
      }
      return jsonContent(rb);
    },
  );

  server.registerTool(
    "diagnose_hint",
    {
      title: "Symptom to troubleshooting steps",
      description:
        "Given a free-text symptom (e.g. 'gpu disappeared from nvidia-smi' " +
        "or 'xid 79 in dmesg'), return the best-matching runbooks with " +
        "their first troubleshooting steps, cautions, and evidence to " +
        "collect. No match means: collect evidence and route to a human — " +
        "this tool never invents a diagnosis.",
      inputSchema: {
        symptom: z
          .string()
          .min(1)
          .describe("Free-text symptom description"),
      },
    },
    async ({ symptom }) => jsonContent(diagnoseHint(symptom)),
  );

  return server;
}
