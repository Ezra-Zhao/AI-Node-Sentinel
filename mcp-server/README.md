# ai-node-sentinel-context

An MCP server (plus a CLI twin) that exposes the diagnostic runbooks of
[AI-Node-Sentinel](..) — a GPU-node failure triage agent — as curated,
callable context for coding and ops agents.

The problem it solves is the one ContextHub-style infrastructure exists
for: an agent asked "the training job died and dmesg says Xid 79, what do
I do?" will otherwise answer from parametric memory — plausible, generic,
and wrong in the ways that matter (it will happily tell you to RMA a card
whose real problem is a lost PSU feed). This server gives the agent the
team's actual runbook instead: versioned, severity-labeled, with ordered
steps, explicit cautions, and a list of evidence to collect before acting.

## Tools

| Tool | Input | Output |
|---|---|---|
| `search_runbooks` | `query` (keywords), optional `limit` | Ranked runbook matches: id, title, severity, score, matched terms, summary |
| `get_runbook` | `id` | Full runbook: summary, ordered steps, cautions, evidence to collect |
| `diagnose_hint` | `symptom` (free text) | Top matching runbooks with first steps, cautions, evidence; no match = collect evidence and route to a human |

The runbook set (`data/runbooks.json`, 10 entries) is a condensed,
hand-written edition of the parent repo's diagnostic knowledge: the XID
runbooks from `rag/knowledge_base.py` (XID 79, 48, 92, 74, 119/120,
13/31, 62/63/64, 45), the Redfish thermal/power interpretation chunk, and
the two meta-rules (repeat-event escalation, unknown-code handling).
Content stays inside that knowledge system on purpose — this is curation
of an existing corpus, not a new invention.

## Why this shape — product decisions

**Why MCP, and why stdio.** The consumers are agents running on an
engineer's machine, mid-incident or mid-coding-session. MCP is the
protocol those agents already speak, and stdio transport means zero
deployment: no port, no auth surface, no service to babysit. An HTTP
transport is a team-deployment question, not a v0.1 question.

**Why lexical retrieval, not embeddings.** The corpus is a dozen curated
documents and the decisive signals are exact tokens — XID codes, "drain",
"NVLink", "Redfish". A weighted keyword scorer (exact XID match >
curated keyword > symptom phrase > body term) is deterministic — the
same symptom returns the same guidance twice, which is what you want at
3am — costs nothing, and needs no API key or index build. This mirrors
the parent repo's TF-IDF retriever, kept behind the same
search-then-fetch interface so an embedding index can replace the scorer
later without touching a single tool contract.

**Why search and fetch are separate tools.** Context is a budget.
`search_runbooks` returns summaries so the agent can pick; `get_runbook`
spends tokens on full text only for the runbook that matters.
`diagnose_hint` exists for the common case where the caller has a
symptom, not a keyword — it returns steps *attributed to their runbook*,
never a merged, unattributed answer.

**The "never guess" rule is a feature.** For symptoms with no runbook
match, `diagnose_hint` returns an evidence-collection checklist and a
route-to-human note. That is inherited from the parent pipeline's policy
for unknown XID codes, and it is the line between a context provider and
a hallucination amplifier.

**What was cut from v0.1** (deliberately, in order):

- No live telemetry tools (no real Redfish polling, no dmesg tail) —
  context first; acting on live systems is a different trust level.
- No write-back (no "file this incident" tool) — v0.1 is read-only by
  design; a context provider that can also mutate state needs an auth
  and audit story first.
- No embedding/semantic search — unjustified at this corpus size.
- No HTTP transport, no auth, no multi-tenancy — no shared deployment
  exists yet to justify them.
- No auto-generated runbook content — every entry is human-curated from
  the parent repo's knowledge base; generation is how runbooks rot.

## Version plan

- **v0.1 (this)** — stdio MCP server, 3 read-only tools, 10 curated
  runbooks, CLI twin over the same retrieval core, protocol-level smoke
  test (`scripts/smoke.mjs`, results in `verification.log`).
- **v0.2** — runbook data generated from the parent repo's Python sources
  by a build script (single source of truth, no hand-synced copies);
  resources/prompts surface in addition to tools; incident-shaped input
  (structured XID + node context) for `diagnose_hint`.
- **v0.3** — optional streamable-HTTP transport behind a flag for shared
  team deployment, with token auth; retrieval scorer swapped for a
  hybrid lexical+embedding index if the corpus passes a few hundred
  entries (interface unchanged).

## Install & run

Requires Node >= 18. From this directory:

```bash
npm install
npm run build        # tsc -> dist/
node scripts/smoke.mjs   # optional: protocol-level smoke test
```

Run the MCP server (stdio):

```bash
node dist/index.js
```

Register it with an MCP client using a local path — example client
config:

```json
{
  "mcpServers": {
    "ai-node-sentinel-context": {
      "command": "node",
      "args": ["/absolute/path/to/AI-Node-Sentinel/mcp-server/dist/index.js"]
    }
  }
}
```

Or via npx against the local package directory (no publish involved):

```bash
npx --prefix /absolute/path/to/AI-Node-Sentinel/mcp-server ai-node-sentinel-context
```

Use the CLI twin (same retrieval core, JSON output):

```bash
node dist/cli.js search "xid 79"
node dist/cli.js get xid-79-bus
node dist/cli.js diagnose "gpu disappeared from nvidia-smi"
node dist/cli.js list
```

## Verification

`verification.log` in this directory records a real run: the official
SDK client connecting over stdio, `tools/list`, all three `tools/call`s
with full responses, plus CLI invocations (including the not-found exit
code). Reproduce with `npm run build && node scripts/smoke.mjs`.

## How this maps to ContextHub

ContextHub's premise is that agents fail on missing or stale context,
not on reasoning. This project is that premise applied to one concrete
corpus: a fleet's diagnostic runbooks, curated into a small, typed,
callable surface with provenance (every step names its runbook),
severity, and explicit non-goals (never guess). The engineering taste is
the same — curation over accumulation, small sharp tools over one giant
context dump, determinism where the domain has exact vocabulary.
