from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/index")


class IndexBody(BaseModel):
    force: bool = False


@router.post("", status_code=202)
def start_index(request: Request, body: IndexBody | None = None):
    run_id = request.app.state.container.indexer.start(force=bool(body and body.force))
    if run_id is None:
        return JSONResponse(
            {"error": {"code": "INDEX_RUNNING", "message": "An index run is already in progress"}}, status_code=409
        )
    return {"run_id": run_id}


@router.get("/status")
def status(request: Request) -> dict:
    return request.app.state.container.indexer.status()
