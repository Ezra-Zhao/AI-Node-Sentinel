# Talk Track — ai-node-sentinel-context (MCP runbook server)

Interview notes for the Landing AI / DeepLearning.AI Visiting Engineer
(ContextHub) conversation. Written to be spoken from, not read aloud.

## The 30-second version

"AI-Node-Sentinel is my GPU-fleet diagnostic agent — Python, LangChain,
Redfish telemetry, a TF-IDF runbook retriever. The failure mode I kept
seeing is that an agent asked about a fault answers from memory and gets
the vendor specifics wrong. So I took the runbook corpus the pipeline
already curates and exposed it the way an agent actually consumes
context: as an MCP server. Three small tools — search, fetch, and a
symptom-to-steps hint — over the team's own runbooks, with provenance
and severity attached. Same retrieval core also ships as a CLI, because
humans and scripts need the same answers agents do."

## Why MCP

- It is the protocol the target consumers (coding agents) already speak;
  building on the official TypeScript SDK meant the interesting work was
  the context design, not protocol plumbing.
- stdio transport for v0.1: the consumer is a local agent on an
  engineer's machine. No port, no auth surface, no deployment. HTTP is
  the right answer only once there is a shared deployment to serve —
  that is a v0.3 line in the README, deliberately not built yet.
- Tools over resources for this corpus: runbooks are queried by symptom
  and code, not browsed. Search-then-fetch respects the agent's context
  budget — summaries first, full text only for the one runbook that
  matters.

## Context curation — the design trade-offs to talk about

1. **Curation over accumulation.** 10 runbooks, each hand-condensed from
   the parent repo's knowledge base, each with severity, ordered steps,
   cautions, and an evidence checklist. The corpus being small and
   trustworthy beats it being large and plausible.
2. **Lexical retrieval, chosen on purpose.** The domain vocabulary is
   exact — XID codes, component names. A weighted keyword scorer is
   deterministic (same symptom, same answer, twice), free to run, and
   auditable: every search result carries `matched_terms`, so you can
   see *why* a runbook ranked. Embeddings are the right tool past a few
   hundred documents; the scorer sits behind the same interface so the
   swap does not change any tool contract. (This mirrors the parent
   repo's TF-IDF choice — same reasoning, second implementation.)
3. **Provenance is part of the payload.** `diagnose_hint` returns steps
   attributed to their runbook, never a merged answer. In an incident,
   "where did this step come from" is a safety question.
4. **"Never guess" as an API behavior.** No match returns an
   evidence-collection checklist and a route-to-human note. That policy
   comes straight from the parent pipeline's handling of unknown XID
   codes. A context layer that invents answers for uncovered cases is
   worse than one that admits the gap.
5. **Read-only v0.1.** No telemetry actions, no write-back. A context
   provider that can also mutate systems needs an auth/audit story
   first; sequencing that correctly is a product decision, not a
   limitation I stumbled into.

## TypeScript / engineering choices

- Official `@modelcontextprotocol/sdk` (resolved 1.32.1), `McpServer`
  high-level API with zod input schemas — schema-validated tool inputs
  for free, which matters when the caller is an LLM.
- Strict TypeScript (`strict: true`, NodeNext modules), Node 24,
  ESM throughout. Compiles clean with `npx tsc`.
- One retrieval core (`src/runbooks.ts`), two delivery surfaces:
  `src/index.ts` (stdio MCP server) and `src/cli.ts` (CLI with
  documented exit codes). The CLI is the SDK-delivery proof: same
  package, `bin` entries for both, `npm pack --dry-run` verified —
  7 files, 11.7 kB tarball.
- Verification is protocol-level, not "it started": `scripts/smoke.mjs`
  drives the real SDK client through initialize, `tools/list`, and all
  three `tools/call`s with assertions on the top hit, and the raw
  transcript is archived in `verification.log`.
- stdout discipline: the server logs to stderr only, because stdout is
  the protocol channel — the kind of detail that only bites you once.

## Honest framing — say this before they ask

"My production background is Python and Go — AI-Node-Sentinel's pipeline
is Python, and my data-center work is systems-side. TypeScript is the
stack I am deliberately adding: this project is me closing that gap in
public, on a domain I know deeply, rather than learning the language on
toy problems. What I would want reviewed hardest is the retrieval
scoring and the tool-surface design — the parts that are judgment, not
syntax."

## Likely questions and grounded answers

- **"How would this scale to thousands of runbooks?"** — The interface
  survives; the scorer does not. Swap in a hybrid lexical+embedding
  index behind `searchRunbooks`, paginate `get_runbook`, and the data
  pipeline (v0.2 plan: generate the JSON from the Python sources so
  there is one source of truth) becomes the real work. I would also add
  per-runbook ownership/freshness metadata — stale context is the
  failure mode at scale.
- **"Why not just put the runbooks in the prompt / a RAG doc store?"** —
  Because the caller is an agent with a context budget making a tool
  decision mid-task. Search-then-fetch spends tokens proportionally to
  relevance; a prompt dump spends them all, always. And MCP makes the
  same corpus available to every agent the team runs, not one app's
  prompt template.
- **"How do you know the retrieval is right?"** — Today: the smoke
  assertions (top hit for canonical queries) and `matched_terms`
  transparency. Next honest step is a small golden-set eval — symptom
  strings to expected runbook ids — run in CI. I would rather name that
  as the gap than overclaim from three queries.
- **"What would you do differently in production?"** — Auth and audit on
  any transport beyond stdio, freshness SLAs on runbook entries, and
  telemetry read-tools only behind a separate, explicitly-scoped server
  — keeping the context provider read-only by default.
