import json

from fastapi import APIRouter, Request

from app.db.session import connect

router = APIRouter()


@router.get("/files")
def list_files(request: Request, tag: str = "", ext: str = "") -> dict:
    c = request.app.state.container
    with connect(c.settings.db_path) as con:
        rows = con.execute("SELECT * FROM files ORDER BY rel_path").fetchall()
    out = []
    for r in rows:
        tags = json.loads(r["tags_json"])
        if (tag and tag not in tags) or (ext and r["ext"] != ext.lower().lstrip(".")):
            continue
        out.append(
            {
                "rel_path": r["rel_path"],
                "ext": r["ext"],
                "size_bytes": r["size_bytes"],
                "tags": tags,
                "page_count": r["page_count"],
                "status": r["status"],
                "message": r["message"],
                "indexed_at": r["indexed_at"],
            }
        )
    return {"files": out, "all_tags": sorted({t for f in out for t in f["tags"]})}


@router.get("/tags")
def all_tags(request: Request) -> dict:
    c = request.app.state.container
    return {"tags": sorted(c.tagger.rules.keys())}


@router.post("/files/retag")
def retag(request: Request) -> dict:
    return {"retagged": request.app.state.container.retag()}


@router.get("/duplicates")
def duplicates(request: Request) -> dict:
    return request.app.state.container.duplicates()
