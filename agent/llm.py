"""LLM provider abstraction.

Scaffold v0.1 runs in DETERMINISTIC mode (no LLM). The LangChain wiring
point is defined here so the reasoning step can be plugged in later
without touching the pipeline.

TODO(Ezra): implement LangChainChatProvider once an API key / local model
endpoint is available, then pass it to TriageAgent(llm=...).
"""
from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Minimal interface the orchestrator needs from any LLM backend."""

    def reason(self, system_prompt: str, evidence: str) -> str:
        """Return chain-of-thought style analysis grounded in `evidence`."""
        ...


class LangChainChatProvider:
    """LangChain-backed provider. NOT IMPLEMENTED in scaffold v0.1.

    Intended implementation (requires requirements-llm.txt):
        from langchain_openai import ChatOpenAI
        self.chat = ChatOpenAI(model=model, temperature=0)
    then format system_prompt + evidence into messages and invoke.
    """

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        raise NotImplementedError(
            "LangChainChatProvider is a stub in scaffold v0.1. "
            "See prompts/triage_system.md for the system prompt draft."
        )

    def reason(self, system_prompt: str, evidence: str) -> str:  # pragma: no cover
        raise NotImplementedError
