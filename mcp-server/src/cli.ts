#!/usr/bin/env node
/**
 * CLI entry point: the same runbook retrieval the MCP server exposes,
 * callable from a shell. One retrieval core, two delivery surfaces —
 * MCP for agents, CLI for humans and scripts.
 *
 * Usage:
 *   node dist/cli.js search "xid 79" [--limit 3]
 *   node dist/cli.js get xid-79-bus
 *   node dist/cli.js diagnose "gpu disappeared from nvidia-smi"
 *   node dist/cli.js list
 *
 * Output is JSON on stdout (machine-readable by default; pipe to jq).
 * Exit codes: 0 ok, 1 usage error, 2 runbook id not found.
 */
import {
  diagnoseHint,
  getRunbook,
  listRunbookIds,
  RUNBOOKS,
  searchRunbooks,
} from "./runbooks.js";

function usage(): never {
  console.error(
    [
      "Usage:",
      '  sentinel-context search "<query>" [--limit N]',
      "  sentinel-context get <runbook-id>",
      '  sentinel-context diagnose "<symptom>"',
      "  sentinel-context list",
    ].join("\n"),
  );
  process.exit(1);
}

function printJson(value: unknown): void {
  console.log(JSON.stringify(value, null, 2));
}

function main(argv: string[]): void {
  const [command, ...rest] = argv;

  switch (command) {
    case "search": {
      const limitFlag = rest.indexOf("--limit");
      let limit = 5;
      if (limitFlag >= 0) {
        limit = Number(rest[limitFlag + 1]);
        if (!Number.isInteger(limit) || limit < 1) usage();
        rest.splice(limitFlag, 2);
      }
      const query = rest.join(" ").trim();
      if (!query) usage();
      const results = searchRunbooks(query, limit);
      printJson({ query, count: results.length, results });
      return;
    }
    case "get": {
      const id = rest[0];
      if (!id) usage();
      const rb = getRunbook(id);
      if (!rb) {
        printJson({ error: `Unknown runbook id: ${id}`, known_ids: listRunbookIds() });
        process.exit(2);
      }
      printJson(rb);
      return;
    }
    case "diagnose": {
      const symptom = rest.join(" ").trim();
      if (!symptom) usage();
      printJson(diagnoseHint(symptom));
      return;
    }
    case "list": {
      printJson(
        RUNBOOKS.map((r) => ({ id: r.id, title: r.title, severity: r.severity })),
      );
      return;
    }
    default:
      usage();
  }
}

main(process.argv.slice(2));
