import asyncio
import json
from contextlib import aclosing
from typing import Any

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.intent import chat_reply, is_data_query
from app.agent.state import DataAgentState
from app.api.schemas.sse_schema import ChatEvent, ErrorEvent, SSEEvent
from app.clients.embedding_client_manager import LocalEmbeddingClient
from app.conf.app_config import app_config
from app.core.error_sanitizer import sanitize_error_message
from app.core.log import logger
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


def encode_sse(event: SSEEvent | dict) -> str:
    """Serialize one complete SSE data event with a stable frame boundary."""
    return f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"


async def wait_for_task_cleanup(task: asyncio.Task) -> None:
    """Wait for a cancelled LangGraph task and its deferred exit tasks."""
    cleanup_futures: list[asyncio.Future] = []
    try:
        await task
    except asyncio.CancelledError as exc:
        cleanup_futures.extend(
            arg for arg in exc.args if isinstance(arg, asyncio.Future)
        )

    while cleanup_futures:
        cleanup = cleanup_futures.pop()
        try:
            await asyncio.shield(cleanup)
        except asyncio.CancelledError as exc:
            cleanup_futures.extend(
                arg for arg in exc.args if isinstance(arg, asyncio.Future)
            )


class QueryService:
    def __init__(
        self,
        embedding_client: LocalEmbeddingClient,
        column_qdrant_repository: ColumnQdrantRepository,
        value_es_repository: ValueESRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        meta_mysql_repository: MetaMySQLRepository,
        dw_mysql_repository: DWMySQLRepository,
    ):
        self.embedding_client = embedding_client
        self.column_qdrant_repository = column_qdrant_repository
        self.value_es_repository = value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository

    async def query(self, query: str):
        """闲聊直接 SSE chat；问数则跑图并以 custom 流推 progress/result/error。"""
        context = DataAgentContext(
            embedding_client=self.embedding_client,
            column_qdrant_repository=self.column_qdrant_repository,
            value_es_repository=self.value_es_repository,
            metric_qdrant_repository=self.metric_qdrant_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository,
            cancel_event=asyncio.Event(),
        )
        if not is_data_query(query):
            chat_event: ChatEvent = {"type": "chat", "message": chat_reply()}
            yield encode_sse(chat_event)
            return

        state = DataAgentState(query=query)
        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        done = object()

        async def run_graph() -> None:
            try:
                async with aclosing(
                    graph.astream(input=state, context=context, stream_mode="custom")
                ) as stream:
                    async for chunk in stream:
                        await queue.put(("chunk", chunk))
            except Exception as exc:  # noqa: BLE001 - forwarded to public error boundary
                await queue.put(("error", exc))
            finally:
                await queue.put(("done", done))

        graph_task = asyncio.create_task(run_graph())
        try:
            try:
                async with asyncio.timeout(app_config.api.query_timeout_seconds):
                    while True:
                        kind, item = await queue.get()
                        if kind == "done":
                            break
                        if kind == "error":
                            raise item
                        yield encode_sse(item)
            finally:
                if not graph_task.done():
                    context["cancel_event"].set()
                    graph_task.cancel()
                await wait_for_task_cleanup(graph_task)
        except asyncio.CancelledError:
            logger.info("问数请求已取消")
            raise
        except TimeoutError:
            timeout_event: ErrorEvent = {
                "type": "error",
                "code": "QUERY_TIMEOUT",
                "message": "问数执行超时",
            }
            yield encode_sse(timeout_event)
        except Exception as exc:  # noqa: BLE001 - stable public error boundary
            logger.error(f"问数执行失败: {sanitize_error_message(exc)}")
            failure_event: ErrorEvent = {
                "type": "error",
                "code": "QUERY_FAILED",
                "message": "问数执行失败",
            }
            yield encode_sse(failure_event)
