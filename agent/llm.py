"""LLM provider abstraction.

Deterministic mode (llm=None) is the default and needs no API key. To add
an LLM reasoning step on top of the rule-based verdicts::

    pip install -r requirements-llm.txt   # langchain stack
    export OPENAI_API_KEY=...            # or any ChatOpenAI-compatible key
    agent = TriageAgent(llm=LangChainChatProvider())

The LLM never *replaces* the decision tree — it appends a grounded
analysis line to the rationale. Rules decide; the model explains.
"""
from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Minimal interface the orchestrator needs from any LLM backend."""

    def reason(self, system_prompt: str, evidence: str) -> str:
        """Return chain-of-thought style analysis grounded in `evidence`."""
        ...


class LangChainChatProvider:
    """LangChain-backed provider. Lazy import: only needs langchain at use time.

    Design intent: keep the core pipeline dependency-free (it must run on a
    bare node), and treat the LLM as an optional reasoning upgrade. The
    import happens in __init__ so a missing `langchain-openai` fails fast
    with a clear message instead of at 3am mid-triage.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0) -> None:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise RuntimeError(
                "LangChainChatProvider needs the LLM stack: "
                "pip install -r requirements-llm.txt") from e
        # ChatOpenAI reads OPENAI_API_KEY from the environment.
        self.chat = ChatOpenAI(model=model, temperature=temperature)

    def reason(self, system_prompt: str, evidence: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage
        resp = self.chat.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=(
                "Analyze this hardware triage evidence. Ground every claim "
                "in the evidence below; do not invent remediation steps.\n\n"
                f"{evidence}")),
        ])
        return str(resp.content)
