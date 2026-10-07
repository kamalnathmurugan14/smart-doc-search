"""Embedders + the in-memory matrix used for cosine search."""

import logging
import re
import zlib
from typing import Protocol

import numpy as np

log = logging.getLogger(__name__)
_WORD = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    name: str
    dim: int

    def encode(self, texts: list[str]) -> np.ndarray: ...


class HashingEmbedder:
    """Offline fallback: hashed bag of words + bigrams, L2-normalised.

    It captures lexical overlap only (no synonyms) - good enough to run everything
    without downloading a model. The real model understands paraphrases.
    """

    name = "hashing"

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for r, text in enumerate(texts):
            words = _WORD.findall(text.lower())
            feats = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
            for f in feats:
                h = zlib.crc32(f.encode())
                out[r, h % self.dim] += 1.0 if (h >> 16) & 1 else -1.0
        out = np.sign(out) * np.sqrt(np.abs(out))  # dampen repeated terms
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1, norms)


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # heavy import, kept lazy

        self.name = model_name
        self._model = SentenceTransformer(model_name)
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._model.encode(texts, normalize_embeddings=True, batch_size=32), dtype=np.float32)


def build_embedder(model_name: str) -> Embedder:
    if model_name.lower() == "hashing":
        return HashingEmbedder()
    try:
        return SentenceTransformerEmbedder(model_name)
    except Exception as exc:  # noqa: BLE001 - missing package or no network
        log.warning("embedder_fallback model=%s reason=%s", model_name, type(exc).__name__)
        return HashingEmbedder()


class EmbeddingIndex:
    """Normalised chunk vectors in one matrix; cosine = matrix @ query."""

    def __init__(self) -> None:
        self.chunk_ids: list[int] = []
        self.matrix = np.zeros((0, 0), dtype=np.float32)

    def build(self, chunk_ids: list[int], vectors: list[np.ndarray]) -> None:
        self.chunk_ids = chunk_ids
        self.matrix = np.vstack(vectors).astype(np.float32) if vectors else np.zeros((0, 0), dtype=np.float32)

    def scores(self, query_vec: np.ndarray) -> np.ndarray:
        if self.matrix.size == 0 or self.matrix.shape[1] != query_vec.shape[0]:
            return np.zeros(len(self.chunk_ids), dtype=np.float32)
        return self.matrix @ query_vec
