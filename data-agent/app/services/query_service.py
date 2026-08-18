import asyncio
import json

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
        )
        if not is_data_query(query):
            chat_event: ChatEvent = {"type": "chat", "message": chat_reply()}
            yield encode_sse(chat_event)
            return

        state = DataAgentState(query=query)
        try:
            async with asyncio.timeout(app_config.api.query_timeout_seconds):
                async for chunk in graph.astream(
                    input=state, context=context, stream_mode="custom"
                ):
                    yield encode_sse(chunk)
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
