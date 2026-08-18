import asyncio
import json

import pytest

from app.conf.app_config import app_config
from app.services import query_service as query_service_module
from app.services.query_service import QueryService


def build_service() -> QueryService:
    return QueryService(
        embedding_client=None,
        column_qdrant_repository=None,
        value_es_repository=None,
        metric_qdrant_repository=None,
        meta_mysql_repository=None,
        dw_mysql_repository=None,
    )


def parse_sse(chunk: str) -> dict:
    assert chunk.startswith("data: ")
    return json.loads(chunk.removeprefix("data: ").strip())


@pytest.mark.asyncio
async def test_query_service_returns_chat_event(monkeypatch) -> None:
    monkeypatch.setattr(query_service_module, "is_data_query", lambda _query: False)
    monkeypatch.setattr(query_service_module, "chat_reply", lambda: "我是析问")

    chunks = [chunk async for chunk in build_service().query("你好")]

    assert chunks == ['data: {"type": "chat", "message": "我是析问"}\n\n']


class SlowGraph:
    async def astream(self, **_kwargs):
        await asyncio.sleep(1)
        yield {"type": "result"}


class FailingGraph:
    async def astream(self, **_kwargs):
        raise RuntimeError("graph failed")
        yield


class StreamingGraph:
    async def astream(self, **_kwargs):
        yield {"type": "progress", "step": "检索", "status": "running"}
        await asyncio.sleep(0)
        yield {
            "type": "result",
            "data": [],
            "sql": "SELECT 1 WHERE FALSE",
            "rowCount": 0,
            "truncated": False,
        }


class CancellableGraph:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cleaned = asyncio.Event()

    async def astream(self, **_kwargs):
        try:
            self.started.set()
            await asyncio.sleep(10)
            yield {"type": "result"}
        finally:
            self.cleaned.set()


@pytest.mark.asyncio
async def test_query_service_returns_stable_timeout_error(monkeypatch) -> None:
    monkeypatch.setattr(query_service_module, "graph", SlowGraph())
    monkeypatch.setattr(app_config.api, "query_timeout_seconds", 0.01)

    chunks = [chunk async for chunk in build_service().query("统计销售额")]

    assert parse_sse(chunks[-1]) == {
        "type": "error",
        "code": "QUERY_TIMEOUT",
        "message": "问数执行超时",
    }


@pytest.mark.asyncio
async def test_query_service_returns_stable_failure_code(monkeypatch) -> None:
    monkeypatch.setattr(query_service_module, "graph", FailingGraph())

    chunks = [chunk async for chunk in build_service().query("统计销售额")]

    assert parse_sse(chunks[-1]) == {
        "type": "error",
        "code": "QUERY_FAILED",
        "message": "问数执行失败",
    }


@pytest.mark.asyncio
async def test_query_service_frames_streamed_events_separately(monkeypatch) -> None:
    monkeypatch.setattr(query_service_module, "graph", StreamingGraph())
    monkeypatch.setattr(query_service_module, "is_data_query", lambda _query: True)

    chunks = [chunk async for chunk in build_service().query("统计销售额")]

    assert len(chunks) == 2
    assert parse_sse(chunks[0]) == {
        "type": "progress",
        "step": "检索",
        "status": "running",
    }
    assert parse_sse(chunks[1]) == {
        "type": "result",
        "data": [],
        "sql": "SELECT 1 WHERE FALSE",
        "rowCount": 0,
        "truncated": False,
    }


@pytest.mark.asyncio
async def test_query_service_propagates_cancellation(monkeypatch) -> None:
    graph = CancellableGraph()
    monkeypatch.setattr(query_service_module, "graph", graph)
    monkeypatch.setattr(app_config.api, "query_timeout_seconds", 30)

    async def consume() -> None:
        async for _chunk in build_service().query("统计销售额"):
            pass

    task = asyncio.create_task(consume())
    await graph.started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.wait_for(graph.cleaned.wait(), timeout=1)
