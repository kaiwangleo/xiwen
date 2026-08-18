from types import SimpleNamespace

import pytest

from app.agent.nodes.execute_sql import execute_sql
from app.agent.nodes.validate_sql import validate_sql
from app.conf.app_config import app_config
from app.repositories.mysql.dw.dw_mysql_repository import QueryRows


class FakeDWRepository:
    def __init__(self, rows: list[dict] | None = None, truncated: bool = True) -> None:
        self.rows = [{"value": 1}, {"value": 2}] if rows is None else rows
        self.truncated = truncated
        self.validations: list[tuple[str, float]] = []
        self.executions: list[tuple[str, int, float]] = []

    async def validate_sql(self, sql: str, *, timeout_seconds: float) -> str:
        assert sql == "select 1;"
        self.validations.append((sql, timeout_seconds))
        return "SELECT 1"

    async def execute_sql(
        self,
        sql: str,
        *,
        max_rows: int,
        timeout_seconds: float,
    ) -> QueryRows:
        self.executions.append((sql, max_rows, timeout_seconds))
        return QueryRows(rows=self.rows, truncated=self.truncated)


class FailingDWRepository(FakeDWRepository):
    async def validate_sql(self, sql: str, *, timeout_seconds: float) -> str:
        raise RuntimeError("password=must-not-leak")

    async def execute_sql(
        self,
        sql: str,
        *,
        max_rows: int,
        timeout_seconds: float,
    ) -> QueryRows:
        raise RuntimeError("password=must-not-leak")


@pytest.mark.asyncio
async def test_validate_node_propagates_normalized_sql(monkeypatch) -> None:
    events: list[dict] = []
    repository = FakeDWRepository()
    runtime = SimpleNamespace(
        stream_writer=events.append,
        context={"dw_mysql_repository": repository},
    )
    monkeypatch.setattr(app_config.api, "sql_timeout_seconds", 4)

    update = await validate_sql({"sql": "select 1;"}, runtime)

    assert update == {"error": None, "sql": "SELECT 1"}
    assert repository.validations == [("select 1;", 4)]
    assert events[-1]["type"] == "progress"
    assert events[-1]["status"] == "success"


@pytest.mark.asyncio
async def test_execute_node_emits_bounded_result(monkeypatch) -> None:
    events: list[dict] = []
    repository = FakeDWRepository()
    runtime = SimpleNamespace(
        stream_writer=events.append,
        context={"dw_mysql_repository": repository},
    )
    monkeypatch.setattr(app_config.api, "max_result_rows", 2)
    monkeypatch.setattr(app_config.api, "sql_timeout_seconds", 4)

    await execute_sql({"sql": "SELECT 1"}, runtime)

    assert repository.executions == [("SELECT 1", 2, 4)]
    assert events[-1] == {
        "type": "result",
        "data": [{"value": 1}, {"value": 2}],
        "sql": "SELECT 1",
        "rowCount": 2,
        "truncated": True,
    }


@pytest.mark.asyncio
async def test_execute_node_emits_empty_result(monkeypatch) -> None:
    events: list[dict] = []
    repository = FakeDWRepository(rows=[], truncated=False)
    runtime = SimpleNamespace(
        stream_writer=events.append,
        context={"dw_mysql_repository": repository},
    )
    monkeypatch.setattr(app_config.api, "max_result_rows", 2)
    monkeypatch.setattr(app_config.api, "sql_timeout_seconds", 4)

    await execute_sql({"sql": "SELECT 1 WHERE FALSE"}, runtime)

    assert events[-1] == {
        "type": "result",
        "data": [],
        "sql": "SELECT 1 WHERE FALSE",
        "rowCount": 0,
        "truncated": False,
    }


@pytest.mark.asyncio
async def test_sql_node_progress_does_not_expose_internal_error(monkeypatch) -> None:
    events: list[dict] = []
    repository = FailingDWRepository()
    runtime = SimpleNamespace(
        stream_writer=events.append,
        context={"dw_mysql_repository": repository},
    )
    monkeypatch.setattr(app_config.api, "sql_timeout_seconds", 4)
    monkeypatch.setattr(app_config.db_dw, "password", "must-not-leak")

    update = await validate_sql({"sql": "select 1;"}, runtime)

    assert update["error"] == "password=***"
    assert events[-1]["detail"] == "SQL 校验未通过"
    assert "must-not-leak" not in str(events[-1])

    with pytest.raises(RuntimeError, match="must-not-leak"):
        await execute_sql({"sql": "SELECT 1"}, runtime)
    assert events[-1]["detail"] == "SQL 执行失败"
    assert "must-not-leak" not in str(events[-1])
