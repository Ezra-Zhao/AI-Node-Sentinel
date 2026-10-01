"""End-to-end demo on SIMULATED telemetry.

Simulates a small GPU cluster, injects synthetic XID events, runs the full
triage pipeline, prints a report, and writes examples/demo_report.json.

NO real hardware is touched. NO LLM calls are made (deterministic mode).
Run from the repo root:  python examples/demo.py
"""
import json
import sys
from pathlib import Path

# Allow running as a script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.orchestrator import TriageAgent
from telemetry.simulator import simulate_cluster


def main() -> None:
    print(">>> AI-Node-Sentinel demo — ALL TELEMETRY IS SIMULATED <<<\n")
    events = simulate_cluster(num_nodes=4, gpus_per_node=8, seed=42)
    agent = TriageAgent()  # llm=None -> deterministic scaffold mode
    report = agent.run(events, node_count=4, simulated=True)

    print(agent.render(report))

    out = Path(__file__).resolve().parent / "demo_report.json"
    out.write_text(json.dumps(agent.report_dict(report), indent=2, default=str))
    print(f"\nJSON report written to {out}")


if __name__ == "__main__":
    main()
