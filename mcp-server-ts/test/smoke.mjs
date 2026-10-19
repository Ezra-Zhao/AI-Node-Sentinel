#!/usr/bin/env node
/**
 * Smoke test for the ai-node-sentinel MCP server.
 *
 * Spawns the built server (dist/index.js) over stdio and speaks raw
 * JSON-RPC to it — no MCP client library involved:
 *   1. initialize
 *   2. notifications/initialized
 *   3. tools/list
 *   4. tools/call lookup_xid { xid_code: 48 }     (known code)
 *   5. tools/call lookup_xid { xid_code: 999 }    (unknown code -> known=false)
 *   6. tools/call list_xids {}
 *   7. tools/call search_runbook { query: "XID 79 GPU fallen off the bus power thermal" }
 *   8. tools/call lookup_xid { xid_code: "48" }  (wrong type -> must error)
 *   9. tools/call lookup_xid {}                  (missing arg -> must error)
 *  10. tools/call search_runbook { query: "" }   (empty query -> must error)
 *
 * Usage: npm run build && npm run smoke
 * Exits 0 only if every check passes.
 */
import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const serverPath = join(dirname(fileURLToPath(import.meta.url)), "..", "dist", "index.js");
const child = spawn(process.execPath, [serverPath], { stdio: ["pipe", "pipe", "pipe"] });
child.stderr.on("data", (d) => process.stderr.write(`[server stderr] ${d}`));

let buffer = "";
const pending = new Map();
let nextId = 1;

child.stdout.on("data", (chunk) => {
  buffer += chunk.toString();
  let idx;
  while ((idx = buffer.indexOf("\n")) >= 0) {
    const line = buffer.slice(0, idx).trim();
    buffer = buffer.slice(idx + 1);
    if (!line) continue;
    const msg = JSON.parse(line);
    if (msg.id !== undefined && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  }
});

function request(method, params) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, resolve);
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
    setTimeout(() => reject(new Error(`timeout waiting for ${method}`)), 10_000);
  });
}

function notify(method, params) {
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method, params }) + "\n");
}

let failures = 0;
function check(label, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failures++;
}

function textOf(result) {
  return result?.content?.map((c) => c.text ?? "").join("\n") ?? "";
}

try {
  const init = await request("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "smoke-test", version: "0.1.0" },
  });
  check(
    "initialize",
    init.result?.serverInfo?.name === "ai-node-sentinel",
    `serverInfo=${JSON.stringify(init.result?.serverInfo)} protocol=${init.result?.protocolVersion}`,
  );
  notify("notifications/initialized", {});

  const list = await request("tools/list", {});
  const names = (list.result?.tools ?? []).map((t) => t.name).sort();
  check(
    "tools/list",
    JSON.stringify(names) === JSON.stringify(["list_xids", "lookup_xid", "search_runbook"]),
    `tools=${names.join(",")}`,
  );
  const lookupTool = list.result.tools.find((t) => t.name === "lookup_xid");
  check(
    "tools/list lookup_xid has full input schema",
    ["integer", "number"].includes(lookupTool?.inputSchema?.properties?.xid_code?.type) &&
      (lookupTool.inputSchema.required ?? []).includes("xid_code"),
    `schema=${JSON.stringify(lookupTool?.inputSchema)}`,
  );

  const call48 = await request("tools/call", {
    name: "lookup_xid",
    arguments: { xid_code: 48 },
  });
  const body48 = JSON.parse(textOf(call48.result));
  check(
    "tools/call lookup_xid 48",
    body48.known === true &&
      body48.name === "Double-bit ECC error (uncorrectable)" &&
      body48.severity === "critical" &&
      body48.category === "memory_ecc",
    `name="${body48.name}" severity=${body48.severity}`,
  );

  const call999 = await request("tools/call", {
    name: "lookup_xid",
    arguments: { xid_code: 999 },
  });
  const body999 = JSON.parse(textOf(call999.result));
  check(
    "tools/call lookup_xid 999 (unknown, never guessed)",
    body999.known === false && body999.severity === "unknown",
    `known=${body999.known} severity=${body999.severity}`,
  );

  const callList = await request("tools/call", { name: "list_xids", arguments: {} });
  const bodyList = JSON.parse(textOf(callList.result));
  check(
    "tools/call list_xids",
    bodyList.count === 12 && bodyList.codes.some((c) => c.xid_code === 79),
    `count=${bodyList.count}`,
  );

  const callSearch = await request("tools/call", {
    name: "search_runbook",
    arguments: { query: "XID 79 GPU fallen off the bus power thermal", top_k: 2 },
  });
  const bodySearch = JSON.parse(textOf(callSearch.result));
  const topChunk = bodySearch.results?.[0]?.chunk_id;
  check(
    "tools/call search_runbook (TF-IDF top-1 for XID 79 query)",
    topChunk === "xid-79-bus" && bodySearch.results[0].score > 0,
    `top=${topChunk} score=${bodySearch.results?.[0]?.score}`,
  );

  const badType = await request("tools/call", {
    name: "lookup_xid",
    arguments: { xid_code: "48" },
  });
  check(
    "tools/call lookup_xid with string arg errors",
    Boolean(badType.error) || badType.result?.isError === true,
    badType.error ? `error=${badType.error.message?.slice(0, 80)}` : "isError=true",
  );

  const missing = await request("tools/call", { name: "lookup_xid", arguments: {} });
  check(
    "tools/call lookup_xid with missing arg errors",
    Boolean(missing.error) || missing.result?.isError === true,
    missing.error ? `error=${missing.error.message?.slice(0, 80)}` : "isError=true",
  );

  const emptyQuery = await request("tools/call", {
    name: "search_runbook",
    arguments: { query: "" },
  });
  check(
    "tools/call search_runbook with empty query errors",
    Boolean(emptyQuery.error) || emptyQuery.result?.isError === true,
    emptyQuery.error ? `error=${emptyQuery.error.message?.slice(0, 80)}` : "isError=true",
  );
} catch (err) {
  check("smoke run completed without exception", false, String(err));
} finally {
  child.stdin.end();
  child.kill();
}

console.log(failures === 0 ? "\nSMOKE: ALL CHECKS PASSED" : `\nSMOKE: ${failures} CHECK(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);
