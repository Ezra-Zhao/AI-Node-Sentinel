"""Triage decision tree.

Scaffold v0.1: INTENTIONALLY A STUB.

The real decision tree (XID + context -> drain / reset / reboot / RMA /
escalate, with confidence thresholds) encodes field experience and must be
written by someone who has operated GPU fleets. Fabricating remediation
rules here would be worse than useless — it would be dishonest.

TODO(Ezra): replace triage_decision() with the real policy, e.g.:
  - XID 79 twice in 24h on the same GPU -> DRAIN_NODE + REBOOT, page on-call
  - XID 48 (DBE) -> DRAIN_NODE + RUN_FIELDDIAG, open RMA ticket if recurring
  - XID 13/31 (app-level) -> CHECK_APP, do NOT drain the node
  - unknown XID -> NEEDS_HUMAN_REVIEW (keep this fallback forever)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TriageDecision:
    action: str        # e.g. "DRAIN_NODE", "RESET_GPU", "NEEDS_HUMAN_REVIEW"
    confidence: float  # 0.0 - 1.0
    rationale: str


def triage_decision(xid_code: int, context: dict) -> TriageDecision:
    """Stub: every event routes to human review with zero confidence.

    DO NOT ship remediation actions from this stub. Encode the real tree
    (see module docstring) before connecting to any alerting system.
    """
    known = context.get("known", False)
    return TriageDecision(
        action="NEEDS_HUMAN_REVIEW",
        confidence=0.0,
        rationale=(
            f"Decision tree not yet encoded (scaffold v0.1). "
            f"XID {xid_code} is {'known' if known else 'UNKNOWN'} to the lookup table; "
            f"no automated remediation taken."
        ),
    )
