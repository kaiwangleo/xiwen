import asyncio
from dataclasses import dataclass

import pytest

from app.repositories.mysql.dw.dw_mysql_repository import (
    DWMySQLRepository,
    SQLExecutionTimeoutError,
)
from app.repositories.mysql.dw.sql_policy import UnsafeSQLError


class FakeMappings:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.fetch_sizes: list[int] = []

    def fetchmany(self, size: int) -> list[dict]:
        self.fetch_sizes.append(size)
        return self.rows[:size]


@dataclass
class FakeResult:
    mapped_rows: list[dict]

    def __post_init__(self) -> None:
        self.mapping_result = FakeMappings(self.mapped_rows)

    def mappings(self) -> FakeMappings:
        return self.mapping_result


class FakeSession:
    def __init__(self, rows: list[dict] | None = None):
        self.result = FakeResult(rows or [])
        self.statements: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None) -> FakeResult:
        self.statements.append((str(statement), params))
        return self.result


class SlowSession(FakeSession):
    async def execute(self, statement, params=None) -> FakeResult:
        await asyncio.sleep(1)
        return await super().execute(statement, params)


class CancellableSession(FakeSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0
        self.query_started = asyncio.Event()
        self.query_cleaned = asyncio.Event()

    async def execute(self, statement, params=None) -> FakeResult:
        self.calls += 1
        if self.calls == 1:
            return await super().execute(statement, params)
        try:
            self.query_started.set()
            await asyncio.sleep(10)
            return await super().execute(statement, params)
        finally:
            self.query_cleaned.set()


@pytest.mark.asyncio
async def test_validate_sql_normalizes_before_explain() -> None:
    session = FakeSession()
    repository = DWMySQLRepository(session)

    normalized = await repository.validate_sql("select 1;", timeout_seconds=1)

    assert normalized == "SELECT 1"
    assert session.statements == [("explain SELECT 1", None)]


@pytest.mark.asyncio
async def test_validate_sql_rejects_mutation_before_database_call() -> None:
    session = FakeSession()
    repository = DWMySQLRepository(session)

    with pytest.raises(UnsafeSQLError):
        await repository.validate_sql("DELETE FROM orders", timeout_seconds=1)

    assert session.statements == []


@pytest.mark.asyncio
async def test_execute_sql_bounds_rows_and_marks_truncation() -> None:
    session = FakeSession([{"id": 1}, {"id": 2}, {"id": 3}])
    repository = DWMySQLRepository(session)

    result = await repository.execute_sql(
        "SELECT id FROM orders",
        max_rows=2,
        timeout_seconds=1,
    )

    assert result.rows == [{"id": 1}, {"id": 2}]
    assert result.row_count == 2
    assert result.truncated is True
    assert session.result.mapping_result.fetch_sizes == [3]
    assert session.statements == [
        (
            "SET SESSION MAX_EXECUTION_TIME = :timeout_ms",
            {"timeout_ms": 1000},
        ),
        ("SELECT id FROM orders LIMIT 3", None),
    ]


@pytest.mark.asyncio
async def test_execute_sql_does_not_mark_exact_limit_as_truncated() -> None:
    session = FakeSession([{"id": 1}, {"id": 2}])
    repository = DWMySQLRepository(session)

    result = await repository.execute_sql(
        "SELECT id FROM orders LIMIT 2",
        max_rows=2,
        timeout_seconds=1,
    )

    assert result.rows == [{"id": 1}, {"id": 2}]
    assert result.truncated is False


@pytest.mark.asyncio
async def test_execute_sql_rejects_non_positive_limit() -> None:
    session = FakeSession([{"id": 1}])
    repository = DWMySQLRepository(session)

    with pytest.raises(ValueError, match="max_rows"):
        await repository.execute_sql(
            "SELECT id FROM orders",
            max_rows=0,
            timeout_seconds=1,
        )

    assert session.statements == []


@pytest.mark.asyncio
async def test_execute_sql_rejects_non_positive_timeout() -> None:
    session = FakeSession([{"id": 1}])
    repository = DWMySQLRepository(session)

    with pytest.raises(ValueError, match="timeout_seconds"):
        await repository.execute_sql(
            "SELECT id FROM orders",
            max_rows=1,
            timeout_seconds=0,
        )

    assert session.statements == []


@pytest.mark.asyncio
async def test_execute_sql_raises_stable_timeout() -> None:
    repository = DWMySQLRepository(SlowSession())

    with pytest.raises(SQLExecutionTimeoutError, match="SQL 执行超时"):
        await repository.execute_sql(
            "SELECT id FROM orders",
            max_rows=1,
            timeout_seconds=0.01,
        )


@pytest.mark.asyncio
async def test_execute_sql_propagates_cancellation_to_database_call() -> None:
    session = CancellableSession()
    repository = DWMySQLRepository(session)
    task = asyncio.create_task(
        repository.execute_sql(
            "SELECT id FROM orders",
            max_rows=1,
            timeout_seconds=30,
        )
    )
    await session.query_started.wait()

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.wait_for(session.query_cleaned.wait(), timeout=1)
