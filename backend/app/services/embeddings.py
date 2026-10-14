"""Embedding-based intent alignment (DESIGN.md §6 layer 2, Path A).

Compares the confirmed intent with a text rendering of the *whole* tool call — tool name,
description, category **and arguments** — so "allowed tool, wrong arguments" is no longer
invisible to the semantic layer (the MVP mock only looked at the tool name).

Encoders run locally:

- ``HashingEncoder``: deterministic, dependency-free bag of hashed words/bigrams. Good for
  tests and CI; weak semantics.
- ``SentenceTransformerEncoder``: a local sentence-transformers model (default
  all-MiniLM-L6-v2), imported lazily so the gateway runs without it installed.

Raw cosine similarity is mapped to the 0–1 alignment score with per-encoder calibration
(``low_similarity`` → 0, ``high_similarity`` → 1). The defaults are starting points and must be
tuned on the evaluation set before results are reported (DESIGN.md §16 "Thresholds").
"""

import hashlib
import math
from collections import OrderedDict
from collections.abc import Sequence
from typing import Any, Protocol

from app.services.ai import AlignmentContext, AlignmentResult
from app.services.intent import VERB_GROUPS, tokens

EXTERNAL_CATEGORIES = {"external", "delete", "payment", "admin"}
NAME_EFFECT_MARKERS = {
    "external": {"send", "upload", "export", "publish", "post", "share", "forward", "sync"},
    "delete": {"delete", "remove", "erase", "purge", "drop", "wipe"},
    "payment": {"pay", "transfer", "purchase", "refund", "charge"},
}


class Encoder(Protocol):
    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


class HashingEncoder:
    def __init__(self, dimensions: int = 512) -> None:
        self.dimensions = dimensions

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._encode(text) for text in texts]

    def _encode(self, text: str) -> list[float]:
        words = sorted(tokens(text))
        features = list(words)
        ordered = [w for w in text.casefold().replace("_", " ").split() if w]
        features += [f"{a} {b}" for a, b in zip(ordered, ordered[1:], strict=False)]
        vector = [0.0] * self.dimensions
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0 if digest[4] % 2 == 0 else -1.0
        return _normalize(vector)


class SentenceTransformerEncoder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: Any = None

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:  # pragma: no cover - depends on optional extra
                raise RuntimeError(
                    "sentence-transformers is not installed; pip install 'asgp-backend[embeddings]'"
                ) from error
            self._model = SentenceTransformer(self.model_name)
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _flatten(value: Any, prefix: str = "", depth: int = 0) -> list[str]:
    if depth > 3:
        return []
    if isinstance(value, dict):
        items: list[str] = []
        for key, item in list(value.items())[:20]:
            items += _flatten(item, f"{prefix}{key} ", depth + 1)
        return items
    if isinstance(value, (list, tuple)):
        items = []
        for item in value[:10]:
            items += _flatten(item, prefix, depth + 1)
        return items
    return [f"{prefix}{str(value)[:200]}"]


def describe_call(context: AlignmentContext) -> str:
    arguments = "; ".join(_flatten(context.parameters))[:1_000]
    name = context.tool_name.replace("_", " ").replace(".", " ")
    parts = [name, context.tool_description, f"category {context.tool_category}"]
    if arguments:
        parts.append(f"arguments: {arguments}")
    return ". ".join(part for part in parts if part)


def effect_of(context: AlignmentContext) -> str | None:
    if context.tool_category in EXTERNAL_CATEGORIES:
        return context.tool_category
    name = tokens(context.tool_name)
    for effect, markers in NAME_EFFECT_MARKERS.items():
        if name & markers:
            return effect
    return None


class EmbeddingAlignmentProvider:
    def __init__(
        self,
        encoder: Encoder,
        *,
        low_similarity: float,
        high_similarity: float,
        cache_size: int = 256,
    ) -> None:
        if not 0 <= low_similarity < high_similarity <= 1:
            raise ValueError("Calibration requires 0 <= low < high <= 1")
        self.encoder = encoder
        self.low = low_similarity
        self.high = high_similarity
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._cache_size = cache_size

    def _intent_vector(self, intent: str) -> list[float]:
        cached = self._cache.get(intent)
        if cached is not None:
            self._cache.move_to_end(intent)
            return cached
        vector = self.encoder.encode([intent])[0]
        self._cache[intent] = vector
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return vector

    def score_alignment(self, context: AlignmentContext) -> AlignmentResult:
        intent_vector = self._intent_vector(context.intent)
        call_vector = self.encoder.encode([describe_call(context)])[0]
        similarity = cosine(intent_vector, call_vector)
        score = (similarity - self.low) / (self.high - self.low)
        score = round(max(0.0, min(1.0, score)), 4)
        risk_factors: tuple[str, ...] = ()
        reason = f"Embedding similarity {similarity:.2f} between the call and the intent."
        effect = effect_of(context)
        if effect is not None:
            verbs = VERB_GROUPS.get(effect, frozenset())
            if not tokens(context.intent) & verbs:
                score = min(score, 0.25)
                risk_factors = (f"{effect}_action_not_stated",)
                reason = f"{effect.capitalize()} action is not evident in the original intent."
        return AlignmentResult(score=score, reason=reason, risk_factors=risk_factors)


def build_alignment_provider(name: str, *, model: str = "") -> object:
    """Factory used by the container. ``lexical`` keeps the MVP MockProvider."""
    from app.services.ai import MockProvider

    if name == "lexical":
        return MockProvider()
    if name == "hashing":
        return EmbeddingAlignmentProvider(
            HashingEncoder(), low_similarity=0.0, high_similarity=0.35
        )
    if name == "sentence-transformers":
        return EmbeddingAlignmentProvider(
            SentenceTransformerEncoder(model), low_similarity=0.10, high_similarity=0.45
        )
    raise ValueError(f"Unknown alignment provider: {name}")
