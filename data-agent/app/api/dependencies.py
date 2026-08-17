from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.embedding_client_manager import LocalEmbeddingClient, embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.knowledge_service import KnowledgeService
from app.services.query_service import QueryService


async def get_meta_session():
    """打开元库会话，请求结束时关闭。"""
    async with meta_mysql_client_manager.session_factory() as session:
        yield session


async def get_dw_session():
    """打开数仓会话，请求结束时关闭。"""
    async with dw_mysql_client_manager.session_factory() as session:
        yield session


async def get_embedding_client():
    """取当前 Embedding 客户端。"""
    return embedding_client_manager.client


async def get_column_qdrant_repository():
    """取字段向量仓库。"""
    return ColumnQdrantRepository(qdrant_client_manager.client)


async def get_value_es_repository():
    """取字段取值 ES 仓库。"""
    return ValueESRepository(es_client_manager.client)


async def get_metric_qdrant_repository():
    """取指标向量仓库。"""
    return MetricQdrantRepository(qdrant_client_manager.client)


async def get_meta_mysql_repository(session: AsyncSession = Depends(get_meta_session)):
    """用请求级元库会话构造仓库。"""
    return MetaMySQLRepository(session)


async def get_dw_mysql_repository(session: AsyncSession = Depends(get_dw_session)):
    """用请求级数仓会话构造仓库。"""
    return DWMySQLRepository(session)


def build_knowledge_service(meta_session: AsyncSession, dw_session: AsyncSession) -> KnowledgeService:
    """用已打开的 meta/dw 会话组装知识构建服务，避免请求级 Depends 提前占连接。"""
    return KnowledgeService(
        meta_mysql_repository=MetaMySQLRepository(meta_session),
        dw_mysql_repository=DWMySQLRepository(dw_session),
        column_qdrant_repository=ColumnQdrantRepository(qdrant_client_manager.client),
        embedding_client=embedding_client_manager.client,
        value_es_repository=ValueESRepository(es_client_manager.client),
        metric_qdrant_repository=MetricQdrantRepository(qdrant_client_manager.client),
    )


async def get_query_service(
        embedding_client: LocalEmbeddingClient = Depends(get_embedding_client),
        column_qdrant_repository: ColumnQdrantRepository = Depends(get_column_qdrant_repository),
        value_es_repository: ValueESRepository = Depends(get_value_es_repository),
        metric_qdrant_repository: MetricQdrantRepository = Depends(get_metric_qdrant_repository),
        meta_mysql_repository: MetaMySQLRepository = Depends(get_meta_mysql_repository),
        dw_mysql_repository: DWMySQLRepository = Depends(get_dw_mysql_repository)
) -> QueryService:
    """组装问数服务（会话随请求生命周期）。"""
    return QueryService(
        embedding_client=embedding_client,
        column_qdrant_repository=column_qdrant_repository,
        value_es_repository=value_es_repository,
        metric_qdrant_repository=metric_qdrant_repository,
        meta_mysql_repository=meta_mysql_repository,
        dw_mysql_repository=dw_mysql_repository
    )
