# Prompt assets

## triage_system.md
Draft system prompt for the LLM reasoning step (see `agent/llm.py`).
Status: **draft v0.1 — written, not yet wired or evaluated.**

Design principles baked in:
1. **Evidence-grounded**: the model may only cite XID codes and telemetry
   present in the provided evidence block — no guessing at unseen signals.
2. **Conservative by default**: unknown codes and low-confidence cases must
   escalate to human review, never auto-remediate.
3. **Operational output**: verdicts map to a fixed action vocabulary
   (see `tools/triage_rules.py` TODO) so downstream alerting stays predictable.

Review and red-team this prompt against real incidents before production use.
