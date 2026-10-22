/**
 * Smoke test: real MCP protocol exchange over stdio against the built
 * server (dist/index.js), using the official SDK client.
 *
 * Covers the full handshake path a real client performs:
 *   initialize (inside client.connect) -> tools/list -> tools/call x3
 * Prints every request/response so the run can be archived verbatim
 * as verification evidence (see verification.log).
 * Exits non-zero on any failure.
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const serverPath = join(here, "..", "dist", "index.js");

function show(label, value) {
  console.log(`\n===== ${label} =====`);
  console.log(typeof value === "string" ? value : JSON.stringify(value, null, 2));
}

function assert(cond, message) {
  if (!cond) throw new Error(`ASSERT FAILED: ${message}`);
}

const transport = new StdioClientTransport({
  command: process.execPath,
  args: [serverPath],
});

const client = new Client({ name: "sentinel-smoke", version: "0.1.0" });

try {
  // initialize handshake happens inside connect()
  await client.connect(transport);
  show(
    "initialize",
    `connected; server info: ${JSON.stringify(client.getServerVersion())}`,
  );

  const tools = await client.listTools();
  show("tools/list response", tools);
  const names = tools.tools.map((t) => t.name).sort();
  assert(
    JSON.stringify(names) ===
      JSON.stringify(["diagnose_hint", "get_runbook", "search_runbooks"]),
    `expected exactly the 3 runbook tools, got ${names.join(",")}`,
  );

  const search = await client.callTool({
    name: "search_runbooks",
    arguments: { query: "xid 79", limit: 3 },
  });
  show("tools/call search_runbooks {query:'xid 79', limit:3}", search);
  const searchJson = JSON.parse(search.content[0].text);
  assert(searchJson.count >= 1, "search_runbooks returned no results");
  assert(
    searchJson.results[0].id === "xid-79-bus",
    `search_runbooks top hit should be xid-79-bus, got ${searchJson.results[0].id}`,
  );

  const get = await client.callTool({
    name: "get_runbook",
    arguments: { id: "xid-79-bus" },
  });
  show("tools/call get_runbook {id:'xid-79-bus'}", get);
  const getJson = JSON.parse(get.content[0].text);
  assert(getJson.id === "xid-79-bus", "get_runbook returned wrong runbook");
  assert(
    Array.isArray(getJson.steps) && getJson.steps.length >= 3,
    "get_runbook should include ordered steps",
  );

  const diag = await client.callTool({
    name: "diagnose_hint",
    arguments: { symptom: "gpu disappeared from nvidia-smi after xid 79" },
  });
  show(
    "tools/call diagnose_hint {symptom:'gpu disappeared from nvidia-smi after xid 79'}",
    diag,
  );
  const diagJson = JSON.parse(diag.content[0].text);
  assert(diagJson.matches.length >= 1, "diagnose_hint returned no matches");
  assert(
    diagJson.matches[0].runbook_id === "xid-79-bus",
    `diagnose_hint top match should be xid-79-bus, got ${diagJson.matches[0].runbook_id}`,
  );
  assert(
    diagJson.matches[0].first_steps.length >= 1,
    "diagnose_hint should include first steps",
  );

  show("SMOKE RESULT", "PASS - initialize, tools/list, and all 3 tools OK");
} catch (err) {
  console.error("\nSMOKE RESULT: FAIL");
  console.error(err);
  process.exitCode = 1;
} finally {
  await client.close().catch(() => {});
}
