# Learning notes

## M0 – Scaffold, config, health
**Built:** FastAPI app factory, one `Settings` class, uniform error shape, `/health`, CI. **Concept:** configuration lives in the environment (12-factor); one typed object is easier to test than scattered `os.getenv`. **Mistake:** committing `.env`. **Try:** add a new setting and an `.env.example` line.

## M1 – Safe filesystem + explorer + upload
**Built:** `safe_resolve`, `/fs/tree`, `/fs/upload`, `FileExplorer`. **Concept:** `Path.resolve()` follows symlinks, so comparing the resolved path to the resolved root blocks `..` *and* symlink escapes. **Mistake:** checking `startswith` on strings (`/data/docs-evil` passes `/data/docs`). **Try:** create a symlink to `/etc` inside DOCS_ROOT and watch the test fail if you remove `.resolve()`.

## M2 – Extractors + chunker
**Built:** pypdf/python-docx/text extractors; paragraph-aware chunker with overlap and offsets. **Concept:** retrieval works on *chunks*; too big = diluted meaning, too small = lost context; overlap keeps sentences that straddle a boundary findable. **Mistake:** a regex that required exactly `\n\n` – trailing spaces before it produced *zero* chunks. **Try:** change `CHUNK_SIZE_CHARS` to 300 and compare results.

## M3 – Incremental indexer
**Built:** SHA-256 diffing; add / modify / delete cases; background job + progress. **Concept:** hash content, not mtime (copying a file changes mtime but not content). **Try:** touch a file and re-index – it should be skipped.

## M4 – BM25 keyword search
**Concept:** BM25 = Σ over query terms of `idf × tf·(k1+1)/(tf + k1·(1−b+b·len/avglen))`. Rare terms (high idf) matter more; repeated terms saturate; long documents are penalised. **Mistake:** negative IDF (see Architecture). **Try:** read the Explain table and recompute one row by hand.

## M5 – Semantic + hybrid
**Concept:** an embedding maps text to a vector so similar *meaning* is nearby; with normalized vectors cosine similarity is a dot product. Keyword search misses "car fix" vs "automobile repaired"; semantic finds it. Hybrid = `α·semantic + (1−α)·keyword` after min-max scaling – raw BM25 (0‥20) and cosine (0‥1) are on different scales, so you can't add them directly. **Try:** slide α from 0 to 1 and watch rankings change.

## M6 – Auto-tagger
**Concept:** simple rules are transparent and good enough for obvious categories (project 2 learns them from data instead). **Try:** add a `Receipt` tag in `rules/tags.yaml`, click *Apply tag rules now*.

## M7 – Duplicates
**Concept:** exact = same hash; near = similar embeddings **and** overlapping 5-word shingles (Jaccard) – two cheap signals beat one. **Try:** lower `DUP_NEAR_THRESHOLD` to 0.8 and see false positives appear.

## M8 – Explain
**Concept:** debuggable search. The sum of per-term contributions equals the BM25 score; the hybrid line shows the exact arithmetic.

## M9 – Polish
Empty/loading/error states everywhere, dark/light theme via CSS variables, performance check on 500 docs.

## M10 – E2E
One Playwright test drives index → search → explain → duplicates against a throw-away backend.
