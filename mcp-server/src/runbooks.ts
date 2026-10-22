/**
 * Runbook store + lexical retrieval for the AI-Node-Sentinel MCP server.
 *
 * Design note (deliberate v0.1 choice): retrieval here is a transparent
 * weighted-keyword scorer, NOT embeddings. The corpus is a dozen curated
 * runbooks and the decisive signals are exact tokens — XID codes, "drain",
 * "NVLink", "Redfish" — where lexical match beats semantic blur, is fully
 * deterministic (the same symptom returns the same guidance twice), and
 * needs no API key, no GPU, and no index build. This mirrors the reasoning
 * behind the parent repo's TF-IDF retriever (rag/retriever.py). If the
 * corpus grows past a few hundred entries, swap `scoreRunbook` for an
 * embedding index behind this same interface.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export interface Runbook {
  id: string;
  title: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  xids: number[];
  keywords: string[];
  symptoms: string[];
  summary: string;
  steps: string[];
  cautions: string[];
  evidence_to_collect: string[];
}

export interface SearchHit {
  id: string;
  title: string;
  severity: Runbook["severity"];
  score: number;
  matched_terms: string[];
  summary: string;
}

function loadRunbooks(): Runbook[] {
  // Compiled output lives in dist/, data lives at the package root:
  // dist/runbooks.js -> ../data/runbooks.json
  const here = dirname(fileURLToPath(import.meta.url));
  const dataPath = join(here, "..", "data", "runbooks.json");
  const raw = readFileSync(dataPath, "utf-8");
  const parsed = JSON.parse(raw) as Runbook[];
  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error(`Runbook data file is empty or malformed: ${dataPath}`);
  }
  return parsed;
}

export const RUNBOOKS: Runbook[] = loadRunbooks();

const byId = new Map<string, Runbook>(RUNBOOKS.map((r) => [r.id, r]));

export function getRunbook(id: string): Runbook | undefined {
  return byId.get(id);
}

export function listRunbookIds(): string[] {
  return RUNBOOKS.map((r) => r.id);
}

/** Lowercase alphanumeric tokens, mirroring rag/retriever.py's tokenizer. */
export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((t) => t.length > 1);
}

/**
 * Score one runbook against query tokens.
 * Weights encode curation intent: an exact XID code or a curated keyword is
 * the strongest signal; symptom phrases next; free text in the body last.
 */
function scoreRunbook(
  rb: Runbook,
  queryTokens: string[],
  rawQuery: string,
): { score: number; matched: string[] } {
  let score = 0;
  const matched = new Set<string>();
  const q = rawQuery.toLowerCase();

  // Exact XID code mention, e.g. "xid 79" or a bare "79" next to "xid".
  for (const code of rb.xids) {
    if (new RegExp(`\\b${code}\\b`).test(q) && q.includes("xid")) {
      score += 10;
      matched.add(`xid-${code}`);
    }
  }

  const keywordSet = new Set(rb.keywords.flatMap((k) => tokenize(k)));
  const symptomTokens = new Set(rb.symptoms.flatMap((s) => tokenize(s)));
  const bodyTokens = new Set(
    tokenize(`${rb.title} ${rb.summary} ${rb.steps.join(" ")}`),
  );
  const titleTokens = new Set(tokenize(rb.title));

  for (const tok of queryTokens) {
    if (keywordSet.has(tok)) {
      score += 4;
      matched.add(tok);
    } else if (symptomTokens.has(tok)) {
      score += 3;
      matched.add(tok);
    } else if (titleTokens.has(tok)) {
      score += 2;
      matched.add(tok);
    } else if (bodyTokens.has(tok)) {
      score += 1;
      matched.add(tok);
    }
  }

  // Whole-phrase boost when a curated keyword/symptom appears verbatim.
  for (const phrase of [...rb.keywords, ...rb.symptoms]) {
    if (phrase.length > 3 && q.includes(phrase.toLowerCase())) {
      score += 5;
      matched.add(phrase);
    }
  }

  return { score, matched: [...matched] };
}

export function searchRunbooks(query: string, limit = 5): SearchHit[] {
  const tokens = [...new Set(tokenize(query))];
  const hits: SearchHit[] = [];
  for (const rb of RUNBOOKS) {
    const { score, matched } = scoreRunbook(rb, tokens, query);
    if (score > 0) {
      hits.push({
        id: rb.id,
        title: rb.title,
        severity: rb.severity,
        score,
        matched_terms: matched,
        summary: rb.summary,
      });
    }
  }
  // Deterministic ordering: score desc, then id asc as tiebreak.
  hits.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  return hits.slice(0, Math.max(1, Math.min(limit, 20)));
}

export interface DiagnoseResult {
  symptom: string;
  matches: Array<{
    runbook_id: string;
    title: string;
    severity: Runbook["severity"];
    score: number;
    first_steps: string[];
    cautions: string[];
    evidence_to_collect: string[];
  }>;
  note: string;
}

/**
 * Symptom -> ordered troubleshooting steps.
 * Returns the top matching runbooks with their first steps, rather than one
 * merged answer: at 3am the engineer needs to know WHICH runbook a step
 * came from. No match is a policy outcome, not an error — the parent repo's
 * rule for unknown XIDs is "never guess, route to a human with evidence".
 */
export function diagnoseHint(symptom: string): DiagnoseResult {
  const hits = searchRunbooks(symptom, 3).filter((h) => h.score >= 3);
  const matches = hits.map((h) => {
    const rb = byId.get(h.id)!;
    return {
      runbook_id: rb.id,
      title: rb.title,
      severity: rb.severity,
      score: h.score,
      first_steps: rb.steps.slice(0, 3),
      cautions: rb.cautions,
      evidence_to_collect: rb.evidence_to_collect,
    };
  });
  return {
    symptom,
    matches,
    note:
      matches.length > 0
        ? "Steps are heuristic defaults from the AI-Node-Sentinel runbook set. Validate against your site runbook before acting on production hardware. Recurrence within 24h upgrades the response one level (see runbook 'repeat-and-unknown')."
        : "No runbook matched this symptom. Do not guess: collect the raw dmesg Xid lines, nvidia-smi output, and Redfish health state, then route to human review (runbook 'repeat-and-unknown').",
  };
}
