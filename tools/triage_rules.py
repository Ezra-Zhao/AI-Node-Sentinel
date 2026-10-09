"""Triage decision tree: XID finding + context -> action + confidence.

HEURISTIC DEFAULTS, not a site-validated runbook. The rules below encode
textbook responses from public vendor documentation (NVIDIA Xid catalog,
Google Cloud GPU troubleshooting). They are deliberately conservative:
when in doubt, the tree says DRAIN (take the node out of scheduling) and
escalates on recurrence, because a wrong "it's fine" costs GPU-hours
while a wrong "drain it" costs one node for an hour.

Before operational use, replace thresholds with YOUR fleet's validated
runbook. The `unknown` fallback (route to human, never guess) stays
forever — that part is not heuristic, it is policy.

Context keys consumed:
    known (bool)          – XID code present in the lookup table
    repeat_count (int)    – same XID on same GPU within the window
    thermal_alert (bool)  – Redfish/chassis thermal alert on the node
    power_degraded (bool) – Redfish PSU redundancy lost / PCIe uncorrectable
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TriageDecision:
    action: str        # DRAIN_NODE | RESET_GPU | CHECK_APPLICATION | ...
    confidence: float  # 0.0 - 1.0, always paired with a rationale
    rationale: str


def triage_decision(xid_code: int, context: dict) -> TriageDecision:
    known = context.get("known", False)
    repeats = int(context.get("repeat_count", 0))
    thermal = bool(context.get("thermal_alert", False))
    power = bool(context.get("power_degraded", False))

    # Policy: never invent meaning for an unknown code.
    if not known:
        return TriageDecision(
            action="NEEDS_HUMAN_REVIEW",
            confidence=0.30,
            rationale=(f"XID {xid_code} is not in the lookup table; no "
                       f"automated action. Record the raw dmesg line and "
                       f"research against vendor docs."),
        )

    # Recurrence upgrades any response one level: isolated events are noise,
    # repeats are signal. Applied per-code below via the `repeats` checks.
    if xid_code == 48:  # Double-bit ECC (uncorrectable) — memory is untrustworthy
        if repeats >= 2:
            return TriageDecision(
                action="DRAIN_NODE_AND_OPEN_RMA", confidence=0.92,
                rationale=(f"XID 48 recurring ({repeats}x) on this GPU: card "
                           f"is degraded, open RMA/service ticket per site policy."))
        return TriageDecision(
            action="DRAIN_NODE", confidence=0.85,
            rationale=("XID 48: uncorrectable DRAM error. Drain the node so no "
                       "new work lands on it; watch for recurrence before RMA."))

    if xid_code == 79:  # GPU fallen off the bus — often power/thermal, not dead HW
        why = "check power delivery and thermals first (Redfish)"
        if power:
            why = ("Redfish shows degraded power (PSU redundancy lost / PCIe "
                   "uncorrectable) — power delivery is the prime suspect")
        elif thermal:
            why = "Redfish thermal alert — likely a thermal trip, not a dead GPU"
        return TriageDecision(
            action="DRAIN_NODE", confidence=0.80,
            rationale=f"XID 79: driver lost the GPU on PCIe; {why}.")

    if xid_code == 74:  # NVLink fabric error
        return TriageDecision(
            action="DRAIN_NODE", confidence=0.80,
            rationale=("XID 74: NVLink fabric error. Drain affected nodes and "
                       "check for correlated XID 74 on neighbors (fabric/switch "
                       "issue) before blaming one card."))

    if xid_code in (119, 120):  # GSP firmware errors
        if repeats >= 2:
            return TriageDecision(
                action="DRAIN_NODE_AND_ESCALATE", confidence=0.85,
                rationale=(f"XID {xid_code} recurring ({repeats}x) after reset: "
                           f"escalate, likely a service ticket."))
        return TriageDecision(
            action="RESET_GPU", confidence=0.75,
            rationale=(f"XID {xid_code}: GSP firmware error. Try GPU reset "
                       f"first; drain + escalate if it recurs."))

    if xid_code == 62:  # PMU halt — catalog immediate action is GPU reset
        if repeats >= 2:
            return TriageDecision(
                action="DRAIN_NODE_AND_ESCALATE", confidence=0.85,
                rationale=(f"XID 62 recurring ({repeats}x): PMU keeps halting "
                           f"after reset — escalate, likely a service ticket."))
        return TriageDecision(
            action="RESET_GPU", confidence=0.78,
            rationale=("XID 62: PMU (power-management microcontroller) halted. "
                       "GPU reset is the catalog immediate action."))

    if xid_code == 64:  # DRAM retirement failure — containment failed
        if repeats >= 2:
            return TriageDecision(
                action="DRAIN_NODE_AND_ESCALATE", confidence=0.85,
                rationale=(f"XID 64 recurring ({repeats}x): row remapping keeps "
                           f"failing — escalate, likely a service ticket."))
        return TriageDecision(
            action="RESET_GPU", confidence=0.80,
            rationale=("XID 64: DRAM row/page remapping FAILED — the GPU could "
                       "not contain an ECC error. Catalog immediate action is "
                       "GPU reset; drain + escalate if it recurs."))

    if xid_code == 92:  # Excessive single-bit ECC — early warning for XID 48
        if repeats >= 3:
            return TriageDecision(
                action="DRAIN_NODE_AND_ESCALATE", confidence=0.80,
                rationale=(f"XID 92 {repeats}x: sustained single-bit ECC storm "
                           f"— precursor pattern for uncorrectable errors. "
                           f"Drain and escalate before it becomes an XID 48."))
        return TriageDecision(
            action="MONITOR", confidence=0.60,
            rationale=("XID 92: elevated single-bit ECC rate. Watch closely — "
                       "this is the early-warning signal for XID 48."))

    if xid_code == 45:  # Preemptive removal on app abort — benign by design
        return TriageDecision(
            action="IGNORE_EVENT", confidence=0.80,
            rationale=("XID 45: application abort tore down the GPU context "
                       "(Ctrl-C / reset / sigkill). Not a hardware signal — "
                       "log only."))

    if xid_code == 63:  # DRAM retirement event — informational
        return TriageDecision(
            action="MONITOR", confidence=0.65,
            rationale=("XID 63: informational row-retirement event — the GPU "
                       "is handling ECC via remapping. Log only; act only if "
                       "chained to other XIDs."))

    if xid_code in (13, 31):  # App-level: do NOT drain on a single occurrence
        if repeats >= 3:
            return TriageDecision(
                action="DRAIN_NODE_AND_ESCALATE", confidence=0.70,
                rationale=(f"XID {xid_code} {repeats}x across this window: "
                           f"persistent across (likely) different workloads — "
                           f"escalate to hardware triage."))
        return TriageDecision(
            action="CHECK_APPLICATION", confidence=0.70,
            rationale=(f"XID {xid_code}: usually application-level (bad memory "
                       f"access by the workload). Check the app/deploy first; "
                       f"do NOT drain the node on a single occurrence."))

    if xid_code == 45:  # App abort teardown — benign by design
        return TriageDecision(
            action="IGNORE_EVENT", confidence=0.65,
            rationale=("XID 45: preemptive removal after an application abort "
                       "(Ctrl-C / GPU reset / sigkill). This is the driver "
                       "cleaning up, not a fault. Log it; investigate only "
                       "if chained to other XIDs."))

    if xid_code == 62:  # PMU halt — firmware microcontroller, reset first
        if repeats >= 2:
            return TriageDecision(
                action="DRAIN_NODE_AND_ESCALATE", confidence=0.85,
                rationale=(f"XID 62 recurring ({repeats}x): PMU keeps halting "
                           f"after reset — drain and escalate, likely a "
                           f"service ticket."))
        return TriageDecision(
            action="RESET_GPU", confidence=0.75,
            rationale=("XID 62: internal PMU (power-management microcontroller) "
                       "halt. Try GPU reset first; drain + escalate if it recurs."))

    if xid_code == 63:  # Row-remap event — informational by design
        return TriageDecision(
            action="MONITOR", confidence=0.60,
            rationale=("XID 63: DRAM row/page retirement event — the GPU is "
                       "handling ECC errors via remapping as designed. No "
                       "response needed; keep an eye on the SBE trend."))

    if xid_code == 64:  # Remap failure — containment failed, reset first
        if repeats >= 2:
            return TriageDecision(
                action="DRAIN_NODE_AND_ESCALATE", confidence=0.85,
                rationale=(f"XID 64 recurring ({repeats}x): DRAM retirement "
                           f"keeps failing — memory subsystem is degraded. "
                           f"Drain and escalate."))
        return TriageDecision(
            action="RESET_GPU", confidence=0.75,
            rationale=("XID 64: DRAM retirement (remap) failed — the GPU could "
                       "not contain an ECC error. Reset the GPU; drain + "
                       "escalate if it recurs."))

    if xid_code == 92:  # High SBE rate — the DBE early-warning signal
        if repeats >= 3:
            return TriageDecision(
                action="DRAIN_NODE_AND_ESCALATE", confidence=0.70,
                rationale=(f"XID 92 {repeats}x across this window: persistently "
                           f"high single-bit ECC rate — this card is trending "
                           f"toward uncorrectable errors (XID 48). Drain and "
                           f"escalate before it degrades."))
        return TriageDecision(
            action="MONITOR", confidence=0.60,
            rationale=("XID 92: excessive single-bit ECC interrupts. Watch "
                       "this GPU closely — a high SBE rate often precedes "
                       "uncorrectable (XID 48) errors."))

    # Known code with no specific rule: watch, don't act.
    return TriageDecision(
        action="MONITOR", confidence=0.50,
        rationale=(f"XID {xid_code} is known but has no specific rule in this "
                   f"runbook version; monitor for recurrence."))
