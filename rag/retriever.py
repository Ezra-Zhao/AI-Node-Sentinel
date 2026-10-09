"""TF-IDF retriever (standard library only).

Retrieval-Augmented Generation, minimal edition: given a query built from
a triage finding (XID code, name, severity, node context), return the
top-k knowledge-base chunks ranked by TF-IDF cosine similarity.

Design intent (interview talking point): the alternative is stuffing the
whole runbook into every LLM prompt (expensive, noisy) or relying on the
model's parametric memory (stale, hallucinates vendor specifics). A tiny
lexical retriever keeps the agent grounded in *our* runbook text, costs
nothing to run, and is fully deterministic — which is what you want at
3am when the same XID should produce the same guidance twice.

Why TF-IDF instead of embeddings: zero dependencies, runs on the node
itself, no GPU, no API key. For a ~10-chunk runbook, lexical overlap
(XID codes, terms like "drain"/"RMA"/"thermal") is exactly the signal
that matters. If the KB grows past a few hundred chunks, swap this for
an embedding index behind the same `retrieve()` signature.
"""
from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens; drops punctuation/stopwords-by-length."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 2]


class TfidfRetriever:
    def __init__(self, documents: dict[str, str]) -> None:
        # Precompute document TF vectors and corpus IDF once at build time.
        self._doc_ids = list(documents.keys())
        self._tf: list[Counter] = [Counter(tokenize(documents[d]))
                                   for d in self._doc_ids]
        df: Counter = Counter()
        for tf in self._tf:
            for term in tf:
                df[term] += 1
        n = len(self._doc_ids)
        # Smoothed IDF so a term in every doc still carries some weight.
        self._idf = {t: math.log((n + 1) / (c + 1)) + 1.0
                     for t, c in df.items()}
        # Precompute doc vector norms for cosine similarity.
        self._norms = [math.sqrt(sum((tf[t] * self._idf.get(t, 0.0)) ** 2
                                     for t in tf)) or 1.0
                       for tf in self._tf]

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        return {t: tf[t] * self._idf[t] for t in tf if t in self._idf}

    def retrieve(self, query: str, top_k: int = 2) -> list[tuple[str, float]]:
        """Return [(chunk_id, score)] for the top-k chunks, score in [0, 1]."""
        qv = self._vector(tokenize(query))
        qnorm = math.sqrt(sum(v * v for v in qv.values())) or 1.0
        scored = []
        for doc_id, tf, dnorm in zip(self._doc_ids, self._tf, self._norms):
            dot = sum(qv.get(t, 0.0) * tf[t] * self._idf[t] for t in qv)
            scored.append((doc_id, dot / (qnorm * dnorm)))
        scored.sort(key=lambda s: s[1], reverse=True)
        return scored[:top_k]

    def retrieve_texts(self, query: str, top_k: int = 2,
                       documents: dict[str, str] | None = None) -> list[str]:
        """Convenience: return the chunk texts instead of (id, score)."""
        docs = documents or {}
        return [docs[cid] for cid, _ in self.retrieve(query, top_k) if cid in docs]
