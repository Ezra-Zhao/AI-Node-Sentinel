"""Redfish telemetry connector.

`RedfishClient` is the interface the agent uses to pull out-of-band
telemetry (thermal sensors, power readings, PCIe error counters) from a
node's BMC. In production this is plain HTTPS::

    GET https://<bmc>/redfish/v1/Chassis/1/Thermal
    GET https://<bmc>/redfish/v1/Systems/1/PCIeDevices/...

`SimulatedRedfishClient` returns synthetic data with the same shape so
the pipeline runs end-to-end without BMC access. Every payload is
labeled simulated at the source.

Design intent (interview talking point): in-band signals (dmesg,
nvidia-smi) disappear when the GPU falls off the bus — Xid 79 means the
driver can no longer see the card. Redfish is the *out-of-band* backstop:
the BMC still reports inlet temperature, power draw and PCIe link state,
which is exactly the context needed to tell "dead GPU" apart from
"starved of power / overheated chassis".
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class RedfishClient(ABC):
    """Out-of-band telemetry source for one node."""

    def __init__(self, node_id: str, bmc_host: str) -> None:
        self.node_id = node_id
        self.bmc_host = bmc_host

    @abstractmethod
    def get_thermal(self) -> dict:
        """Chassis/GPU temperatures, e.g. {'inlet_c': 24.0, 'gpu_hotspot_c': 71.5}."""

    @abstractmethod
    def get_power(self) -> dict:
        """Power readings, e.g. {'input_w': 3200, 'psu_redundancy_ok': True}."""

    @abstractmethod
    def get_pcie_errors(self) -> dict:
        """PCIe AER-style counters, e.g. {'correctable': 12, 'uncorrectable': 0}."""


class SimulatedRedfishClient(RedfishClient):
    """Synthetic BMC. All values are invented; shape matches Redfish.

    TODO(Ezra): replace with a real client using `requests` against
    https://<bmc>/redfish/v1/... with HTTP Basic / session auth. The
    interface stays the same, so the agent code does not change.
    """

    # Per-node synthetic profiles keyed by scenario. Demo picks "mixed".
    _PROFILES = {
        "healthy": {"inlet_c": 23.0, "gpu_hotspot_c": 66.0, "input_w": 2900,
                    "psu_redundancy_ok": True, "pcie_correctable": 3,
                    "pcie_uncorrectable": 0},
        "hot": {"inlet_c": 34.0, "gpu_hotspot_c": 91.0, "input_w": 3400,
                "psu_redundancy_ok": True, "pcie_correctable": 210,
                "pcie_uncorrectable": 0},
        "power": {"inlet_c": 24.0, "gpu_hotspot_c": 58.0, "input_w": 1800,
                  "psu_redundancy_ok": False, "pcie_correctable": 45,
                  "pcie_uncorrectable": 2},
    }

    def __init__(self, node_id: str, bmc_host: str = "bmc-simulated",
                 profile: str = "healthy") -> None:
        super().__init__(node_id, bmc_host)
        if profile not in self._PROFILES:
            raise ValueError(f"unknown profile {profile!r}")
        self._p = self._PROFILES[profile]

    def _meta(self) -> dict:
        return {"node_id": self.node_id, "bmc": self.bmc_host,
                "simulated": True,
                "ts": datetime.now(timezone.utc).isoformat()}

    def get_thermal(self) -> dict:
        return {**self._meta(),
                "inlet_c": self._p["inlet_c"],
                "gpu_hotspot_c": self._p["gpu_hotspot_c"],
                "thermal_alert": self._p["gpu_hotspot_c"] > 85.0}

    def get_power(self) -> dict:
        return {**self._meta(),
                "input_w": self._p["input_w"],
                "psu_redundancy_ok": self._p["psu_redundancy_ok"]}

    def get_pcie_errors(self) -> dict:
        return {**self._meta(),
                "correctable": self._p["pcie_correctable"],
                "uncorrectable": self._p["pcie_uncorrectable"]}


# ---- Redfish event payload parsing ----------------------------------------

# Clean-room mapping from Redfish Event MessageIds to our normalized event
# kinds. Based on the DMTF Redfish Event schema shape
# ("@odata.type": "#Event.v*_Event", "Events": [{...}]) and the common
# registry prefixes (ThermalEvent, PowerEvent, PCIe-related). Prefixes are
# matched case-insensitively; anything unmatched lands in kind="health"
# with the raw message preserved.
_MESSAGEID_KIND = (
    (("temp", "thermal"), "thermal"),
    (("power", "psu", "powersupply", "powerredundancy"), "power"),
    (("pcie", "aer"), "pcie"),
    (("fan",), "thermal"),
)


def _kind_for_message_id(message_id: str) -> str:
    mid = (message_id or "").lower()
    for needles, kind in _MESSAGEID_KIND:
        if any(n in mid for n in needles):
            return kind
    return "health"


_SEVERITY_MAP = {"critical": "critical", "warning": "warning", "ok": "ok"}


def parse_event(event: dict, node_id: str) -> "TelemetryEvent":
    """Parse one Redfish event dict into a TelemetryEvent.

    Accepts the DMTF Redfish event shape (EventType, EventId, Severity,
    Message, MessageId, EventTimestamp, OriginOfCondition). Missing fields
    degrade gracefully — the raw event is always kept in the payload.
    """
    # Local import to avoid a hard cycle at module import time.
    from agent.schemas import TelemetryEvent

    message_id = event.get("MessageId", "")
    severity = _SEVERITY_MAP.get(str(event.get("Severity", "")).lower(), "unknown")
    origin = event.get("OriginOfCondition") or {}
    sensor = origin.get("@odata.id", "") if isinstance(origin, dict) else str(origin)
    ts = event.get("EventTimestamp") or datetime.now(timezone.utc).isoformat()
    return TelemetryEvent(
        node_id=node_id,
        gpu_index=-1,  # Redfish is chassis-level; GPU attribution is heuristic
        timestamp=ts,
        source="redfish",
        kind=_kind_for_message_id(message_id),
        payload={
            "message_id": message_id,
            "severity": severity,
            "message": (event.get("Message") or "")[:300],
            "sensor": sensor,
            "event_type": event.get("EventType", ""),
            "event_id": event.get("EventId", ""),
        },
    )


def parse_events(payload: dict, node_id: str) -> list["TelemetryEvent"]:
    """Parse a Redfish event collection ({"Events": [...]}) into events."""
    events = payload.get("Events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        return []
    return [parse_event(e, node_id) for e in events if isinstance(e, dict)]
