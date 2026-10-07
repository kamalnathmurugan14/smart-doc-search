from app.db.session import connect
from tests.conftest import make_pdf


def last_run(c):
    return c.indexer.status()["last_run"]


def test_first_run_then_skip_unchanged(container):
    container.indexer.run_blocking()
    r = last_run(container)
    assert r["files_indexed"] == 5 and r["files_skipped"] == 0
    container.indexer.run_blocking()
    r = last_run(container)
    assert r["files_indexed"] == 0 and r["files_skipped"] == 5


def test_modified_and_removed_and_force(container, docs):
    container.indexer.run_blocking()
    (docs / "garage.txt").write_text("Totally different content about bananas.", encoding="utf-8")
    (docs / "sub" / "recipe.txt").unlink()
    container.indexer.run_blocking()
    r = last_run(container)
    assert r["files_indexed"] == 1 and r["files_removed"] == 1
    with connect(container.settings.db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 4
        assert (
            "bananas"
            in con.execute(
                "SELECT text FROM chunks c JOIN files f ON f.id=c.file_id WHERE rel_path='garage.txt'"
            ).fetchone()[0]
        )
        assert con.execute("SELECT COUNT(*) FROM chunks WHERE file_id NOT IN (SELECT id FROM files)").fetchone()[0] == 0
    container.indexer.run_blocking(force=True)
    assert last_run(container)["files_indexed"] == 4


def test_scanned_pdf_and_corrupt_file_do_not_stop_run(container, docs):
    make_pdf(docs / "blank.pdf", [""])
    (docs / "broken.pdf").write_bytes(b"not a pdf at all")
    container.indexer.run_blocking()
    r = last_run(container)
    assert r["files_indexed"] == 6 and any(e["rel_path"] == "broken.pdf" for e in r["errors"])
    with connect(container.settings.db_path) as con:
        st = {x["rel_path"]: x["status"] for x in con.execute("SELECT rel_path, status FROM files")}
    assert st["blank.pdf"] == "no_text" and st["broken.pdf"] == "error" and st["invoice.pdf"] == "ok"


def test_index_api_and_status(client):
    assert client.get("/index/status").json()["state"] == "idle"
    run_id = client.post("/index", json={"force": False}).json()["run_id"]
    assert run_id >= 1
    import time

    for _ in range(100):
        s = client.get("/index/status").json()
        if s["state"] == "idle" and s["last_run"]:
            break
        time.sleep(0.05)
    assert s["last_run"]["files_indexed"] == 5 and s["progress"]["done"] == 5


def test_hidden_and_unsupported_ignored(container, docs):
    (docs / ".hidden").mkdir()
    (docs / ".hidden" / "x.txt").write_text("secret")
    (docs / "image.png").write_bytes(b"png")
    container.indexer.run_blocking()
    assert last_run(container)["files_seen"] == 5


def test_symlink_pointing_outside_docs_root_is_ignored_not_fatal(container, docs, tmp_path):
    secret = tmp_path / "outside_secret.txt"
    secret.write_text("TOP SECRET outside the docs folder", encoding="utf-8")
    (docs / "sneaky.txt").symlink_to(secret)
    container.indexer.run_blocking()
    r = last_run(container)
    assert r["files_seen"] == 5 and r["files_indexed"] == 5 and not r["errors"]  # the run completed normally
    with connect(container.settings.db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM files WHERE rel_path='sneaky.txt'").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM chunks WHERE text LIKE '%TOP SECRET%'").fetchone()[0] == 0
