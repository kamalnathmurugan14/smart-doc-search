from app.core.chunker import chunk_pages
from app.core.extractors import extract
from tests.conftest import make_pdf


def test_txt_md_docx_pdf(docs):
    assert "automobile" in extract(docs / "garage.txt").text
    assert "Quarterly" in extract(docs / "notes.md").text
    assert "agreement" in extract(docs / "contract.docx").text.lower()
    ex = extract(docs / "invoice.pdf")
    assert ex.pages[0][0] == 1 and "INV-1042" in ex.text


def test_pdf_pages_and_empty_warning(tmp_path):
    p = tmp_path / "two.pdf"
    make_pdf(p, ["first page text", "second page text"])
    assert [n for n, _ in extract(p).pages] == [1, 2]
    blank = tmp_path / "blank.pdf"
    make_pdf(blank, [""])
    ex = extract(blank)
    assert ex.pages == [] and "no extractable text" in ex.warning


def test_encoding_fallback(tmp_path):
    p = tmp_path / "cp.txt"
    p.write_bytes("café résumé".encode("cp1252"))
    assert "café" in extract(p).text


def test_chunker_respects_size_overlap_and_offsets():
    paras = [f"Paragraph {i}. " + "word " * 30 for i in range(12)]
    text = "\n\n".join(paras)
    chunks = chunk_pages([(3, text)], size=500, overlap=100)
    assert len(chunks) > 2
    for c in chunks:
        assert c.page == 3 and len(c.text) <= 500
        assert text[c.char_start : c.char_end] == c.text
    assert any(chunks[i + 1].char_start < chunks[i].char_end for i in range(len(chunks) - 1))  # overlap
    assert all(chunks[i + 1].char_start > chunks[i].char_start for i in range(len(chunks) - 1))


def test_chunker_splits_huge_paragraph_and_handles_empty():
    chunks = chunk_pages([(1, "x" * 50 + " " + "y" * 3000)], size=500, overlap=50)
    assert all(len(c.text) <= 500 for c in chunks) and len(chunks) >= 6
    assert chunk_pages([]) == []
