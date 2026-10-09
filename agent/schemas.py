"""Core data schemas shared by ingestion, triage, and reporting."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TelemetryEvent:
    """One normalized telemetry event from a GPU node.

    In production this is parsed from dmesg / DCGM exporter / NVML output.
    The bundled simulator emits synthetic events with the same shape.
    """
    node_id: str
    gpu_index: int
    timestamp: str          # ISO-8601
    source: str            # "dmesg" | "dcgm" | "nvml" | "simulator"
    kind: str              # "xid" | "thermal" | "ecc" | "power"
    payload: dict = field(default_factory=dict)

    @classmethod
    def xid(cls, node_id: str, gpu_index: int, xid_code: int,
            timestamp: str, source: str = "dmesg") -> "TelemetryEvent":
        return cls(node_id=node_id, gpu_index=gpu_index, timestamp=timestamp,
                   source=source, kind="xid", payload={"xid": xid_code})


@dataclass
class XidFinding:
    """An XID event enriched with lookup metadata."""
    node_id: str
    gpu_index: int
    xid_code: int
    timestamp: str
    name: str | None
    category: str
    severity: str          # "critical" | "high" | "medium" | "unknown"
    known: bool            # False when the code is absent from the lookup table


@dataclass
class TriageVerdict:
    """The triage outcome for a single XID finding."""
    finding: XidFinding
    action: str            # e.g. DRAIN_NODE, RESET_GPU, NEEDS_HUMAN_REVIEW
    confidence: float      # 0.0 - 1.0, always paired with a rationale
    rationale: str
    # RAG evidence: [(chunk_id, chunk_text)] grounding this verdict.
    evidence: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class TriageReport:
    """Full pipeline output for one triage run."""
    generated_at: str
    node_count: int
    event_count: int
    verdicts: list[TriageVerdict]
    simulated: bool = True  # True unless built from real hardware telemetry

    def counts_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for v in self.verdicts:
            counts[v.finding.severity] = counts.get(v.finding.severity, 0) + 1
        return counts
