"""Keyword search with BM25Okapi. Rebuilt in memory from the chunks table at startup."""

import math
import re

import numpy as np
from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset("a an and are as at be by for from in is it of on or that the to was were will with".split())


def tokenize(text: str, stopwords: bool = True) -> list[str]:
    toks = _TOKEN.findall(text.lower())
    return [t for t in toks if t not in STOPWORDS] if stopwords else toks


class LuceneBM25(BM25Okapi):
    """BM25Okapi with the Lucene/Elasticsearch IDF: log(1 + (N-n+0.5)/(n+0.5)).

    The textbook IDF log((N-n+0.5)/(n+0.5)) goes NEGATIVE for terms found in more than half
    the documents, which makes tiny or duplicate-heavy corpora return no hits at all.
    """

    def _calc_idf(self, nd: dict) -> None:
        self.average_idf = 0.0
        for word, freq in nd.items():
            self.idf[word] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))
        self.average_idf = sum(self.idf.values()) / len(self.idf) if self.idf else 0.0


class BM25Index:
    def __init__(self) -> None:
        self.chunk_ids: list[int] = []
        self.docs: list[list[str]] = []
        self.bm25: LuceneBM25 | None = None

    def build(self, chunk_ids: list[int], texts: list[str]) -> None:
        self.chunk_ids = chunk_ids
        self.docs = [tokenize(t) for t in texts]
        self.bm25 = LuceneBM25(self.docs) if any(self.docs) else None

    def scores(self, query: str) -> np.ndarray:
        q = tokenize(query)
        if self.bm25 is None or not q:
            return np.zeros(len(self.chunk_ids))
        return np.asarray(self.bm25.get_scores(q), dtype=float)

    def matches(self, query: str) -> np.ndarray:
        """True where the chunk contains at least one query term (independent of score sign)."""
        q = set(tokenize(query))
        return np.array([bool(q & set(d)) for d in self.docs], dtype=bool)

    def explain_terms(self, query: str, chunk_id: int) -> list[dict]:
        """Per-term BM25 contribution. The contributions sum to scores()[chunk]."""
        if self.bm25 is None:
            return []
        pos = self.chunk_ids.index(chunk_id)
        doc = self.docs[pos]
        b = self.bm25
        out = []
        for term in tokenize(query):
            tf = doc.count(term)
            idf = float(b.idf.get(term, 0.0))
            denom = tf + b.k1 * (1 - b.b + b.b * len(doc) / b.avgdl)
            out.append(
                {
                    "term": term,
                    "tf": tf,
                    "idf": round(idf, 4),
                    "contribution": round(idf * tf * (b.k1 + 1) / denom if tf else 0.0, 4),
                }
            )
        return out
