"""Wires services together. One Container per app; rebuilt indexes live in memory."""

import json
import threading

import numpy as np

from app.config import Settings
from app.db.session import connect, init_db
from app.services.bm25_index import BM25Index
from app.services.dedupe import find_duplicates
from app.services.embedding_index import Embedder, EmbeddingIndex, build_embedder
from app.services.indexer import Indexer
from app.services.search_service import SearchService
from app.services.tagger import Tagger


class Container:
    def __init__(self, settings: Settings, embedder: Embedder | None = None) -> None:
        self.settings = settings
        settings.docs_root.mkdir(parents=True, exist_ok=True)
        init_db(settings.db_path)
        self.embedder = embedder or build_embedder(settings.embedding_model)
        self.tagger = Tagger(settings.tag_rules_path)
        self.indexer = Indexer(settings, self.embedder, self.tagger, on_done=self.reload)
        self._lock = threading.Lock()
        self.search = SearchService(self.embedder, BM25Index(), EmbeddingIndex(), {})
        self.reload()

    def reload(self) -> None:
        """Rebuild BM25 + embedding matrix from the chunks table (cheap; runs at startup and after indexing)."""
        ids, texts, vecs, meta = [], [], [], {}
        with connect(self.settings.db_path) as con:
            rows = con.execute(
                "SELECT c.id, c.file_id, c.page, c.text, c.embedding, f.rel_path, f.tags_json "
                "FROM chunks c JOIN files f ON f.id=c.file_id ORDER BY c.id"
            ).fetchall()
        for r in rows:
            ids.append(r["id"])
            texts.append(r["text"])
            vecs.append(np.frombuffer(r["embedding"], dtype=np.float32))
            meta[r["id"]] = {
                "file_id": r["file_id"],
                "rel_path": r["rel_path"],
                "page": r["page"],
                "text": r["text"],
                "tags": json.loads(r["tags_json"]),
            }
        bm, emb = BM25Index(), EmbeddingIndex()
        bm.build(ids, texts)
        dims = {v.shape[0] for v in vecs}
        emb.build(ids, vecs if len(dims) == 1 else [])
        with self._lock:
            self.search = SearchService(self.embedder, bm, emb, meta)

    def duplicates(self) -> dict:
        with connect(self.settings.db_path) as con:
            files = [dict(r) for r in con.execute("SELECT id, rel_path, sha256 FROM files WHERE status!='error'")]
        svc = self.search
        per_file: dict[int, list[int]] = {}
        for pos, cid in enumerate(svc.bm25.chunk_ids):
            per_file.setdefault(svc.meta[cid]["file_id"], []).append(pos)
        vecs, texts = {}, {}
        for fid, positions in per_file.items():
            if svc.emb.matrix.size:
                m = svc.emb.matrix[positions].mean(axis=0)
                n = np.linalg.norm(m)
                vecs[fid] = m / n if n else m
            texts[fid] = " ".join(svc.meta[svc.bm25.chunk_ids[p]]["text"] for p in positions)
        return find_duplicates(files, vecs, texts, self.settings.dup_near_threshold, self.settings.dup_jaccard_min)

    def retag(self) -> int:
        self.tagger = Tagger(self.settings.tag_rules_path)
        self.indexer.tagger = self.tagger
        n = 0
        with connect(self.settings.db_path) as con:
            for f in con.execute("SELECT id FROM files WHERE status='ok'").fetchall():
                text = "\n\n".join(
                    r["text"]
                    for r in con.execute("SELECT text FROM chunks WHERE file_id=? ORDER BY chunk_index", (f["id"],))
                )
                con.execute("UPDATE files SET tags_json=? WHERE id=?", (json.dumps(self.tagger.tag(text)), f["id"]))
                n += 1
        self.reload()
        return n
