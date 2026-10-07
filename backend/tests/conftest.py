import zlib
from pathlib import Path

import numpy as np
import pytest
from docx import Document
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.config import Settings
from app.deps import Container
from app.main import create_app

CONCEPTS = [
    {"car", "automobile", "vehicle", "auto"},
    {"fix", "repair", "repaired", "mend", "fixed"},
    {"cheap", "inexpensive", "affordable"},
]


class ConceptEmbedder:
    """Tiny deterministic 'semantic' embedder: synonyms share a dimension (stands in for MiniLM in tests)."""

    name, dim = "concept-test", 64

    def encode(self, texts):
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for r, t in enumerate(texts):
            for w in "".join(c if c.isalnum() else " " for c in t.lower()).split():
                for i, group in enumerate(CONCEPTS):
                    if w in group:
                        out[r, i] += 1
                        break
                else:
                    out[r, 8 + zlib.crc32(w.encode()) % (self.dim - 8)] += 1
        n = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(n == 0, 1, n)


def make_pdf(path: Path, pages: list[str]) -> None:
    c = canvas.Canvas(str(path))
    for text in pages:
        y = 800
        for line in text.split("\n"):
            c.drawString(50, y, line)
            y -= 16
        c.showPage()
    c.save()


def make_docx(path: Path, paragraphs: list[str]) -> None:
    d = Document()
    for p in paragraphs:
        d.add_paragraph(p)
    d.save(str(path))


INVOICE = (
    "INVOICE\nInvoice number: INV-1042\nBill to: Acme Corp\nSubtotal: $900.00\nGST: $100.00\n"
    "Total due: $1000.00\nDue date: 2026-01-31"
)
CONTRACT = (
    "SERVICE AGREEMENT\nThis agreement is made between the parties. The renewal of this contract happens "
    "yearly. Governing law applies. The party agrees to keep all terms confidential."
)


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    root = tmp_path / "docs"
    (root / "sub").mkdir(parents=True)
    make_pdf(root / "invoice.pdf", [INVOICE])
    make_docx(root / "contract.docx", CONTRACT.split(". "))
    (root / "garage.txt").write_text("The automobile was repaired at the garage last week.", encoding="utf-8")
    (root / "notes.md").write_text(
        "# Notes\n\nQuarterly report: executive summary, findings, conclusion and recommendations.", encoding="utf-8"
    )
    (root / "sub" / "recipe.txt").write_text("Mix flour and eggs. Bake for thirty minutes.", encoding="utf-8")
    return root


@pytest.fixture
def settings(tmp_path: Path, docs: Path) -> Settings:
    rules = Path(__file__).resolve().parent.parent / "rules" / "tags.yaml"
    return Settings(
        docs_root=docs,
        data_dir=tmp_path / "data",
        embedding_model="hashing",
        max_upload_mb=1,
        tag_rules_path=rules,
        _env_file=None,
    )


@pytest.fixture
def container(settings: Settings) -> Container:
    return Container(settings, embedder=ConceptEmbedder())


@pytest.fixture
def indexed(container: Container) -> Container:
    container.indexer.run_blocking()
    return container


@pytest.fixture
def client(container: Container, settings: Settings):
    with TestClient(create_app(settings, container)) as c:
        yield c
