# ai-node-sentinel-mcp — TypeScript MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server (TypeScript,
official `@modelcontextprotocol/sdk`, **stdio transport**) that exposes
AI-Node-Sentinel's GPU-node diagnostic knowledge to any MCP client —
Claude Code, Claude Desktop, IDEs, or your own agent — without running
the Python pipeline.

## Tools

| Tool | Arguments | Returns |
|---|---|---|
| `lookup_xid` | `xid_code` (integer > 0) | Name, category, severity label and notes for an NVIDIA XID error code. Unknown codes return `known: false` with human-review guidance — meanings are never guessed (same policy as the Python `lookup_xid()`). |
| `list_xids` | — | All 12 codes in the lookup table, with name / category / severity. |
| `search_runbook` | `query` (string, required), `top_k` (1–10, default 2) | Top-k runbook chunks (`chunk_id`, TF-IDF cosine `score` in [0, 1], full text) from the triage knowledge base. |

Invalid input (wrong type, missing argument, empty query) is rejected
with a proper MCP error result — see the smoke test.

## Install & run

Requires Node.js ≥ 18 (developed on Node v24).

```bash
cd mcp-server-ts
npm install
npm run build     # tsc -> dist/
npm start         # node dist/index.js, speaks MCP over stdio
npm run smoke     # end-to-end JSON-RPC smoke test (test/smoke.mjs)
```

Point any MCP client at it, e.g.:

```json
{
  "mcpServers": {
    "ai-node-sentinel": {
      "command": "node",
      "args": ["/absolute/path/to/AI-Node-Sentinel/mcp-server-ts/dist/index.js"]
    }
  }
}
```

## Data: same source as the Python version — no second dataset

This server does **not** maintain its own copy of the XID table or the
runbook. The JSON files under `data/` are generated from the Python
sources by `scripts/export_data.py`:

| File | Generated from | Contents |
|---|---|---|
| `data/xid_info.json` | `../tools/xid_lookup.py` :: `XID_INFO` | 12 XID codes. The Python module seeds them from NVIDIA's public XID catalog (Release 615, <https://docs.nvidia.com/deploy/xid-errors/>), cross-checked with Google Cloud's GPU troubleshooting guide. Severity labels are this project's triage heuristics. |
| `data/knowledge_base.json` | `../rag/knowledge_base.py` :: `KNOWLEDGE_BASE` | 15 runbook chunks (clean-room project text). The Python source defines two chunk ids twice; the export collapses duplicates exactly like Python dict semantics — last definition wins. |

The exporter parses the Python files with `ast` + `ast.literal_eval`
(it does not import/execute them). To refresh after the Python data
changes:

```bash
npm run export-data && npm run build
```

## Relationship to the Python version

- **Same data, same semantics.** `lookup_xid` mirrors
  `tools.xid_lookup.lookup_xid()` (including the unknown-code policy);
  `search_runbook` is a faithful port of `rag/retriever.py` — same
  tokenizer, same smoothed IDF, same cosine scoring. A 5-query parity
  check against the Python retriever produced identical rankings and
  scores (see `VERIFICATION.md`).
- **Different role.** The Python package is the full pipeline (telemetry
  ingest → triage decision tree → reports). This server is a read-only
  knowledge interface: lookup + retrieval only, no triage decisions, no
  telemetry, no LLM step. It is an add-on subproject; the Python code is
  untouched and does not depend on it.

## Layout

```
mcp-server-ts/
├── package.json / tsconfig.json
├── scripts/export_data.py   # Python sources -> data/*.json (with provenance headers)
├── data/                    # generated JSON (committed; regenerate, don't hand-edit)
├── src/
│   ├── index.ts             # MCP server + tool definitions (stdio)
│   ├── data.ts              # typed loaders for data/*.json
│   └── retriever.ts         # TF-IDF retriever, port of rag/retriever.py
├── test/smoke.mjs           # raw JSON-RPC smoke test (no client library)
└── VERIFICATION.md          # recorded build/smoke/parity run output
```

## License

MIT — same as the parent repository.
