"""dmesg log parser.

Parses kernel-log lines in the format the NVIDIA driver uses for Xid
events, e.g.::

    [12345.678901] NVRM: Xid (PCI:0000:41:00): 79, pid='<unknown>', name=<unknown>, GPU has fallen off the bus

Design intent (interview talking point): in production the agent tails
`dmesg -T` / journald on each node; this parser is the *ingestion edge*
that turns unstructured kernel text into normalized TelemetryEvent
objects the rest of the pipeline can reason about. A regex keeps it
dependency-free and fast enough to run on every node.

Only Xid lines become ``kind="xid"`` events; everything else is skipped
(the agent is a triage tool, not a general log indexer).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from agent.schemas import TelemetryEvent

# Matches: [timestamp] NVRM: Xid (PCI:0000:41:00): 79, <rest>
# The PCI domain/bus/device/function segment is optional — some kernels
# log "Xid (PCI:0000:86:00.0)" while others omit it.
_XID_RE = re.compile(
    r"^\[\s*(?P<ts>[0-9]+\.[0-9]+)\]\s+NVRM:\s+Xid\s+"
    r"(?:\(PCI:(?P<pci>[0-9a-fA-F:.]+)\)\s*:\s*)?"
    r"(?P<xid>[0-9]+)\s*,"
)

# Optional GPU index hint, e.g. "Xid (PCI:0000:41:00): 79, ... GPU 3 ..."
_GPU_RE = re.compile(r"\bGPU\s*(?P<gpu>\d+)\b", re.IGNORECASE)


def parse_line(line: str, node_id: str,
               boot_time: datetime | None = None) -> TelemetryEvent | None:
    """Parse one dmesg line; return a TelemetryEvent or None if not an Xid line.

    ``boot_time`` anchors the monotonic ``[12345.67]`` timestamp to wall
    clock. When unknown (offline log analysis), we fall back to "now",
    which is fine for triage ordering within a single batch.
    """
    m = _XID_RE.match(line.strip())
    if not m:
        return None
    xid_code = int(m.group("xid"))
    uptime_s = float(m.group("ts"))
    if boot_time is None:
        ts = datetime.now(timezone.utc)
    else:
        ts = boot_time + timedelta(seconds=uptime_s)
    gpu_m = _GPU_RE.search(line)
    gpu_index = int(gpu_m.group("gpu")) if gpu_m else -1  # -1 = not identified
    pci = m.group("pci") or "unknown"
    return TelemetryEvent(
        node_id=node_id,
        gpu_index=gpu_index,
        timestamp=ts.isoformat(),
        source="dmesg",
        kind="xid",
        payload={"xid": xid_code, "pci": pci, "raw": line.strip()[:300]},
    )


def parse_text(text: str, node_id: str,
               boot_time: datetime | None = None) -> list[TelemetryEvent]:
    """Parse a whole dmesg capture into Xid events (chronological)."""
    events = []
    for line in text.splitlines():
        ev = parse_line(line, node_id, boot_time)
        if ev is not None:
            events.append(ev)
    return events
