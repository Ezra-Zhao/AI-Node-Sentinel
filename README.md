# AI-Node-Sentinel

**Post-Silicon Hardware Diagnostic Agent for PCIe/XID Triage**

An AI-agent-based diagnostic pipeline for GPU node failures in AI infrastructure:
it ingests node telemetry (kernel logs, DCGM/NVML metrics), identifies NVIDIA XID
error events, and produces structured triage verdicts — so on-call engineers get
"what broke, how bad, what to do first" instead of raw `dmesg` output.

Built for the realities of large GPU fleets (post-silicon validation, data-center
operations, and AI training clusters where one bad GPU can stall thousands of others).

> **Project status: scaffold v0.1 (honest edition).**
> The end-to-end pipeline runs today on **simulated** telemetry. What is real:
> event ingestion, XID lookup against public documentation, report rendering.
> What is still TODO (clearly marked in code): the field-validated XID→remediation
> decision tree and the LangChain LLM reasoning step. Nothing in this repo pretends
> to be a production diagnostician yet.

---

## Problem

In a 1,000+ GPU cluster, XID errors (NVIDIA's hardware/firmware error codes) are
the first signal that a GPU is degrading — but triage today is manual:

1. An engineer greps `dmesg` across nodes for `Xid`.
2. They look up what the code means (NVIDIA Xid catalog, tribal knowledge).
3. They decide: drain the node? reset the GPU? reboot? RMA the card?
4. Meanwhile the training job keeps retrying on broken hardware.

Slow triage = wasted GPU-hours = real money at AI-infra scale.

## Architecture

```
                    +-------------------+
                    |  Node Telemetry   |
                    | dmesg / DCGM /    |
                    | NVML  (simulated) |
                    +--------+----------+
                             |
                             v
                    +--------+----------+
                    | Event Ingestion   |  agent/schemas.py
                    | (parse, normalize)|
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
              v                             v
   +----------+----------+        +---------+---------+
   | XID Lookup Table  |        | Triage Decision   |
   | tools/xid_lookup  |        | Tree    [TODO]    |
   | (public docs)     |        |                   |
   +----------+----------+        +---------+---------+
              |                             |
              +--------------+--------------+
                             |
                             v
                    +--------+----------+
                    |  Triage Agent     |  agent/orchestrator.py
                    |  orchestration;   |
                    |  LLM reasoning    |
                    |  via LangChain    |
                    |      [TODO]       |
                    +--------+----------+
                             |
                             v
                    +--------+----------+
                    |  Triage Report    |
                    |  console + JSON   |
                    +-------------------+
```

Pipeline stages:

| Stage | Module | Status |
|---|---|---|
| Telemetry ingestion & normalization | `agent/schemas.py` | ✅ Implemented |
| XID code → metadata lookup | `tools/xid_lookup.py` | ✅ Seeded from public NVIDIA docs |
| Severity classification | `tools/triage_rules.py` | ⚠️ Stub — returns `NEEDS_HUMAN_REVIEW` |
| Triage decision tree (drain/reset/reboot/RMA) | `tools/triage_rules.py` | 🔲 TODO — owner's domain |
| LLM chain-of-thought reasoning | `agent/llm.py` | 🔲 TODO — LangChain adapter stub |
| Report rendering (console + JSON) | `agent/orchestrator.py` | ✅ Implemented |
| Simulated telemetry generator | `telemetry/simulator.py` | ✅ Implemented (synthetic data only) |

## Tech Stack

- **Python 3.11+**, `pydantic` for schemas
- **LangChain** (`requirements-llm.txt`, optional) — reserved for the LLM reasoning step
- `pytest` for tests; GitHub Actions CI

## Quickstart (2 minutes, no GPU required)

```bash
git clone https://github.com/<you>/AI-Node-Sentinel.git
cd AI-Node-Sentinel
pip install -r requirements.txt

# End-to-end demo on SIMULATED telemetry:
python examples/demo.py
```

The demo simulates a 4-node cluster, injects synthetic XID events, runs the full
triage pipeline, prints a report, and writes `examples/demo_report.json`.
Every event is labeled simulated — see `telemetry/simulator.py`.

```bash
# Run tests
python -m pytest tests/ -q
```

### Wiring a real LLM (TODO)

```bash
pip install -r requirements-llm.txt   # langchain stack
```

Then implement `LangChainChatProvider` in `agent/llm.py` and pass it to
`TriageAgent(llm=...)`. The system prompt draft lives in
`prompts/triage_system.md`.

## Roadmap

- [x] v0.1 scaffold: pipeline, simulator, demo, tests, CI
- [ ] Encode field-validated XID → remediation decision tree (`tools/triage_rules.py`)
- [ ] LangChain reasoning step with evidence-grounded prompts (`agent/llm.py`)
- [ ] Real telemetry connectors: `dmesg` parser, DCGM exporter, NVML
- [ ] Recurring-fault detection across time windows (flapping GPUs)
- [ ] Alertmanager / PagerDuty webhook output

## License

MIT — see [LICENSE](LICENSE).

## Attribution

XID code metadata seeded from NVIDIA's public XID error documentation
(`https://docs.nvidia.com/deploy/xid-errors/`) and Google Cloud's GPU
troubleshooting guide. This repo is not affiliated with NVIDIA.
