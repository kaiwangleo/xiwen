from app.agent.llm import llm
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.core.log import logger


def _changed(old: dict, new: dict, *keys: str) -> bool:
    """比较配置树某一路径是否变化。"""
    cur_old, cur_new = old, new
    for key in keys:
        if not isinstance(cur_old, dict) or not isinstance(cur_new, dict):
            return cur_old != cur_new
        cur_old = cur_old.get(key)
        cur_new = cur_new.get(key)
    return cur_old != cur_new


def _any_changed(old: dict, new: dict, prefixes: list[tuple[str, ...]]) -> bool:
    """任一路径变化即为真。"""
    return any(_changed(old, new, *prefix) for prefix in prefixes)


async def apply_runtime_changes(old: dict, new: dict) -> dict:
    """按变更热加载客户端；向量维度/模型变化只告警不自动重建。"""
    reloaded: list[str] = []
    warnings: list[str] = []

    if _any_changed(old, new, [("llm",)]):
        llm.reload()
        reloaded.append("llm")
        logger.info("已热加载 LLM")

    if _any_changed(old, new, [("embedding",)]):
        await embedding_client_manager.reload()
        reloaded.append("embedding")
        logger.info("已热加载 Embedding 客户端")
        if _changed(old, new, "embedding", "model"):
            warnings.append("Embedding 模型已更换，请重建知识库")

    if _changed(old, new, "qdrant", "host") or _changed(old, new, "qdrant", "port"):
        await qdrant_client_manager.reload()
        reloaded.append("qdrant")
        logger.info("已热加载 Qdrant 客户端")

    if _changed(old, new, "qdrant", "embedding_size"):
        warnings.append("向量维度已变化，请重建知识库")

    if _changed(old, new, "es", "host") or _changed(old, new, "es", "port"):
        await es_client_manager.reload()
        reloaded.append("es")
        logger.info("已热加载 Elasticsearch 客户端")

    if _any_changed(old, new, [("db_meta",)]):
        await meta_mysql_client_manager.reload()
        reloaded.append("db_meta")
        logger.info("已热加载 meta 数据库连接")

    if _any_changed(old, new, [("db_dw",)]):
        await dw_mysql_client_manager.reload()
        reloaded.append("db_dw")
        logger.info("已热加载 dw 数据库连接")

    return {
        "restart_required": False,
        "reloaded": reloaded,
        "rebuild_required": bool(warnings),
        "runtime_warnings": warnings,
    }
