"""SIMULATED node telemetry generator.

Every event produced here is SYNTHETIC. Its only purpose is to let the
triage pipeline run end-to-end without access to real GPU hardware.
Event shapes mirror what real dmesg / DCGM / NVML parsers would emit
(see agent/schemas.py).

Deterministic: same seed -> same events (tests rely on this).
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from agent.schemas import TelemetryEvent

# Pool of XID codes to inject. 999 is a synthetic UNKNOWN code that
# exercises the lookup-miss path; it does not exist in NVIDIA docs.
XID_POOL = [13, 31, 48, 74, 79, 119, 120, 999]


def simulate_cluster(num_nodes: int = 4, gpus_per_node: int = 8,
                     seed: int = 42,
                     start: datetime | None = None) -> list[TelemetryEvent]:
    """Generate a synthetic cluster telemetry window."""
    rng = random.Random(seed)
    start = start or datetime(2026, 10, 1, 6, 0, 0, tzinfo=timezone.utc)
    events: list[TelemetryEvent] = []
    ts = start

    for n in range(num_nodes):
        node_id = f"node-{n:02d}"
        for g in range(gpus_per_node):
            # Baseline health signals (synthetic but plausible ranges).
            events.append(TelemetryEvent(
                node_id=node_id, gpu_index=g, timestamp=ts.isoformat(),
                source="simulator", kind="thermal",
                payload={"temp_c": round(rng.uniform(55, 78), 1)}))
            events.append(TelemetryEvent(
                node_id=node_id, gpu_index=g, timestamp=ts.isoformat(),
                source="simulator", kind="ecc",
                payload={"sbe": rng.randint(0, 3), "dbe": 0}))
            # Inject 0-2 XID events on a random subset of GPUs.
            if rng.random() < 0.35:
                for _ in range(rng.randint(1, 2)):
                    code = rng.choice(XID_POOL)
                    ts = ts + timedelta(seconds=rng.randint(5, 300))
                    events.append(TelemetryEvent.xid(
                        node_id, g, code, ts.isoformat(), source="simulator"))
    # Chronological order, like a real log stream.
    events.sort(key=lambda e: e.timestamp)
    return events
