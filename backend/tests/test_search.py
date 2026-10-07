import numpy as np

from app.services.hybrid import blend, min_max
from app.services.search_service import make_snippet


def top(client, **params):
    return client.get("/search", params=params).json()["results"]


def test_keyword_expected_doc_first(indexed, client):
    assert top(client, q="invoice number total due", mode="keyword")[0]["rel_path"] == "invoice.pdf"
    assert top(client, q="renewal contract", mode="keyword")[0]["rel_path"] == "contract.docx"


def test_snippet_highlight_and_escape():
    s = make_snippet("Hello <script>alert(1)</script> invoice total", "invoice")
    assert "<mark>invoice</mark>" in s and "<script>" not in s


def test_semantic_finds_paraphrase_keyword_misses(indexed, client):
    assert top(client, q="car fix", mode="keyword") == []
    res = top(client, q="car fix", mode="semantic")
    assert res and res[0]["rel_path"] == "garage.txt"
    assert res[0]["scores"]["semantic"] > 0.3


def test_hybrid_returns_all_scores_and_alpha_matters(indexed, client):
    r = top(client, q="invoice total", mode="hybrid", alpha=0.0)[0]
    assert r["rel_path"] == "invoice.pdf" and set(r["scores"]) == {"keyword", "semantic", "hybrid"}
    assert r["scores"]["keyword"] > 0 and 0 <= r["scores"]["hybrid"] <= 1
    assert top(client, q="car fix", mode="hybrid", alpha=1.0)[0]["rel_path"] == "garage.txt"


def test_minmax_pitfalls():
    assert (min_max(np.array([2.0, 2.0, 2.0])) == 0).all()  # constant list carries no signal
    assert min_max(np.array([1.0, 3.0, 5.0])).tolist() == [0.0, 0.5, 1.0]
    assert blend(np.array([0.0, 4.0]), np.array([1.0, 0.0]), 0.5).tolist() == [0.5, 0.5]


def test_search_errors_and_empty_index(client):
    assert top(client, q="anything") == []  # empty index -> no results, not an error
    assert client.get("/search", params={"q": "x", "mode": "bogus"}).status_code == 422
    assert client.get("/search", params={"q": "  "}).json()["error"]["code"] == "EMPTY_QUERY"


def test_one_result_per_file_and_top_k(indexed, client):
    res = top(client, q="the", mode="hybrid", top_k=2)
    assert len(res) <= 2 and len({r["rel_path"] for r in res}) == len(res)


def test_term_in_most_docs_still_matches(container, client, docs):
    """Regression: textbook BM25 idf is negative for terms in >50% of docs -> zero hits."""
    for f in docs.iterdir():
        if f.is_file():
            f.unlink()
    for name in ("a.txt", "b.txt", "c.txt"):
        (docs / name).write_text("renewal contract text", encoding="utf-8")
    container.indexer.run_blocking()
    res = top(client, q="renewal", mode="keyword")
    assert len(res) == 3 and all(r["scores"]["keyword"] > 0 for r in res)
