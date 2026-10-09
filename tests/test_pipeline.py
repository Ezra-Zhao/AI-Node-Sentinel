"""Pipeline tests: determinism, lookup honesty, decision tree, report shape,
Redfish event parsing."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.orchestrator import TriageAgent
from agent.schemas import TelemetryEvent
from telemetry import redfish as redfish_mod
from telemetry.dmesg import parse_text as parse_dmesg
from telemetry.simulator import XID_POOL, simulate_cluster
from tools.triage_rules import triage_decision
from tools.xid_lookup import XID_INFO, lookup_xid

REPO = Path(__file__).resolve().parents[1]


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


def test_decision_tree_dbe_drains():
    d = triage_decision(48, context={"known": True, "repeat_count": 1})
    assert d.action == "DRAIN_NODE"
    assert d.confidence >= 0.8


def test_decision_tree_repeat_dbe_escalates_to_rma():
    d = triage_decision(48, context={"known": True, "repeat_count": 2})
    assert d.action == "DRAIN_NODE_AND_OPEN_RMA"


def test_decision_tree_app_level_does_not_drain():
    d = triage_decision(13, context={"known": True, "repeat_count": 1})
    assert d.action == "CHECK_APPLICATION"


def test_decision_tree_unknown_stays_human_review():
    d = triage_decision(999, context={"known": False})
    assert d.action == "NEEDS_HUMAN_REVIEW"


def test_pipeline_report_shape():
    events = simulate_cluster(num_nodes=2, gpus_per_node=4, seed=1)
    agent = TriageAgent()
    report = agent.run(events, node_count=2, simulated=True)
    assert report.simulated is True
    assert report.node_count == 2
    assert report.event_count == len(events)
    for v in report.verdicts:
        assert v.finding.node_id.startswith("node-")
        assert 0.0 <= v.confidence <= 1.0
        assert v.rationale  # every verdict explains itself


def test_unknown_xid_marked_unknown_severity():
    e = TelemetryEvent.xid("node-00", 0, 999, "2026-10-01T00:00:00+00:00",
                           source="simulator")
    verdict = TriageAgent().triage_event(e, context={})
    assert verdict.finding.known is False
    assert verdict.finding.severity == "unknown"
    assert verdict.action == "NEEDS_HUMAN_REVIEW"


def test_verdicts_carry_rag_evidence():
    e = TelemetryEvent.xid("node-00", 0, 79, "2026-10-01T00:00:00+00:00",
                           source="dmesg")
    verdict = TriageAgent().triage_event(e, context={"known": True})
    assert len(verdict.evidence) > 0
    chunk_ids = [cid for cid, _ in verdict.evidence]
    assert any("79" in cid or "bus" in cid for cid in chunk_ids)


# ---- extended XID table (NVIDIA public catalog, clean-room summaries) ----

def test_lookup_extended_xids_known():
    expected = {45: "low", 62: "critical", 63: "info", 64: "high", 92: "medium"}
    for code, severity in expected.items():
        info = lookup_xid(code)
        assert info is not None, f"XID {code} should be known"
        assert info["severity"] == severity, f"XID {code} severity"
        assert info["name"] and info["category"]


def test_lookup_table_size():
    # 12 real codes + lookup-miss exercised via 999 (not in the table).
    assert len(XID_INFO) >= 12


def test_decision_tree_abort_ignored():
    d = triage_decision(45, context={"known": True, "repeat_count": 1})
    assert d.action == "IGNORE_EVENT"


def test_decision_tree_pmu_reset_then_escalate():
    d = triage_decision(62, context={"known": True, "repeat_count": 1})
    assert d.action == "RESET_GPU"
    d2 = triage_decision(62, context={"known": True, "repeat_count": 2})
    assert d2.action == "DRAIN_NODE_AND_ESCALATE"


def test_decision_tree_remap_events():
    d = triage_decision(63, context={"known": True, "repeat_count": 1})
    assert d.action == "MONITOR"  # informational by design
    d2 = triage_decision(64, context={"known": True, "repeat_count": 1})
    assert d2.action == "RESET_GPU"


def test_decision_tree_high_sbe_watched():
    d = triage_decision(92, context={"known": True, "repeat_count": 1})
    assert d.action == "MONITOR"
    d2 = triage_decision(92, context={"known": True, "repeat_count": 3})
    assert d2.action == "DRAIN_NODE_AND_ESCALATE"


def test_simulator_pool_covers_new_xids():
    assert {45, 62, 63, 64, 92} <= set(XID_POOL)


def test_dmesg_parses_new_xid_lines():
    line = ("[  7890.654321] NVRM: Xid (PCI:0000:84:00): 92, "
            "pid='<unknown>', name=<unknown>, Excessive single-bit ECC interrupts")
    events = parse_dmesg(line, node_id="node-01")
    assert len(events) == 1
    assert events[0].payload["xid"] == 92
    verdict = TriageAgent().triage_event(events[0], context={"known": True})
    assert verdict.finding.severity == "medium"
    assert verdict.action == "MONITOR"


# ---- Redfish event payload parsing ----

def test_redfish_event_parsing_kinds():
    payload = json.loads((REPO / "telemetry" / "sample_redfish_events.json").read_text())
    events = redfish_mod.parse_events(payload, node_id="node-01")
    assert len(events) == 4
    kinds = {e.payload["message_id"]: e.kind for e in events}
    assert kinds["ThermalEvent.1.0.TempReadingHigh"] == "thermal"
    assert kinds["PowerEvent.1.0.PowerSupplyRedundancyLost"] == "power"
    assert kinds["PCIeEvent.1.0.UncorrectableError"] == "pcie"
    for e in events:
        assert e.source == "redfish"
        assert e.node_id == "node-01"
        assert e.gpu_index == -1  # chassis-level, not GPU-attributed


def test_redfish_event_severity_mapping():
    payload = json.loads((REPO / "telemetry" / "sample_redfish_events.json").read_text())
    events = redfish_mod.parse_events(payload, node_id="node-01")
    sev = {e.payload["message_id"]: e.payload["severity"] for e in events}
    assert sev["ThermalEvent.1.0.TempReadingHigh"] == "critical"
    assert sev["PowerEvent.1.0.PowerSupplyRedundancyLost"] == "warning"
    assert sev["FanEvent.1.0.FanSpeedNormal"] == "ok"


def test_redfish_parse_degrades_gracefully():
    assert redfish_mod.parse_events({}, "node-01") == []
    assert redfish_mod.parse_events({"Events": "nope"}, "node-01") == []
    # Missing fields must not raise; raw event is preserved.
    ev = redfish_mod.parse_event({}, "node-01")
    assert ev.kind == "health"
    assert ev.payload["severity"] == "unknown"
