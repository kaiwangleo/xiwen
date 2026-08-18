import asyncio

import pytest

from app.conf.app_config import app_config
from app.services.health_service import (
    _check_llm_config,
    collect_dependency_health,
    mysql_grants_are_read_only,
)


async def healthy_probe() -> None:
    return None


async def failing_probe() -> None:
    raise RuntimeError("credential details must not leak")


async def slow_probe() -> None:
    await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_collect_dependency_health_reports_all_healthy() -> None:
    result = await collect_dependency_health(
        {"mysql": healthy_probe, "qdrant": healthy_probe},
        timeout_seconds=0.1,
    )

    assert result == {
        "status": "ok",
        "dependencies": {"mysql": "ok", "qdrant": "ok"},
    }


@pytest.mark.asyncio
async def test_collect_dependency_health_contains_failures() -> None:
    result = await collect_dependency_health(
        {"mysql": healthy_probe, "elasticsearch": failing_probe},
        timeout_seconds=0.1,
    )

    assert result == {
        "status": "degraded",
        "dependencies": {"mysql": "ok", "elasticsearch": "unavailable"},
    }
    assert "credential" not in str(result)


@pytest.mark.asyncio
async def test_collect_dependency_health_bounds_each_probe() -> None:
    result = await collect_dependency_health(
        {"embedding": slow_probe},
        timeout_seconds=0.01,
    )

    assert result == {
        "status": "degraded",
        "dependencies": {"embedding": "unavailable"},
    }


def test_mysql_grants_accept_select_only_warehouse_user() -> None:
    grants = [
        "GRANT USAGE ON *.* TO `xiwen_readonly`@`%`",
        "GRANT SELECT, SHOW VIEW ON `dw`.* TO `xiwen_readonly`@`%`",
    ]

    assert mysql_grants_are_read_only(grants, "dw") is True


@pytest.mark.parametrize(
    "grants",
    [
        ["GRANT ALL PRIVILEGES ON *.* TO `root`@`%`"],
        ["GRANT SELECT, INSERT ON `dw`.* TO `writer`@`%`"],
        ["GRANT SELECT ON `other`.* TO `reader`@`%`"],
        ["GRANT `analytics_role`@`%` TO `reader`@`%`"],
    ],
)
def test_mysql_grants_reject_unverified_or_mutating_access(grants: list[str]) -> None:
    assert mysql_grants_are_read_only(grants, "dw") is False


@pytest.mark.asyncio
async def test_llm_health_requires_model_and_base_url(monkeypatch) -> None:
    monkeypatch.setattr(app_config.llm, "model_name", "")
    monkeypatch.setattr(app_config.llm, "base_url", "")

    with pytest.raises(RuntimeError, match="incomplete"):
        await _check_llm_config()

    monkeypatch.setattr(app_config.llm, "model_name", "test-model")
    monkeypatch.setattr(app_config.llm, "base_url", "http://127.0.0.1:8001/v1")
    await _check_llm_config()
