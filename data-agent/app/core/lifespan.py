from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.services.semantic_service import ensure_semantic_table
from app.services.session_service import ensure_session_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化客户端并确保会话/语义表存在，退出时关连接。"""
    # FastAPI 应用启动前执行
    embedding_client_manager.init()
    qdrant_client_manager.init()
    es_client_manager.init()
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()
    await ensure_session_tables(meta_mysql_client_manager.engine)
    await ensure_semantic_table(meta_mysql_client_manager.engine)
    yield
    # FastAPI 应用结束前执行

    await qdrant_client_manager.close()
    await es_client_manager.close()
    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
