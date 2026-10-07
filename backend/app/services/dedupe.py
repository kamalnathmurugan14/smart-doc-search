"""Exact (same sha256) and near duplicates (mean-embedding cosine, confirmed by shingle Jaccard)."""

import re

import numpy as np

_W = re.compile(r"\w+")


def shingles(text: str, k: int = 5) -> set[tuple[str, ...]]:
    w = _W.findall(text.lower())
    return {tuple(w[i : i + k]) for i in range(max(1, len(w) - k + 1))} if w else set()


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def find_duplicates(
    files: list[dict],
    file_vecs: dict[int, np.ndarray],
    file_text: dict[int, str],
    cos_threshold: float,
    jaccard_min: float,
) -> dict:
    by_hash: dict[str, list[dict]] = {}
    for f in files:
        if f["sha256"]:
            by_hash.setdefault(f["sha256"], []).append(f)
    exact = [[x["rel_path"] for x in g] for g in by_hash.values() if len(g) > 1]
    exact_of = {x["rel_path"]: i for i, g in enumerate(exact) for x in [{"rel_path": p} for p in g]}

    ids = [f["id"] for f in files if f["id"] in file_vecs]
    byid = {f["id"]: f for f in files}
    parent = {i: i for i in ids}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    sims: dict[tuple[int, int], float] = {}
    if len(ids) > 1:
        mat = np.vstack([file_vecs[i] for i in ids])
        cos = mat @ mat.T
        sh = {i: shingles(file_text[i]) for i in ids}
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                ia, ib = ids[a], ids[b]
                pa, pb = byid[ia]["rel_path"], byid[ib]["rel_path"]
                if byid[ia]["sha256"] == byid[ib]["sha256"] or (
                    pa in exact_of and exact_of.get(pa) == exact_of.get(pb)
                ):
                    continue  # already reported as exact
                if cos[a, b] >= cos_threshold and jaccard(sh[ia], sh[ib]) >= jaccard_min:
                    sims[(ia, ib)] = float(cos[a, b])
                    parent[find(ia)] = find(ib)
    groups: dict[int, list[int]] = {}
    for i in ids:
        groups.setdefault(find(i), []).append(i)
    near = []
    for members in groups.values():
        if len(members) > 1:
            vals = [v for (x, y), v in sims.items() if x in members and y in members]
            near.append({"files": [byid[m]["rel_path"] for m in members], "similarity": round(min(vals), 4)})
    return {"exact": exact, "near": near}
