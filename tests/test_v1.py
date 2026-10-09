"""v1 module tests: dmesg/nvidia-smi parsers, Redfish sim, RAG retriever."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.knowledge_base import KNOWLEDGE_BASE
from rag.retriever import TfidfRetriever
from telemetry.dmesg import parse_line, parse_text
from telemetry.nvidia_smi import parse_csv
from telemetry.redfish import SimulatedRedfishClient

DMESG_LINE = ("[ 1234.567890] NVRM: Xid (PCI:0000:41:00): 79, pid='<unknown>', "
              "name=<unknown>, GPU has fallen off the bus")
NOISE_LINE = "[ 1234.567890] usb 1-2: new high-speed USB device number 4"


def test_dmesg_parses_xid_line():
    ev = parse_line(DMESG_LINE, node_id="node-01")
    assert ev is not None
    assert ev.kind == "xid"
    assert ev.payload["xid"] == 79
    assert ev.payload["pci"] == "0000:41:00"
    assert ev.source == "dmesg"


def test_dmesg_skips_non_xid_lines():
    assert parse_line(NOISE_LINE, node_id="node-01") is None
    assert parse_line("", node_id="node-01") is None


def test_dmesg_parses_sample_log():
    text = (Path(__file__).resolve().parents[1]
            / "telemetry" / "sample_dmesg.log").read_text()
    events = parse_text(text, node_id="node-01")
    codes = sorted(e.payload["xid"] for e in events)
    assert codes == [13, 45, 48, 62, 79, 79, 92, 119, 120]  # usb noise line skipped


def test_nvidia_smi_parses_rows_and_surfaces_dbe():
    csv_text = ("0, NVIDIA H100 80GB HBM3, 61, 98, P0, 0\n"
                "3, NVIDIA H100 80GB HBM3, 58, 99, P0, 2\n")
    events = parse_csv(csv_text, node_id="node-01")
    kinds = [e.kind for e in events]
    assert "thermal" in kinds and "ecc" in kinds
    # dbe=2 on gpu 3 must surface as an XID 48 event for uniform triage.
    xid48 = [e for e in events
             if e.kind == "xid" and e.payload["xid"] == 48]
    assert len(xid48) == 1 and xid48[0].gpu_index == 3


def test_redfish_sim_profiles():
    hot = SimulatedRedfishClient("node-01", profile="hot")
    assert hot.get_thermal()["thermal_alert"] is True
    healthy = SimulatedRedfishClient("node-01", profile="healthy")
    assert healthy.get_thermal()["thermal_alert"] is False
    assert healthy.get_power()["psu_redundancy_ok"] is True
    degraded = SimulatedRedfishClient("node-01", profile="power")
    assert degraded.get_power()["psu_redundancy_ok"] is False


def test_retriever_finds_relevant_chunk():
    r = TfidfRetriever(KNOWLEDGE_BASE)
    top = r.retrieve("XID 79 GPU has fallen off the bus critical", top_k=2)
    assert top[0][0] == "xid-79-bus"
    assert 0.0 < top[0][1] <= 1.0


def test_retriever_thermal_query():
    r = TfidfRetriever(KNOWLEDGE_BASE)
    top = r.retrieve("Redfish thermal alert inlet temperature hotspot", top_k=3)
    ids = [cid for cid, _ in top]
    assert "redfish-thermal" in ids
