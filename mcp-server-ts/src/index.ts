#!/usr/bin/env node
/**
 * AI-Node-Sentinel MCP server (TypeScript, stdio transport).
 *
 * Exposes the same diagnostic knowledge as the Python pipeline to any
 * MCP client (Claude Code, Claude Desktop, IDEs, ...):
 *
 *   lookup_xid      NVIDIA XID code -> name / category / severity / notes
 *                   (data: tools/xid_lookup.py :: XID_INFO, via export script)
 *   list_xids       every XID code present in the lookup table
 *   search_runbook  keyword query -> top-k runbook chunks, ranked with the
 *                   same TF-IDF algorithm as rag/retriever.py
 *                   (data: rag/knowledge_base.py :: KNOWLEDGE_BASE)
 *
 * Policy carried over from the Python code: unknown XID codes are never
 * guessed at — lookup_xid reports known=false and the runbook's
 * "unknown-xid" guidance (route to human review).
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import { KNOWLEDGE_BASE, XID_INFO, lookupXid } from "./data.js";
import { TfidfRetriever } from "./retriever.js";

const retriever = new TfidfRetriever(KNOWLEDGE_BASE);

const server = new McpServer({
  name: "ai-node-sentinel",
  version: "0.1.0",
});

server.registerTool(
  "lookup_xid",
  {
    title: "Look up an NVIDIA XID error code",
    description:
      "Look up an NVIDIA XID error code in the AI-Node-Sentinel table " +
      "(sourced from NVIDIA's public XID catalog, Release 615). Returns the " +
      "error name, category, this project's severity label, and notes. " +
      "Unknown codes return known=false — their meaning is never guessed.",
    inputSchema: {
      xid_code: z
        .number()
        .int()
        .positive()
        .describe("The numeric XID error code, e.g. 48 for a double-bit ECC error."),
    },
  },
  async ({ xid_code }) => {
    const info = lookupXid(xid_code);
    if (info === undefined) {
      const payload = {
        xid_code,
        known: false,
        severity: "unknown",
        guidance:
          "XID code not in the lookup table. Per project policy: do not guess. " +
          "Mark severity unknown, route to human review, and record the raw " +
          "dmesg line so the code can be researched against vendor documentation.",
      };
      return {
        content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
        structuredContent: payload,
      };
    }
    const payload = { xid_code, known: true, ...info };
    return {
      content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
      structuredContent: payload,
    };
  },
);

server.registerTool(
  "list_xids",
  {
    title: "List all known XID codes",
    description:
      "List every NVIDIA XID code present in the lookup table, with its name " +
      "and severity label. Takes no arguments.",
    inputSchema: {},
  },
  async () => {
    const codes = [...XID_INFO.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([xid_code, info]) => ({
        xid_code,
        name: info.name,
        category: info.category,
        severity: info.severity,
      }));
    const payload = { count: codes.length, codes };
    return {
      content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
      structuredContent: payload,
    };
  },
);

server.registerTool(
  "search_runbook",
  {
    title: "Search the triage runbook",
    description:
      "Search the AI-Node-Sentinel runbook knowledge base (the same chunks " +
      "the Python RAG pipeline retrieves) with TF-IDF cosine similarity — " +
      "the same algorithm and parameters as rag/retriever.py. Returns the " +
      "top-k chunk ids, scores in [0, 1], and full chunk texts.",
    inputSchema: {
      query: z
        .string()
        .min(1)
        .describe(
          "Free-text query, e.g. \"XID 48 double-bit ECC drain\" or \"nvlink fabric error\".",
        ),
      top_k: z
        .number()
        .int()
        .min(1)
        .max(10)
        .default(2)
        .describe("How many chunks to return (default 2, as in the Python retriever)."),
    },
  },
  async ({ query, top_k }) => {
    if (query.trim().length === 0) {
      throw new Error("query must not be empty or whitespace only");
    }
    const results = retriever.retrieve(query, top_k).map(([chunk_id, score]) => ({
      chunk_id,
      score: Number(score.toFixed(4)),
      text: KNOWLEDGE_BASE[chunk_id],
    }));
    const payload = { query, count: results.length, results };
    return {
      content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
      structuredContent: payload,
    };
  },
);

async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // stdout is the JSON-RPC channel — log to stderr only.
  console.error("ai-node-sentinel MCP server running on stdio");
}

main().catch((err) => {
  console.error("fatal:", err);
  process.exit(1);
});
