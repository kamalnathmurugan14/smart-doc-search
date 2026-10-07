"""Throw-away backend for Playwright: temp docs folder + hashing embedder, served on :8000."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import uvicorn  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

tmp = Path(tempfile.mkdtemp())
docs = tmp / "docs"
docs.mkdir()
text = "SERVICE AGREEMENT\n\nThis agreement renewal clause: the contract renews yearly. The parties agree. Governing law applies."
(docs / "contract.txt").write_text(text, encoding="utf-8")
(docs / "contract_copy.txt").write_text(text, encoding="utf-8")
(docs / "notes.md").write_text("# Notes\n\nLunch menu and holiday schedule.", encoding="utf-8")
rules = Path(__file__).resolve().parent.parent / "rules" / "tags.yaml"
settings = Settings(
    docs_root=docs, data_dir=tmp / "data", embedding_model="hashing", tag_rules_path=rules, _env_file=None
)
uvicorn.run(create_app(settings), host="127.0.0.1", port=8000, log_level="warning")
