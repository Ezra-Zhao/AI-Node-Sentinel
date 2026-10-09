# Validation & Triage Report

- **Generated:** 2026-10-09T20:19:49.108383+00:00
- **Data:** SIMULATED (synthetic telemetry — demo mode)
- **Nodes scanned:** 1  |  **Events:** 26  |  **XID findings:** 10

## Recommended actions (summary)

- 🟥 **DRAIN_NODE** × 4
- 🟧 **RESET_GPU** × 3
- 🟨 **CHECK_APPLICATION** × 1
- 🟩 **MONITOR** × 1
- ⬜ **IGNORE_EVENT** × 1

## Findings

### 1. 🟥 GPU has fallen off the bus (XID 79)

- **Severity:** critical  |  **Node:** `node-01`  |  **GPU:** -1  |  **Time:** 2026-10-09T20:19:49.072240+00:00
- **Recommended action:** `DRAIN_NODE` (confidence 0.80)
- **Rationale:** XID 79: driver lost the GPU on PCIe; Redfish thermal alert — likely a thermal trip, not a dead GPU.
- **Runbook evidence:**
  - `xid-79-bus` — XID 79 — GPU has fallen off the bus, severity CRITICAL.
  - `redfish-thermal` — Redfish thermal interpretation: compare GPU hotspot against

### 2. 🟥 GPU has fallen off the bus (XID 79)

- **Severity:** critical  |  **Node:** `node-01`  |  **GPU:** -1  |  **Time:** 2026-10-09T20:19:49.072309+00:00
- **Recommended action:** `DRAIN_NODE` (confidence 0.80)
- **Rationale:** XID 79: driver lost the GPU on PCIe; Redfish thermal alert — likely a thermal trip, not a dead GPU.
- **Runbook evidence:**
  - `xid-79-bus` — XID 79 — GPU has fallen off the bus, severity CRITICAL.
  - `redfish-thermal` — Redfish thermal interpretation: compare GPU hotspot against

### 3. 🟥 Double-bit ECC error (uncorrectable) (XID 48)

- **Severity:** critical  |  **Node:** `node-01`  |  **GPU:** -1  |  **Time:** 2026-10-09T20:19:49.072328+00:00
- **Recommended action:** `DRAIN_NODE` (confidence 0.85)
- **Rationale:** XID 48: uncorrectable DRAM error. Drain the node so no new work lands on it; watch for recurrence before RMA.
- **Runbook evidence:**
  - `xid-48-dbe` — XID 48 — Double-bit ECC error (uncorrectable), severity CRITICAL.
  - `xid-92-sbe` — XID 92 — Excessive single-bit ECC interrupts, severity

### 4. 🟨 Graphics Engine Exception (XID 13)

- **Severity:** high  |  **Node:** `node-01`  |  **GPU:** -1  |  **Time:** 2026-10-09T20:19:49.072351+00:00
- **Recommended action:** `CHECK_APPLICATION` (confidence 0.70)
- **Rationale:** XID 13: usually application-level (bad memory access by the workload). Check the app/deploy first; do NOT drain the node on a single occurrence.
- **Runbook evidence:**
  - `xid-13-31-app` — XID 13 / 31 — Graphics Engine Exception / GPU memory page fault,
  - `xid-92-sbe` — XID 92 — Excessive single-bit ECC interrupts, severity

### 5. 🟧 GSP RPC timeout (XID 119)

- **Severity:** critical  |  **Node:** `node-01`  |  **GPU:** -1  |  **Time:** 2026-10-09T20:19:49.072362+00:00
- **Recommended action:** `RESET_GPU` (confidence 0.75)
- **Rationale:** XID 119: GSP firmware error. Try GPU reset first; drain + escalate if it recurs.
- **Runbook evidence:**
  - `xid-119-120-gsp` — XID 119/120 — GSP (GPU System Processor) RPC timeout / error,
  - `unknown-xid` — Unknown XID codes (not in the lookup table): never guess. Mark

### 6. 🟧 GSP error (XID 120)

- **Severity:** critical  |  **Node:** `node-01`  |  **GPU:** -1  |  **Time:** 2026-10-09T20:19:49.072372+00:00
- **Recommended action:** `RESET_GPU` (confidence 0.75)
- **Rationale:** XID 120: GSP firmware error. Try GPU reset first; drain + escalate if it recurs.
- **Runbook evidence:**
  - `xid-119-120-gsp` — XID 119/120 — GSP (GPU System Processor) RPC timeout / error,
  - `unknown-xid` — Unknown XID codes (not in the lookup table): never guess. Mark

### 7. ⬜ Preemptive removal (application abort) (XID 45)

- **Severity:** low  |  **Node:** `node-01`  |  **GPU:** 2  |  **Time:** 2026-10-09T20:19:49.072379+00:00
- **Recommended action:** `IGNORE_EVENT` (confidence 0.80)
- **Rationale:** XID 45: application abort tore down the GPU context (Ctrl-C / reset / sigkill). Not a hardware signal — log only.
- **Runbook evidence:**
  - `xid-45-abort` — XID 45 — Preemptive removal after application abort,
  - `xid-45-63-benign` — XID 45 (preemptive removal on app abort) is benign by

### 8. 🟩 Excessive single-bit ECC interrupts (XID 92)

- **Severity:** medium  |  **Node:** `node-01`  |  **GPU:** -1  |  **Time:** 2026-10-09T20:19:49.072389+00:00
- **Recommended action:** `MONITOR` (confidence 0.60)
- **Rationale:** XID 92: elevated single-bit ECC rate. Watch closely — this is the early-warning signal for XID 48.
- **Runbook evidence:**
  - `xid-92-sbe` — XID 92 — Excessive single-bit ECC interrupts, severity
  - `xid-48-dbe` — XID 48 — Double-bit ECC error (uncorrectable), severity CRITICAL.

### 9. 🟧 PMU halt error (XID 62)

- **Severity:** critical  |  **Node:** `node-01`  |  **GPU:** 5  |  **Time:** 2026-10-09T20:19:49.072396+00:00
- **Recommended action:** `RESET_GPU` (confidence 0.78)
- **Rationale:** XID 62: PMU (power-management microcontroller) halted. GPU reset is the catalog immediate action.
- **Runbook evidence:**
  - `xid-62-pmu` — XID 62 — PMU halt error, severity CRITICAL. The GPU's
  - `unknown-xid` — Unknown XID codes (not in the lookup table): never guess. Mark

### 10. 🟥 Double-bit ECC error (uncorrectable) (XID 48)

- **Severity:** critical  |  **Node:** `node-01`  |  **GPU:** 3  |  **Time:** 2026-10-09T20:19:49.072653+00:00
- **Recommended action:** `DRAIN_NODE` (confidence 0.85)
- **Rationale:** XID 48: uncorrectable DRAM error. Drain the node so no new work lands on it; watch for recurrence before RMA.
- **Runbook evidence:**
  - `xid-48-dbe` — XID 48 — Double-bit ECC error (uncorrectable), severity CRITICAL.
  - `xid-92-sbe` — XID 92 — Excessive single-bit ECC interrupts, severity

## Severity breakdown

critical: 7, high: 1, low: 1, medium: 1

---
_Generated by AI-Node-Sentinel (demo mode: all telemetry synthetic). Triage rules are heuristic defaults — validate against your site runbook before operational use._