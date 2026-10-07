"""Keyword / semantic / hybrid search over the in-memory indexes."""

import html
import re

import numpy as np

from app.errors import AppError
from app.services.bm25_index import BM25Index, tokenize
from app.services.embedding_index import Embedder, EmbeddingIndex
from app.services.hybrid import blend, min_max

MODES = ("keyword", "semantic", "hybrid")


def make_snippet(text: str, query: str, width: int = 260) -> str:
    """HTML-safe snippet with <mark> around query terms."""
    terms = sorted(set(tokenize(query)), key=len, reverse=True)
    pos = 0
    if terms:
        m = re.search("|".join(re.escape(t) for t in terms), text, re.I)
        pos = m.start() if m else 0
    start = max(0, pos - width // 4)
    piece = text[start : start + width]
    out = html.escape(piece.replace("\n", " "))
    if terms:
        out = re.sub(
            r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b",
            lambda m: f"<mark>{m.group(0)}</mark>",
            out,
            flags=re.I,
        )
    return ("…" if start > 0 else "") + out + ("…" if start + width < len(text) else "")


class SearchService:
    def __init__(self, embedder: Embedder, bm25: BM25Index, emb: EmbeddingIndex, meta: dict[int, dict]) -> None:
        self.embedder, self.bm25, self.emb, self.meta = embedder, bm25, emb, meta

    def search(
        self, q: str, mode: str = "hybrid", top_k: int = 10, alpha: float = 0.5, tags: list[str] | None = None
    ) -> dict:
        if mode not in MODES:
            raise AppError("BAD_MODE", f"mode must be one of {', '.join(MODES)}", 422)
        q = q.strip()
        if not q:
            raise AppError("EMPTY_QUERY", "Query must not be empty", 422)
        ids = self.bm25.chunk_ids
        if not ids:
            return {"query": q, "mode": mode, "results": []}
        kw = self.bm25.scores(q)
        kw_hit = self.bm25.matches(q)
        qv = self.embedder.encode([q])[0]
        sem = self.emb.scores(qv) if mode != "keyword" else np.zeros(len(ids))
        if mode == "keyword":
            final, norm_kw, norm_sem = kw, min_max(kw), np.zeros(len(ids))
        elif mode == "semantic":
            final, norm_kw, norm_sem = sem, np.zeros(len(ids)), min_max(sem)
        else:
            norm_kw, norm_sem = min_max(kw), min_max(sem)
            final = blend(kw, sem, alpha)
        best: dict[int, int] = {}  # file_id -> position of its best chunk
        for pos in np.argsort(-final):
            m = self.meta[ids[pos]]
            if tags and not set(tags) & set(m["tags"]):
                continue
            relevant = (
                kw_hit[pos]
                if mode == "keyword"
                else (sem[pos] > 0) if mode == "semantic" else (kw_hit[pos] or sem[pos] > 0)
            )
            if not relevant:
                continue
            best.setdefault(m["file_id"], int(pos))
            if len(best) >= top_k:
                break
        results = []
        for pos in best.values():
            m = self.meta[ids[pos]]
            results.append(
                {
                    "file": m["rel_path"].rsplit("/", 1)[-1],
                    "rel_path": m["rel_path"],
                    "page": m["page"],
                    "snippet_html": make_snippet(m["text"], q),
                    "scores": {
                        "keyword": round(float(kw[pos]), 4),
                        "semantic": round(float(sem[pos]), 4),
                        "hybrid": round(float(final[pos]) if mode == "hybrid" else 0.0, 4),
                    },
                    "norm": {"keyword": round(float(norm_kw[pos]), 4), "semantic": round(float(norm_sem[pos]), 4)},
                    "tags": m["tags"],
                    "chunk_id": ids[pos],
                }
            )
        return {"query": q, "mode": mode, "results": results}
