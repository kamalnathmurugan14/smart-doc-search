# Architecture

## Components
| Layer | Module | Responsibility |
|---|---|---|
| API | `app/api/*` | Thin FastAPI routers; all errors become `{error:{code,message}}` |
| Safety | `core/paths.py` | `safe_resolve`, `sanitize_filename` – the only way a user path touches disk |
| Ingest | `core/extractors.py`, `core/chunker.py` | file → pages → overlapping paragraph-aware chunks with page + offsets |
| Index | `services/indexer.py` | scan, SHA-256 compare, extract, chunk, embed, store; background thread with progress |
| Search | `bm25_index.py`, `embedding_index.py`, `hybrid.py`, `search_service.py` | in-memory BM25 + normalized matrix; fusion |
| Insight | `explain.py`, `tagger.py`, `dedupe.py` | why-ranked, rule tags, duplicates |
| Wiring | `deps.py` | `Container` owns settings, embedder, indexes; `reload()` rebuilds memory from SQLite |

## Data flow
1. **Index**: `POST /index` → thread → for each file: hash → (unchanged? skip) → extract → chunk → embed → write `files` + `chunks` (embedding as float32 BLOB) → after the run `Container.reload()` rebuilds BM25 and the matrix.
2. **Search**: query → BM25 scores over all chunks + `matrix @ query_vec` → (min-max) blend → keep best chunk per file → snippet with `<mark>`.
3. **Explain**: recompute the same scores for one chunk and break them down; the numbers are asserted equal to `/search` in tests.

## Decisions & trade-offs
- **sqlite3, no ORM** – the schema is 4 small tables; visible SQL is better for learning.
- **Everything searchable lives in RAM** – simple and fast (3 ms at 500 docs); a corpus of millions of chunks would need an ANN index (see project 4 / ChromaDB).
- **Lucene-style IDF** – `rank_bm25`'s default IDF is negative for terms in >50 % of documents, which silently returned *no results* on small/duplicate-heavy corpora (found by the E2E test, now a regression test).
- **Embedder fallback** – if `sentence-transformers` is missing the app still works (lexical hashing embedder) and reports it in `/health`. Changing embedder triggers a forced re-index (stored in `meta`).
- **Hybrid normalization** – min-max per query. Pitfall: a list where all scores are equal normalizes to zeros (no signal) instead of dividing by zero.
- **One result per file** – the best chunk represents the file; `chunk_id` lets Explain drill down.
- **Near duplicates** – cosine of mean file embeddings is a cheap filter (O(n²) matrix product), then shingle-Jaccard confirms; groups merged with union-find.
