"""Performance check: generate N small docs, index them, time searches.  python scripts/perf_check.py [N]"""

import random
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import Settings  # noqa: E402
from app.deps import Container  # noqa: E402

WORDS = "invoice contract report budget client project meeting schedule payment renewal security quarterly growth team".split()


def main(n: int) -> None:
    rnd = random.Random(1)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "docs"
        root.mkdir()
        for i in range(n):
            body = "\n\n".join(" ".join(rnd.choices(WORDS, k=60)) for _ in range(6))
            (root / f"doc_{i:04d}.txt").write_text(f"Document {i}\n\n{body}", encoding="utf-8")
        s = Settings(docs_root=root, data_dir=Path(tmp) / "data", embedding_model="hashing", _env_file=None)
        c = Container(s)
        t = time.perf_counter()
        c.indexer.run_blocking()
        print(f"index {n} docs: {time.perf_counter() - t:.1f}s")
        t = time.perf_counter()
        c.indexer.run_blocking()
        print(f"re-index (no changes): {time.perf_counter() - t:.2f}s")
        for mode in ("keyword", "semantic", "hybrid"):
            t = time.perf_counter()
            for _ in range(20):
                c.search.search("quarterly security budget", mode)
            print(f"{mode} search: {(time.perf_counter() - t) / 20 * 1000:.1f} ms")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 500)
