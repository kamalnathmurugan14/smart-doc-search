"""Incremental indexer: scan DOCS_ROOT -> extract -> chunk -> embed -> SQLite."""

import hashlib
import json
import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from app.config import Settings
from app.core.chunker import chunk_pages
from app.core.extractors import extract, page_count
from app.core.paths import rel_posix
from app.db.session import connect
from app.services.embedding_index import Embedder
from app.services.tagger import Tagger

log = logging.getLogger(__name__)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Indexer:
    def __init__(self, settings: Settings, embedder: Embedder, tagger: Tagger, on_done: Callable[[], None]) -> None:
        self.s, self.embedder, self.tagger, self.on_done = settings, embedder, tagger, on_done
        self._lock = threading.Lock()
        self.state = "idle"
        self.done = 0
        self.total = 0
        self.thread: threading.Thread | None = None

    # ---- public -----------------------------------------------------
    def start(self, force: bool = False) -> int | None:
        """Start a background run. Returns run_id, or None when one is already running."""
        with self._lock:
            if self.state == "running":
                return None
            self.state, self.done, self.total = "running", 0, 0
        with connect(self.s.db_path) as con:
            run_id = con.execute("INSERT INTO index_runs(started_at) VALUES(?)", (_now(),)).lastrowid
        self.thread = threading.Thread(target=self._run, args=(run_id, force), daemon=True)
        self.thread.start()
        return run_id

    def run_blocking(self, force: bool = False) -> int:
        run_id = self.start(force)
        assert run_id is not None
        assert self.thread is not None
        self.thread.join()
        return run_id

    def status(self) -> dict:
        with connect(self.s.db_path) as con:
            row = con.execute(
                "SELECT * FROM index_runs WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1"
            ).fetchone()
        last = None
        if row:
            last = {
                **{k: row[k] for k in row.keys() if k != "errors_json"},
                "errors": json.loads(row["errors_json"] or "[]"),
            }
        return {"state": self.state, "progress": {"done": self.done, "total": self.total}, "last_run": last}

    # ---- internals --------------------------------------------------
    def _scan(self) -> list[Path]:
        root = self.s.docs_root.resolve()
        found = []
        for p in sorted(root.rglob("*")):
            rel_parts = p.relative_to(root).parts
            if any(part.startswith(".") for part in rel_parts) or not p.is_file():
                continue
            if p.suffix.lower().lstrip(".") in self.s.extensions:
                found.append(p)
        return found

    def _run(self, run_id: int, force: bool) -> None:
        errors: list[dict] = []
        indexed = skipped = removed = 0
        try:
            root = self.s.docs_root.resolve()
            files = self._scan() if root.exists() else []
            self.total = len(files)
            with connect(self.s.db_path) as con:
                # a different embedding model means old vectors are unusable
                prev = con.execute("SELECT value FROM meta WHERE key='embedder'").fetchone()
                if prev is None or prev["value"] != f"{self.embedder.name}:{self.embedder.dim}":
                    force = True
                    con.execute(
                        "INSERT OR REPLACE INTO meta VALUES('embedder', ?)",
                        (f"{self.embedder.name}:{self.embedder.dim}",),
                    )
                known = {r["rel_path"]: r for r in con.execute("SELECT * FROM files")}
                seen = set()
                for path in files:
                    rel = rel_posix(root, path)
                    seen.add(rel)
                    try:
                        digest = sha256_of(path)
                        old = known.get(rel)
                        if old and old["sha256"] == digest and old["status"] != "error" and not force:
                            skipped += 1
                        else:
                            self._index_file(con, path, rel, digest, old["id"] if old else None)
                            indexed += 1
                    except Exception as exc:  # noqa: BLE001 - one bad file must not stop the run
                        log.warning("index_error file=%s err=%s", rel, type(exc).__name__)
                        errors.append({"rel_path": rel, "error": f"{type(exc).__name__}: {exc}"[:300]})
                        self._mark_error(con, path, rel, str(exc)[:300], known.get(rel))
                    self.done += 1
                    con.commit()
                for rel, row in known.items():  # files deleted from disk
                    if rel not in seen:
                        con.execute("DELETE FROM files WHERE id=?", (row["id"],))
                        removed += 1
                con.execute(
                    "UPDATE index_runs SET finished_at=?, files_seen=?, files_indexed=?, files_skipped=?, "
                    "files_removed=?, errors_json=? WHERE id=?",
                    (_now(), len(files), indexed, skipped, removed, json.dumps(errors), run_id),
                )
            self.on_done()
        except Exception as exc:  # noqa: BLE001
            log.exception("index_run_failed")
            with connect(self.s.db_path) as con:
                con.execute(
                    "UPDATE index_runs SET finished_at=?, errors_json=? WHERE id=?",
                    (_now(), json.dumps([{"rel_path": "*", "error": str(exc)[:300]}]), run_id),
                )
        finally:
            self.state = "idle"

    def _mark_error(self, con, path: Path, rel: str, msg: str, old) -> None:
        st = path.stat()
        if old:
            con.execute("DELETE FROM chunks WHERE file_id=?", (old["id"],))
            con.execute(
                "UPDATE files SET status='error', message=?, sha256=?, size_bytes=?, mtime=? WHERE id=?",
                (msg, "", st.st_size, st.st_mtime, old["id"]),
            )
        else:
            con.execute(
                "INSERT INTO files(rel_path,sha256,size_bytes,mtime,ext,status,message) VALUES(?,?,?,?,?,?,?)",
                (rel, "", st.st_size, st.st_mtime, path.suffix.lower().lstrip("."), "error", msg),
            )

    def _index_file(self, con, path: Path, rel: str, digest: str, file_id: int | None) -> None:
        st = path.stat()
        ex = extract(path)
        chunks = chunk_pages(ex.pages, self.s.chunk_size_chars, self.s.chunk_overlap_chars)
        tags = self.tagger.tag(ex.text) if chunks else []
        status = "ok" if chunks else "no_text"
        vals = (digest, st.st_size, st.st_mtime, json.dumps(tags), page_count(path), _now(), status, ex.warning)
        if file_id is None:
            file_id = con.execute(
                "INSERT INTO files(rel_path,sha256,size_bytes,mtime,ext,tags_json,page_count,indexed_at,status,message) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    rel,
                    digest,
                    st.st_size,
                    st.st_mtime,
                    path.suffix.lower().lstrip("."),
                    json.dumps(tags),
                    vals[4],
                    vals[5],
                    status,
                    ex.warning,
                ),
            ).lastrowid
        else:
            con.execute("DELETE FROM chunks WHERE file_id=?", (file_id,))
            con.execute(
                "UPDATE files SET sha256=?, size_bytes=?, mtime=?, tags_json=?, page_count=?, indexed_at=?, "
                "status=?, message=? WHERE id=?",
                (*vals, file_id),
            )
        if chunks:
            vecs = self.embedder.encode([c.text for c in chunks]).astype(np.float32)
            con.executemany(
                "INSERT INTO chunks(file_id,chunk_index,page,text,char_start,char_end,embedding) VALUES(?,?,?,?,?,?,?)",
                [
                    (file_id, c.index, c.page, c.text, c.char_start, c.char_end, v.tobytes())
                    for c, v in zip(chunks, vecs)
                ],
            )
