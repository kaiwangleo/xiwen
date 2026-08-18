import asyncio
from contextlib import aclosing

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.conf.app_config import app_config
from app.services.health_service import check_health
from app.services.query_service import QueryService

query_router = APIRouter()


class QueryStreamingResponse(StreamingResponse):
    """Stream SSE while leaving disconnect ownership to the body iterator."""

    async def __call__(self, _scope, _receive, send) -> None:
        try:
            await self.stream_response(send)
        except OSError:
            pass
        finally:
            close = getattr(self.body_iterator, "aclose", None)
            if close is not None:
                await close()

        if self.background is not None:
            await self.background()


async def stream_until_disconnect(request: Request, response):
    async def wait_for_disconnect() -> None:
        while True:
            message = await request.receive()
            if message["type"] == "http.disconnect":
                return

    disconnect_task = asyncio.create_task(wait_for_disconnect())
    next_chunk: asyncio.Task | None = None
    try:
        async with aclosing(response):
            while True:
                next_chunk = asyncio.create_task(anext(response))
                done, _pending = await asyncio.wait(
                    {disconnect_task, next_chunk},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if disconnect_task in done:
                    next_chunk.cancel()
                    await asyncio.gather(next_chunk, return_exceptions=True)
                    return
                try:
                    yield next_chunk.result()
                except StopAsyncIteration:
                    return
                finally:
                    next_chunk = None
    finally:
        disconnect_task.cancel()
        pending = [disconnect_task]
        if next_chunk is not None and not next_chunk.done():
            next_chunk.cancel()
            pending.append(next_chunk)
        await asyncio.gather(*pending, return_exceptions=True)


@query_router.get("/api/health")
async def health():
    """Return dependency readiness without exposing connection details."""
    result = await check_health()
    status_code = 200 if result["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=result)


@query_router.post("/api/query")
async def query(
    request: Request,
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
    return QueryStreamingResponse(
        stream_until_disconnect(request, query_service.query(normalized_query)),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
