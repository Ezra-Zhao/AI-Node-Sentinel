"""Triage agent orchestration.

Pipeline: ingest -> extract XID events -> lookup metadata ->
apply triage rules -> render report.

Scaffold v0.1 is deterministic: the LLM reasoning step is defined but not
wired (see agent/llm.py). Every verdict produced before the decision tree
is encoded carries action=NEEDS_HUMAN_REVIEW and confidence=0.0 — by design,
never a fabricated diagnosis.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Iterable, Optional

from agent.llm import LLMProvider
from agent.schemas import TelemetryEvent, TriageReport, TriageVerdict, XidFinding
from tools.triage_rules import triage_decision
from tools.xid_lookup import lookup_xid


class TriageAgent:
    def __init__(self, llm: Optional[LLMProvider] = None) -> None:
        # None -> deterministic scaffold mode (no LLM calls).
        self.llm = llm

    # ---- pipeline stages -------------------------------------------------

    def ingest(self, events: Iterable[TelemetryEvent]) -> list[TelemetryEvent]:
        """Normalize raw events. Currently a pass-through; real parsers land here."""
        return list(events)

    def extract_xid_events(self, events: list[TelemetryEvent]) -> list[TelemetryEvent]:
        return [e for e in events if e.kind == "xid"]

    def triage_event(self, event: TelemetryEvent) -> TriageVerdict:
        code = int(event.payload["xid"])
        info = lookup_xid(code)
        finding = XidFinding(
            node_id=event.node_id,
            gpu_index=event.gpu_index,
            xid_code=code,
            timestamp=event.timestamp,
            name=info["name"] if info else None,
            category=info["category"] if info else "unknown",
            severity=info["severity"] if info else "unknown",
            known=info is not None,
        )
        # TODO(Ezra): decision tree stub — see tools/triage_rules.py.
        decision = triage_decision(code, context={"known": finding.known})

        rationale = decision.rationale
        if self.llm is not None:  # pragma: no cover - needs real LLM wiring
            evidence = (
                f"node={finding.node_id} gpu={finding.gpu_index} "
                f"xid={finding.xid_code} name={finding.name} "
                f"severity={finding.severity} ts={finding.timestamp}"
            )
            rationale += "\n[LLM] " + self.llm.reason(
                system_prompt=open("prompts/triage_system.md").read(),
                evidence=evidence,
            )
        return TriageVerdict(
            finding=finding,
            action=decision.action,
            confidence=decision.confidence,
            rationale=rationale,
        )

    def run(self, events: Iterable[TelemetryEvent],
            node_count: int = 0, simulated: bool = True) -> TriageReport:
        ingested = self.ingest(events)
        xid_events = self.extract_xid_events(ingested)
        verdicts = [self.triage_event(e) for e in xid_events]
        return TriageReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            node_count=node_count,
            event_count=len(ingested),
            verdicts=verdicts,
            simulated=simulated,
        )

    # ---- rendering ---------------------------------------------------------

    def render(self, report: TriageReport) -> str:
        lines = [
            "=" * 68,
            "AI-NODE-SENTINEL  TRIAGE REPORT",
            f"generated : {report.generated_at}",
            f"data      : {'SIMULATED (synthetic telemetry)' if report.simulated else 'REAL hardware telemetry'}",
            f"nodes     : {report.node_count}   events scanned: {report.event_count}",
            f"xid events: {len(report.verdicts)}",
            "=" * 68,
        ]
        if not report.verdicts:
            lines.append("No XID events found. Fleet looks healthy (in this sample).")
        for v in report.verdicts:
            f = v.finding
            label = f.name or f"UNKNOWN XID {f.xid_code}"
            lines += [
                "",
                f"[{f.severity.upper():8s}] {label}  (XID {f.xid_code})",
                f"  node={f.node_id}  gpu={f.gpu_index}  ts={f.timestamp}",
                f"  action={v.action}  confidence={v.confidence:.2f}",
                f"  rationale: {v.rationale}",
            ]
        counts = report.counts_by_severity()
        lines += ["", f"severity breakdown: {counts or 'n/a'}", "=" * 68]
        return "\n".join(lines)

    def report_dict(self, report: TriageReport) -> dict:
        return asdict(report)
