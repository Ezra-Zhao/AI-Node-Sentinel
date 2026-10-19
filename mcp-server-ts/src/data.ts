/**
 * Data loading for the MCP server.
 *
 * The JSON files under ../data are GENERATED from the Python sources in
 * this repository by scripts/export_data.py — they are not a separate,
 * hand-maintained dataset:
 *   data/xid_info.json       <- tools/xid_lookup.py :: XID_INFO
 *   data/knowledge_base.json <- rag/knowledge_base.py :: KNOWLEDGE_BASE
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export interface XidInfo {
  name: string;
  category: string;
  /** critical | high | medium | low | info — this project's triage label */
  severity: string;
  notes: string;
}

const dataDir = join(dirname(fileURLToPath(import.meta.url)), "..", "data");

function loadJson(file: string): unknown {
  return JSON.parse(readFileSync(join(dataDir, file), "utf-8"));
}

interface XidFile {
  source: string;
  entries: Record<string, XidInfo>;
}

interface KbFile {
  source: string;
  chunks: Record<string, string>;
}

const xidFile = loadJson("xid_info.json") as XidFile;
const kbFile = loadJson("knowledge_base.json") as KbFile;

/** XID code -> metadata, mirroring tools/xid_lookup.py's XID_INFO. */
export const XID_INFO: ReadonlyMap<number, XidInfo> = new Map(
  Object.entries(xidFile.entries).map(([code, meta]) => [Number(code), meta]),
);

export const XID_SOURCE = xidFile.source;

/** chunk_id -> runbook text, mirroring rag/knowledge_base.py's KNOWLEDGE_BASE. */
export const KNOWLEDGE_BASE: Readonly<Record<string, string>> = kbFile.chunks;

export const KB_SOURCE = kbFile.source;

/**
 * Mirror of Python's lookup_xid(): returns the metadata for a known code,
 * or undefined for an unknown one. Unknown codes are never guessed at.
 */
export function lookupXid(xidCode: number): XidInfo | undefined {
  return XID_INFO.get(xidCode);
}
