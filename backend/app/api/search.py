from fastapi import APIRouter, Query, Request

from app.services.explain import explain as explain_chunk

router = APIRouter()


@router.get("/search")
def search(
    request: Request,
    q: str,
    mode: str = "hybrid",
    top_k: int = Query(10, ge=1, le=50),
    alpha: float | None = Query(None, ge=0, le=1),
    tags: str = "",
) -> dict:
    c = request.app.state.container
    a = c.settings.hybrid_alpha if alpha is None else alpha
    tag_list = [t for t in tags.split(",") if t]
    return c.search.search(q, mode, top_k, a, tag_list)


@router.get("/explain")
def explain(request: Request, q: str, chunk_id: int, alpha: float | None = Query(None, ge=0, le=1)) -> dict:
    c = request.app.state.container
    return explain_chunk(c.search, q, chunk_id, c.settings.hybrid_alpha if alpha is None else alpha)
