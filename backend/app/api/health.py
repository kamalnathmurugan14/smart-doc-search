from fastapi import APIRouter, Request

from app.config import APP_VERSION

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    c = request.app.state.container
    return {"status": "ok", "version": APP_VERSION, "embedder": c.embedder.name}
