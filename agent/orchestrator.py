"""Triage agent orchestration.

Pipeline (the "Silicon Triage Agent" loop):
    ingest -> extract XID events -> lookup metadata ->
    RAG retrieve runbook evidence -> apply decision tree ->
    render report (console + markdown + JSON).

Deterministic by default (no LLM calls). Pass llm=<provider> to add a
LangChain reasoning step on top of the rule-based verdicts.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from agent.llm import LLMProvider
from agent.report_md import render_markdown
from agent.schemas import TelemetryEvent, TriageReport, TriageVerdict, XidFinding
from rag.knowledge_base import KNOWLEDGE_BASE
from rag.retriever import TfidfRetriever
from tools.triage_rules import triage_decision
from tools.xid_lookup import lookup_xid

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "triage_system.md"


class TriageAgent:
    def __init__(self, llm: Optional[LLMProvider] = None) -> None:
        # None -> deterministic mode (no LLM calls). The retriever is
        # stdlib-only, so RAG evidence works in every mode.
        self.llm = llm
        self.retriever = TfidfRetriever(KNOWLEDGE_BASE)

    # ---- pipeline stages -------------------------------------------------

    def ingest(self, events: Iterable[TelemetryEvent]) -> list[TelemetryEvent]:
        """Normalize raw events. Parsers (dmesg/nvidia-smi/redfish) land here."""
        return list(events)

    def extract_xid_events(self, events: list[TelemetryEvent]) -> list[TelemetryEvent]:
        return [e for e in events if e.kind == "xid"]

    def _repeat_counts(self, events: list[TelemetryEvent]) -> Counter:
        """Count (node, gpu, xid) occurrences — recurrence is the escalation signal."""
        return Counter((e.node_id, e.gpu_index, int(e.payload["xid"]))
                       for e in events)

    def _rag_query(self, finding: XidFinding) -> str:
        # Lexical query: XID code + name + severity hit the right runbook chunks.
        return (f"XID {finding.xid_code} {finding.name or ''} "
                f"{finding.category} {finding.severity}")

    def triage_event(self, event: TelemetryEvent, context: dict) -> TriageVerdict:
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
        # RAG: ground the verdict in our runbook before deciding.
        evidence = [(cid, KNOWLEDGE_BASE[cid])
                    for cid, _ in self.retriever.retrieve(self._rag_query(finding))]

        decision = triage_decision(code, {**context, "known": finding.known})

        rationale = decision.rationale
        if self.llm is not None:
            evidence_text = (
                f"node={finding.node_id} gpu={finding.gpu_index} "
                f"xid={finding.xid_code} name={finding.name} "
                f"severity={finding.severity} ts={finding.timestamp}\n"
                f"runbook: {' | '.join(t[:200] for _, t in evidence)}"
            )
            system = _PROMPT_PATH.read_text() if _PROMPT_PATH.exists() else ""
            rationale += "\n[LLM] " + self.llm.reason(
                system_prompt=system, evidence=evidence_text)

        return TriageVerdict(
            finding=finding,
            action=decision.action,
            confidence=decision.confidence,
            rationale=rationale,
            evidence=evidence,
        )

    def run(self, events: Iterable[TelemetryEvent],
            node_count: int = 0, simulated: bool = True,
            node_context: dict[str, dict] | None = None) -> TriageReport:
        """Run the full triage loop.

        node_context: {node_id: {"thermal_alert": bool, "power_degraded": bool}}
        from Redfish/out-of-band telemetry; feeds the decision tree.
        """
        ingested = self.ingest(events)
        xid_events = self.extract_xid_events(ingested)
        repeats = self._repeat_counts(xid_events)
        node_context = node_context or {}
        verdicts = []
        for e in xid_events:
            code = int(e.payload["xid"])
            ctx = {
                "repeat_count": repeats[(e.node_id, e.gpu_index, code)],
                "thermal_alert": node_context.get(e.node_id, {}).get("thermal_alert", False),
                "power_degraded": node_context.get(e.node_id, {}).get("power_degraded", False),
            }
            verdicts.append(self.triage_event(e, ctx))
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
            if v.evidence:
                lines.append("  evidence: " + ", ".join(cid for cid, _ in v.evidence))
        counts = report.counts_by_severity()
        lines += ["", f"severity breakdown: {counts or 'n/a'}", "=" * 68]
        return "\n".join(lines)

    def render_md(self, report: TriageReport) -> str:
        """Ticket-ready markdown report."""
        return render_markdown(report)

    def report_dict(self, report: TriageReport) -> dict:
        return asdict(report)
