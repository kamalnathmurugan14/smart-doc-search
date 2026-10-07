"""Explain WHY a chunk ranked where it did."""

import re

import numpy as np

from app.errors import AppError
from app.services.hybrid import min_max
from app.services.search_service import SearchService


def explain(svc: SearchService, q: str, chunk_id: int, alpha: float = 0.5) -> dict:
    if chunk_id not in svc.meta:
        raise AppError("CHUNK_NOT_FOUND", "Unknown chunk_id", 404)
    ids = svc.bm25.chunk_ids
    pos = ids.index(chunk_id)
    kw_all = svc.bm25.scores(q)
    qv = svc.embedder.encode([q])[0]
    sem_all = svc.emb.scores(qv)
    terms = svc.bm25.explain_terms(q, chunk_id)
    text = svc.meta[chunk_id]["text"]
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 15]
    top = []
    if sents:
        sims = svc.embedder.encode(sents) @ qv
        top = [{"sentence": sents[i], "cosine": round(float(sims[i]), 4)} for i in np.argsort(-sims)[:3]]
    nk, ns = float(min_max(kw_all)[pos]), float(min_max(sem_all)[pos])
    return {
        "keyword": {
            "terms": terms,
            "score": round(float(kw_all[pos]), 4),
            "sum_of_terms": round(sum(t["contribution"] for t in terms), 4),
        },
        "semantic": {
            "cosine": round(float(sem_all[pos]), 4),
            "embedder": svc.embedder.name,
            "top_matching_sentences": top,
        },
        "hybrid": {
            "formula": "final = alpha*semantic_norm + (1-alpha)*keyword_norm",
            "alpha": alpha,
            "normalized_scores": {"keyword": round(nk, 4), "semantic": round(ns, 4)},
            "final": round(alpha * ns + (1 - alpha) * nk, 4),
        },
    }
