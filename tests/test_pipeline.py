"""Scaffold tests: determinism, lookup honesty, stub behavior, report shape."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.orchestrator import TriageAgent
from agent.schemas import TelemetryEvent
from telemetry.simulator import simulate_cluster
from tools.triage_rules import triage_decision
from tools.xid_lookup import lookup_xid


def test_simulator_is_deterministic():
    a = simulate_cluster(seed=7)
    b = simulate_cluster(seed=7)
    assert [e.timestamp for e in a] == [e.timestamp for e in b]
    assert len(a) == len(b) > 0


def test_lookup_known_xid():
    info = lookup_xid(79)
    assert info is not None
    assert "bus" in info["name"].lower()
    assert info["severity"] == "critical"


def test_lookup_unknown_xid_returns_none():
    # Unknown codes must NOT be guessed at.
    assert lookup_xid(999) is None
    assert lookup_xid(123456) is None


def test_triage_stub_routes_to_human_review():
    d = triage_decision(79, context={"known": True})
    assert d.action == "NEEDS_HUMAN_REVIEW"
    assert d.confidence == 0.0


def test_pipeline_report_shape():
    events = simulate_cluster(num_nodes=2, gpus_per_node=4, seed=1)
    agent = TriageAgent()
    report = agent.run(events, node_count=2, simulated=True)
    assert report.simulated is True
    assert report.node_count == 2
    assert report.event_count == len(events)
    for v in report.verdicts:
        assert v.finding.node_id.startswith("node-")
        assert v.action == "NEEDS_HUMAN_REVIEW"  # stub until tree is encoded


def test_unknown_xid_marked_unknown_severity():
    e = TelemetryEvent.xid("node-00", 0, 999, "2026-10-01T00:00:00+00:00",
                           source="simulator")
    verdict = TriageAgent().triage_event(e)
    assert verdict.finding.known is False
    assert verdict.finding.severity == "unknown"
