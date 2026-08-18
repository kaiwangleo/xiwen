"""Dependency readiness checks for the Xiwen API."""

import asyncio
from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import text

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.conf.app_config import app_config

HealthProbe = Callable[[], Awaitable[None]]
_READ_ONLY_PRIVILEGES = {"SELECT", "SHOW VIEW", "USAGE"}


def mysql_grants_are_read_only(grants: list[str], database: str) -> bool:
    """Conservatively verify direct grants contain no mutation privileges."""
    target_database = database.replace("`", "").upper()
    has_target_select = False

    for grant in grants:
        normalized = " ".join(grant.upper().split())
        if not normalized.startswith("GRANT ") or " ON " not in normalized:
            continue

        privilege_clause, remainder = normalized.removeprefix("GRANT ").split(" ON ", 1)
        object_scope = remainder.split(" TO ", 1)[0].replace("`", "").strip()
        privileges = {
            item.strip().removesuffix(" PRIVILEGES")
            for item in privilege_clause.split(",")
        }
        if not privileges.issubset(_READ_ONLY_PRIVILEGES):
            return False

        if "SELECT" in privileges and (
            object_scope == "*.*" or object_scope.startswith(f"{target_database}.")
        ):
            has_target_select = True

    return has_target_select


async def collect_dependency_health(
    probes: Mapping[str, HealthProbe],
    *,
    timeout_seconds: float,
) -> dict:
    """Run bounded probes and return non-sensitive readiness states."""

    async def run_probe(name: str, probe: HealthProbe) -> tuple[str, str]:
        try:
            async with asyncio.timeout(timeout_seconds):
                await probe()
        except Exception:  # noqa: BLE001 - health probes collapse failures by contract
            return name, "unavailable"
        return name, "ok"

    results = await asyncio.gather(
        *(run_probe(name, probe) for name, probe in probes.items())
    )
    dependencies = dict(results)
    status = (
        "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    )
    return {"status": status, "dependencies": dependencies}


async def _check_mysql(manager) -> None:
    if manager.engine is None:
        raise RuntimeError("MySQL client is not initialized")
    async with manager.engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def _check_dw_read_only() -> None:
    manager = dw_mysql_client_manager
    if manager.engine is None:
        raise RuntimeError("MySQL client is not initialized")
    async with manager.engine.connect() as connection:
        result = await connection.execute(text("SHOW GRANTS FOR CURRENT_USER()"))
        grants = [str(row[0]) for row in result.fetchall()]
    if not mysql_grants_are_read_only(grants, manager.db_config.database):
        raise RuntimeError("Warehouse account is not verified as read-only")


async def _check_qdrant() -> None:
    if qdrant_client_manager.client is None:
        raise RuntimeError("Qdrant client is not initialized")
    await qdrant_client_manager.client.get_collections()


async def _check_elasticsearch() -> None:
    if es_client_manager.client is None or not await es_client_manager.client.ping():
        raise RuntimeError("Elasticsearch is unavailable")


async def _check_embedding() -> None:
    if embedding_client_manager.client is None:
        raise RuntimeError("Embedding client is not initialized")
    await embedding_client_manager.client.health()


async def _check_llm_config() -> None:
    required = (app_config.llm.model_name, app_config.llm.base_url)
    if any(
        not value.strip() or value.strip().upper().startswith("CHANGE_ME")
        for value in required
    ):
        raise RuntimeError("LLM configuration is incomplete")


async def check_health() -> dict:
    """Check every runtime dependency used by the query graph."""
    return await collect_dependency_health(
        {
            "mysql_meta": lambda: _check_mysql(meta_mysql_client_manager),
            "mysql_dw": lambda: _check_mysql(dw_mysql_client_manager),
            "mysql_dw_read_only": _check_dw_read_only,
            "qdrant": _check_qdrant,
            "elasticsearch": _check_elasticsearch,
            "embedding": _check_embedding,
            "llm_config": _check_llm_config,
        },
        timeout_seconds=app_config.api.health_timeout_seconds,
    )
