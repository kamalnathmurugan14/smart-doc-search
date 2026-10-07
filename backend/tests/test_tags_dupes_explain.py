from app.services.tagger import Tagger


def test_invoice_tagged(indexed, client):
    files = {f["rel_path"]: f for f in client.get("/files").json()["files"]}
    assert "Invoice" in files["invoice.pdf"]["tags"]
    assert "Contract" in files["contract.docx"]["tags"]
    assert files["garage.txt"]["tags"] == []
    assert [f["rel_path"] for f in client.get("/files", params={"tag": "Invoice"}).json()["files"]] == ["invoice.pdf"]
    assert client.get("/files", params={"ext": "md"}).json()["files"][0]["rel_path"] == "notes.md"


def test_search_tag_filter(indexed, client):
    res = client.get("/search", params={"q": "total agreement", "mode": "keyword", "tags": "Invoice"}).json()["results"]
    assert res and all("Invoice" in r["tags"] for r in res)


def test_tagger_rules_editable(tmp_path):
    p = tmp_path / "t.yaml"
    p.write_text("tags:\n  Pets:\n    keywords: [cat, dog]\n    weight: 1\n    threshold: 2\n")
    t = Tagger(p)
    assert t.tag("a cat and a dog") == ["Pets"] and t.tag("just a cat") == []


def test_retag_after_rule_change(indexed, client, tmp_path):
    rules = indexed.settings.tag_rules_path
    new = tmp_path / "new.yaml"
    new.write_text("tags:\n  Garage:\n    keywords: [garage]\n    weight: 1\n    threshold: 1\n")
    indexed.settings.tag_rules_path = new
    assert client.post("/files/retag").json()["retagged"] == 5
    tagged = [f["rel_path"] for f in client.get("/files", params={"tag": "Garage"}).json()["files"]]
    assert tagged == ["garage.txt"]
    indexed.settings.tag_rules_path = rules


def test_duplicates_exact_and_near(container, client, docs):
    base = "The quarterly sales report shows strong growth across all regions this year. " * 12
    (docs / "a.txt").write_text(base, encoding="utf-8")
    (docs / "copy.txt").write_bytes((docs / "a.txt").read_bytes())  # exact copy
    (docs / "edited.txt").write_text(base + " One extra closing sentence was added by an editor.", encoding="utf-8")
    container.indexer.run_blocking()
    d = client.get("/duplicates").json()
    assert sorted(d["exact"][0]) == ["a.txt", "copy.txt"]
    near = [set(n["files"]) for n in d["near"]]
    assert any("edited.txt" in n and ("a.txt" in n or "copy.txt" in n) for n in near)
    assert not any("invoice.pdf" in n for n in near)


def test_explain_numbers_match(indexed, client):
    q = "invoice total due"
    hit = client.get("/search", params={"q": q, "mode": "hybrid"}).json()["results"][0]
    ex = client.get("/explain", params={"q": q, "chunk_id": hit["chunk_id"]}).json()
    assert abs(ex["keyword"]["sum_of_terms"] - hit["scores"]["keyword"]) < 1e-3
    assert abs(ex["semantic"]["cosine"] - hit["scores"]["semantic"]) < 1e-3
    assert abs(ex["hybrid"]["final"] - hit["scores"]["hybrid"]) < 1e-3
    assert ex["keyword"]["terms"][0]["term"] == "invoice" and ex["semantic"]["top_matching_sentences"]
    assert client.get("/explain", params={"q": q, "chunk_id": 99999}).status_code == 404
