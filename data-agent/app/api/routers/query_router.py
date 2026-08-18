from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from starlette.responses import JSONResponse, StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.conf.app_config import app_config
from app.services.health_service import check_health
from app.services.query_service import QueryService

query_router = APIRouter()


@query_router.get("/api/health")
async def health():
    """Return dependency readiness without exposing connection details."""
    result = await check_health()
    status_code = 200 if result["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=result)


@query_router.post("/api/query")
async def query(
    query: QuerySchema,
    query_service: QueryService = Depends(get_query_service),  # noqa: B008
):
    """问数入口，返回 SSE。"""
    normalized_query = query.query.strip()
    if not normalized_query:
        raise HTTPException(status_code=422, detail="问题不能为空")
    if len(normalized_query) > app_config.api.max_query_chars:
        raise HTTPException(
            status_code=422,
            detail=f"问题长度不能超过 {app_config.api.max_query_chars} 个字符",
        )
    return StreamingResponse(
        query_service.query(normalized_query),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
