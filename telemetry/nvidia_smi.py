"""nvidia-smi output parser.

Parses the CSV produced by::

    nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,\
pstate,ecc.errors.uncorrected.volatile.total --format=csv,noheader

Design intent: nvidia-smi is the cheapest fleet-wide health signal —
one SSH/parallel-ssh sweep gives temperature, utilization and ECC
counters for every GPU. The parser turns each row into ``thermal`` and
``ecc`` events; an uncorrected ECC total > 0 becomes an ``xid``-like
event (code 48, DBE) so the triage pipeline handles it uniformly.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO

from agent.schemas import TelemetryEvent

# nvidia-smi reports "N/A" or "[N/A]" when a counter is unsupported.
_NA = {"N/A", "[N/A]", ""}


def _to_int(value: str) -> int | None:
    v = value.strip()
    if v in _NA:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def parse_csv(text: str, node_id: str) -> list[TelemetryEvent]:
    """Parse nvidia-smi CSV rows into thermal/ECC TelemetryEvents."""
    now = datetime.now(timezone.utc).isoformat()
    events: list[TelemetryEvent] = []
    reader = csv.reader(StringIO(text.strip()))
    for row in reader:
        if not row or row[0].strip().startswith("#"):
            continue
        # index, name, temp_c, util_pct, pstate, dbe_total
        if len(row) < 6:
            continue
        try:
            gpu_index = int(row[0].strip())
        except ValueError:
            continue  # header row or garbage
        temp_c = _to_int(row[2])
        util = _to_int(row[3])
        dbe = _to_int(row[5])

        payload = {"gpu_name": row[1].strip(), "pstate": row[4].strip()}
        if temp_c is not None:
            events.append(TelemetryEvent(
                node_id=node_id, gpu_index=gpu_index, timestamp=now,
                source="nvidia-smi", kind="thermal",
                payload={**payload, "temp_c": temp_c,
                         "util_pct": util if util is not None else -1}))
        if dbe is not None:
            events.append(TelemetryEvent(
                node_id=node_id, gpu_index=gpu_index, timestamp=now,
                source="nvidia-smi", kind="ecc",
                payload={**payload, "dbe": dbe}))
            if dbe > 0:
                # Surface DBE through the same triage path as a dmesg Xid 48.
                events.append(TelemetryEvent(
                    node_id=node_id, gpu_index=gpu_index, timestamp=now,
                    source="nvidia-smi", kind="xid",
                    payload={"xid": 48, "dbe_total": dbe,
                             "note": "uncorrected ECC counter > 0"}))
    return events
