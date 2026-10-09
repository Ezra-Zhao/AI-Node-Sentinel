"""XID error-code lookup table.

Seeded ONLY from public documentation. Authoritative source:
    https://docs.nvidia.com/deploy/xid-errors/  (Release 615 catalog)
Cross-checked against Google Cloud's GPU troubleshooting guide
(https://docs.cloud.google.com/compute/docs/troubleshooting/troubleshooting-gpus).

All descriptions below are clean-room summaries of the public catalog's
mnemonics and resolution buckets (facts, not prose) — severity labels and
action hints are this project's heuristic interpretation, NOT vendor
runbook text.

TODO(Ezra): extend this table with codes you see in the field and, more
importantly, replace the generic action hints with YOUR validated runbook
(drain vs reset vs reboot vs RMA thresholds). The lookup gives *meaning*;
the remediation policy in tools/triage_rules.py gives *decisions*.
"""

# xid_code -> metadata. Keep entries factual and sourced; do not invent
# remediation steps here. Severity is this project's triage label:
#   critical  -> page the on-call, hardware may be untrustworthy
#   high      -> act today, hardware likely OK
#   medium    -> watch closely, early-warning signal
#   low       -> benign/expected event, log only
#   info      -> informational, no response needed
XID_INFO: dict[int, dict[str, str]] = {
    13: {
        "name": "Graphics Engine Exception",
        "category": "illegal_memory_access",
        "severity": "high",
        "notes": "Often application-level; NVIDIA classifies as non-fatal in the "
                 "k8s DRA GPU health check defaults.",
    },
    31: {
        "name": "GPU memory page fault",
        "category": "illegal_memory_access",
        "severity": "high",
        "notes": "Memory page fault; can indicate app bug or HW issue.",
    },
    45: {
        "name": "Preemptive removal (application abort)",
        "category": "app_lifecycle",
        "severity": "low",
        "notes": "Logged when the app aborts and the driver tears down the GPU "
                 "context (Ctrl-C, GPU reset, sigkill). Usually NOT a bug — a "
                 "user or system action. Ignore unless chained to other XIDs.",
    },
    48: {
        "name": "Double-bit ECC error (uncorrectable)",
        "category": "memory_ecc",
        "severity": "critical",
        "notes": "Uncorrectable DRAM error; row-remap / service path per site policy.",
    },
    62: {
        "name": "PMU halt error",
        "category": "firmware_pmu",
        "severity": "critical",
        "notes": "Internal power-management microcontroller halted; catalog "
                 "immediate action is GPU reset.",
    },
    63: {
        "name": "DRAM retirement (row remapping) event",
        "category": "memory_ecc",
        "severity": "info",
        "notes": "Informational: the GPU is handling ECC errors via row/page "
                 "remapping. No response needed on its own.",
    },
    64: {
        "name": "DRAM retirement failure",
        "category": "memory_ecc",
        "severity": "high",
        "notes": "Row/page remapping failed — the GPU could not contain an ECC "
                 "error. Catalog immediate action is GPU reset.",
    },
    74: {
        "name": "NVLink error",
        "category": "nvlink",
        "severity": "critical",
        "notes": "NVLink fabric error; check bridges / switch per platform docs.",
    },
    79: {
        "name": "GPU has fallen off the bus",
        "category": "pcie_connectivity",
        "severity": "critical",
        "notes": "GPU lost PCIe connectivity; commonly power/thermal/seating/HW.",
    },
    92: {
        "name": "Excessive single-bit ECC interrupts",
        "category": "memory_ecc",
        "severity": "medium",
        "notes": "High single-bit ECC error rate. Often a precursor to "
                 "uncorrectable (XID 48) errors — watch this GPU closely.",
    },
    119: {
        "name": "GSP RPC timeout",
        "category": "gsp_firmware",
        "severity": "critical",
        "notes": "GPU System Processor error; typically needs GPU reset per docs.",
    },
    120: {
        "name": "GSP error",
        "category": "gsp_firmware",
        "severity": "critical",
        "notes": "GPU System Processor error; typically needs GPU reset per docs.",
    },
}


def lookup_xid(xid_code: int) -> dict[str, str] | None:
    """Return metadata for a known XID code, else None.

    Unknown codes are NOT guessed at — the pipeline marks them
    severity=unknown and routes to human review.
    """
    return XID_INFO.get(int(xid_code))
