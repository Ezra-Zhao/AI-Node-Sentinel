"""Triage knowledge base.

Each chunk is clean-room text written for this project from public
documentation (NVIDIA Xid error catalog, Google Cloud GPU troubleshooting
guide). They are HEURISTIC DEFAULTS for demo/portfolio purposes — a
starting runbook, not a site-validated SOP. Validate thresholds and
actions against your own fleet's runbook before operational use.
"""
from __future__ import annotations

# chunk_id -> text
KNOWLEDGE_BASE: dict[str, str] = {
    "xid-48-dbe": """XID 48 — Double-bit ECC error (uncorrectable), severity CRITICAL.
Meaning: the GPU's DRAM reported an error that ECC could not correct; the
affected memory region is unreliable. First occurrence: drain the node so no
new work lands on it, keep the GPU idle, and record the event with GPU
serial/location. If the same GPU reports XID 48 again within 24h, treat the
card as degraded: open an RMA/service ticket per site policy. Do NOT simply
reboot and return the node to the pool — uncorrectable errors tend to recur.""",

    "xid-79-bus": """XID 79 — GPU has fallen off the bus, severity CRITICAL.
Meaning: the driver lost PCIe communication with the GPU. Common causes, in
rough likelihood order: power delivery problem (PSU redundancy lost, rail
droop under load), thermal trip, card seating / riser issue, or a genuinely
failed GPU. Triage order: (1) check out-of-band telemetry — inlet temp and
PSU redundancy via Redfish; (2) if power/thermal look normal, reseat or move
the card; (3) persistent after reseat => RMA. Note: in-band tools (nvidia-smi)
cannot see the card in this state, so Redfish is the primary evidence.""",

    "xid-74-nvlink": """XID 74 — NVLink error, severity CRITICAL.
Meaning: an error on the NVLink fabric between GPUs. Check the NVLink
bridges/switch for the platform, then look for correlated XID 74 events on
neighbor GPUs — a cluster of them points at the fabric/switch rather than a
single card. Drain affected nodes; do not return them until the link trains
cleanly again.""",

    "xid-119-120-gsp": """XID 119/120 — GSP (GPU System Processor) RPC timeout / error,
severity CRITICAL. Meaning: the GPU's embedded microcontroller stopped
responding to the driver. First response: GPU reset (nvidia-smi --gpu-reset
where supported). If GSP errors repeat on the same GPU after reset, drain the
node and escalate — recurring GSP faults usually end in a service ticket.""",

    "xid-13-31-app": """XID 13 / 31 — Graphics Engine Exception / GPU memory page fault,
severity HIGH. Meaning: often application-level (illegal memory access by the
CUDA workload) rather than broken hardware. Do NOT drain the node on a single
occurrence: check the application first (recent code/deploy change, bad input
batch, OOM-adjacent access patterns). Escalate to hardware triage only if the
same GPU throws them across unrelated workloads.""",

    "xid-45-abort": """XID 45 — Preemptive removal after application abort,
severity LOW. Meaning: the user application was aborted (Ctrl-C, GPU reset,
sigkill) and the driver tore down the GPU context. This is cleanup, not a
fault — the benign XID. Log it and move on. Investigate only when XID 45
appears chained with real error XIDs (e.g. 48/79) in the same window.""",

    "xid-62-pmu": """XID 62 — PMU halt error, severity CRITICAL.
Meaning: the GPU's internal power-management microcontroller halted.
First response: GPU reset. A PMU that keeps halting after reset is a
firmware/hardware problem — drain the node and escalate, do not keep
resetting it in a loop.""",

    "xid-63-64-remap": """XID 63 / 64 — DRAM row retirement events.
XID 63 is informational: the GPU is containing ECC errors through row/page
remapping as designed — no response needed, just note the SBE trend.
XID 64 is the failure case: remapping failed and the error could not be
contained. Treat like a hardware memory problem: reset the GPU first,
drain and escalate if it recurs.""",

    "xid-92-sbe": """XID 92 — Excessive single-bit ECC interrupts, severity MEDIUM.
Meaning: the single-bit ECC error rate is abnormally high. SBEs are
correctable, so nothing is broken yet — but a rising SBE rate is the
classic precursor to uncorrectable double-bit errors (XID 48). Action:
monitor this GPU's ECC counters (nvidia-smi -q) on a short cadence; if
XID 92 keeps firing or XID 48 appears, drain and escalate.""",

    "repeat-escalation": """Repeat-event rule (heuristic default): the same XID code on
the same GPU twice within 24 hours upgrades the response one level —
CHECK becomes DRAIN, DRAIN becomes DRAIN+ESCALATE. Single isolated events,
especially XID 13/31, are usually noise; recurrence is the signal that
separates a flaky card from a bad run.""",

    "redfish-thermal": """Redfish thermal interpretation: compare GPU hotspot against
chassis inlet. Hotspot above ~85C with a normal inlet (~23-27C) points at the
card's cooling (heatsink mount, fan zone, TIM) rather than the room. Hotspot
high AND inlet high points at facility cooling. Correlate thermal alerts with
XID 79 before concluding the GPU is dead — many 'fallen off the bus' events
are thermal trips in disguise.""",

    "redfish-power": """Redfish power interpretation: PSU redundancy lost
(psu_redundancy_ok=false) plus XID 79 is the classic signature of a power
delivery problem, not a dead GPU. Check input power draw vs. provisioned
capacity before touching the card. PCIe uncorrectable error counters > 0 in
Redfish alongside XID 79/74 strengthen the case for a bus/fabric problem.""",

    "report-audience": """Triage report audience: the on-call engineer at 3am. Every
verdict must answer three questions in order: WHAT broke (finding + severity),
HOW BAD (blast radius: one GPU vs node vs fabric), WHAT FIRST (the single
recommended action). Confidence is a number with a reason, never a bare
number — low confidence must say what evidence is missing.""",

    "unknown-xid": """Unknown XID codes (not in the lookup table): never guess. Mark
severity unknown, route to human review, and record the raw dmesg line so the
code can be researched against vendor documentation. An unknown code with a
healthy Redfish profile is usually a new firmware event, not an emergency.""",
}
