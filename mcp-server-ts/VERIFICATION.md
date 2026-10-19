# Verification record

All commands below were actually run on 2026-10-19 (America/Los_Angeles)
in this directory, on Node v24.20.0 / npm 10.9.4 / Python 3.12.3.
Outputs are quoted verbatim (trimmed only for npm funding boilerplate).

## 1. Data export + cross-check against the Python sources

```bash
python3 scripts/export_data.py
```

```
xid_info.json: 12 codes -> [13, 31, 45, 48, 62, 63, 64, 74, 79, 92, 119, 120]
knowledge_base.json: 15 chunks -> ['xid-48-dbe', 'xid-79-bus', 'xid-74-nvlink',
  'xid-119-120-gsp', 'xid-13-31-app', 'xid-45-abort', 'xid-62-pmu',
  'xid-63-64-remap', 'xid-92-sbe', 'repeat-escalation', 'redfish-thermal',
  'redfish-power', 'report-audience', 'unknown-xid', 'xid-45-63-benign']
```

Then the exported JSON was asserted **identical** to the live Python
runtime dicts (`tools.xid_lookup.XID_INFO`, `rag.knowledge_base.KNOWLEDGE_BASE`):

```
CROSS-CHECK OK: exported JSON is identical to the Python runtime data
sample XID 48: {'name': 'Double-bit ECC error (uncorrectable)',
  'category': 'memory_ecc', 'severity': 'critical',
  'notes': 'Uncorrectable DRAM error; row-remap / service path per site policy.'}
```

## 2. Install & build

```bash
npm install        # resolves @modelcontextprotocol/sdk ^1.32.1, zod, typescript
npm run build      # tsc -> dist/{index,data,retriever}.js, no errors
npm start          # prints "ai-node-sentinel MCP server running on stdio" (stderr)
```

## 3. Smoke test — raw JSON-RPC over stdio (`npm run smoke`)

`test/smoke.mjs` spawns `dist/index.js` and sends `initialize`,
`notifications/initialized`, `tools/list`, and `tools/call` requests
(including three invalid-input cases). Final run:

```
PASS  initialize — serverInfo={"name":"ai-node-sentinel","version":"0.1.0"} protocol=2024-11-05
PASS  tools/list — tools=list_xids,lookup_xid,search_runbook
PASS  tools/list lookup_xid has full input schema — {"type":"object","properties":{"xid_code":{"type":"integer","exclusiveMinimum":0,"description":"..."}},"required":["xid_code"],...}
PASS  tools/call lookup_xid 48 — name="Double-bit ECC error (uncorrectable)" severity=critical
PASS  tools/call lookup_xid 999 (unknown, never guessed) — known=false severity=unknown
PASS  tools/call list_xids — count=12
PASS  tools/call search_runbook (TF-IDF top-1 for XID 79 query) — top=xid-79-bus score=0.3494
PASS  tools/call lookup_xid with string arg errors — isError=true
PASS  tools/call lookup_xid with missing arg errors — isError=true
PASS  tools/call search_runbook with empty query errors — isError=true

SMOKE: ALL CHECKS PASSED
```

## 4. TF-IDF parity with the Python retriever

The same 5 queries were run through Python `rag/retriever.py` and the
TypeScript port. Rankings **and** scores (4 decimal places) are identical:

| Query | Python top-2 | TypeScript top-2 |
|---|---|---|
| `XID 79 GPU fallen off the bus power thermal` | xid-79-bus 0.3494, redfish-thermal 0.3340 | xid-79-bus 0.3494, redfish-thermal 0.3340 |
| `XID 48 double-bit ECC error drain` | xid-92-sbe 0.3578, xid-48-dbe 0.2901 | xid-92-sbe 0.3578, xid-48-dbe 0.2901 |
| `nvlink fabric error neighbors` | xid-74-nvlink 0.4907, redfish-power 0.1023 | xid-74-nvlink 0.4907, redfish-power 0.1023 |
| `single-bit ECC precursor monitor` | xid-92-sbe 0.4222, xid-45-63-benign 0.1350 | xid-92-sbe 0.4222, xid-45-63-benign 0.1350 |
| `unknown xid human review` | unknown-xid 0.4705, xid-92-sbe 0.0428 | unknown-xid 0.4705, xid-92-sbe 0.0428 |
