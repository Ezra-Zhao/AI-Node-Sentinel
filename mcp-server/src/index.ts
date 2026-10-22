#!/usr/bin/env node
/**
 * stdio entry point for the AI-Node-Sentinel MCP server.
 *
 * stdio transport is the v0.1 choice on purpose: the consumers of this
 * context are local coding agents (the ContextHub use case — an agent on
 * an engineer's machine asking "what does XID 79 mean in OUR runbook?").
 * stdio needs no port, no auth surface, and no deployment; an HTTP
 * transport is a v0.2 candidate once a shared/team deployment exists.
 *
 * stdout is the protocol channel — all logging goes to stderr.
 */
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("ai-node-sentinel-context MCP server running on stdio");
}

main().catch((err: unknown) => {
  console.error("Fatal error starting MCP server:", err);
  process.exit(1);
});
