"""End-to-end demo on SIMULATED telemetry.

Pipeline exercised:
  1. Parse a synthetic dmesg capture      (telemetry/dmesg.py)
  2. Parse synthetic nvidia-smi CSV       (telemetry/nvidia_smi.py)
  3. Pull synthetic Redfish BMC telemetry  (telemetry/redfish.py)
  4. RAG: retrieve runbook evidence       (rag/)
  5. Apply the triage decision tree       (tools/triage_rules.py)
  6. Render console + markdown + JSON reports

NO real hardware is touched. NO LLM calls are made (deterministic mode).
Set AI_SENTINEL_LLM=1 with requirements-llm.txt installed and OPENAI_API_KEY
set to add the LangChain reasoning step.

Run from the repo root:  python examples/demo.py
"""
import json
import os
import sys
from pathlib import Path

# Allow running as a script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.llm import LangChainChatProvider
from agent.orchestrator import TriageAgent
from telemetry.dmesg import parse_text as parse_dmesg
from telemetry.nvidia_smi import parse_csv as parse_smi
from telemetry.redfish import SimulatedRedfishClient

HERE = Path(__file__).resolve().parent


def main() -> None:
    print(">>> AI-Node-Sentinel demo — ALL TELEMETRY IS SIMULATED <<<\n")

    # 1+2. In-band signals: dmesg + nvidia-smi (synthetic samples).
    events = parse_dmesg((HERE.parent / "telemetry" / "sample_dmesg.log").read_text(),
                        node_id="node-01")
    events += parse_smi((HERE.parent / "telemetry" / "sample_nvidia_smi.csv").read_text(),
                        node_id="node-01")

    # 3. Out-of-band: Redfish BMC telemetry. The "hot" profile correlates
    # with the XID 79s in the dmesg sample (thermal trip, not dead GPU).
    redfish = SimulatedRedfishClient("node-01", profile="hot")
    thermal = redfish.get_thermal()
    power = redfish.get_power()
    pcie = redfish.get_pcie_errors()
    node_context = {
        "node-01": {
            "thermal_alert": thermal["thermal_alert"],
            "power_degraded": (not power["psu_redundancy_ok"]
                               or pcie["uncorrectable"] > 0),
        }
    }
    print(f"Redfish (simulated): inlet={thermal['inlet_c']}C "
          f"hotspot={thermal['gpu_hotspot_c']}C thermal_alert={thermal['thermal_alert']}\n")

    # Optional LLM reasoning step.
    llm = None
    if os.environ.get("AI_SENTINEL_LLM") == "1":
        llm = LangChainChatProvider()
        print("LLM reasoning: enabled (LangChain)\n")
    else:
        print("LLM reasoning: off (deterministic mode; "
              "set AI_SENTINEL_LLM=1 to enable)\n")

    # 4+5. Triage.
    agent = TriageAgent(llm=llm)
    report = agent.run(events, node_count=1, simulated=True,
                       node_context=node_context)

    print(agent.render(report))

    # 6. Artifacts.
    md_path = HERE / "demo_report.md"
    md_path.write_text(agent.render_md(report))
    json_path = HERE / "demo_report.json"
    json_path.write_text(json.dumps(agent.report_dict(report), indent=2, default=str))
    print(f"\nMarkdown report written to {md_path}")
    print(f"JSON report written to {json_path}")


if __name__ == "__main__":
    main()
