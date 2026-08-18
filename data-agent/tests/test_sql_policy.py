import pytest

from app.repositories.mysql.dw.sql_policy import (
    UnsafeSQLError,
    limit_read_only_sql,
    normalize_read_only_sql,
)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "SELECT ';' AS literal;",
        "WITH totals AS (SELECT SUM(amount) AS value FROM orders) SELECT value FROM totals",
        "SELECT id FROM current_orders UNION ALL SELECT id FROM archived_orders",
        "SELECT COUNT(*) FROM orders WHERE created_at >= CURRENT_DATE - INTERVAL 7 DAY",
        "SELECT ':=' AS literal",
        "SELECT '--not a comment' AS literal",
    ],
)
def test_normalize_read_only_sql_accepts_queries(sql: str) -> None:
    normalized = normalize_read_only_sql(sql)

    assert normalized
    assert not normalized.endswith(";")


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "UPDATE orders SET amount = 0",
        "DELETE FROM orders",
        "INSERT INTO audit_log(message) VALUES ('x')",
        "DROP TABLE orders",
        "SHOW TABLES",
        "EXPLAIN SELECT * FROM orders",
        "SELECT 1; SELECT 2",
        "SELECT SLEEP(10)",
        "SELECT GET_LOCK('xiwen', 10)",
        "SELECT RELEASE_LOCK('xiwen')",
        "SELECT LOAD_FILE('/etc/passwd')",
        "SELECT SYS_EXEC('id')",
        "SELECT SYS_EVAL('id')",
        "SELECT 1 INTO OUTFILE '/tmp/xiwen.txt'",
        "SELECT * FROM orders FOR UPDATE",
        "SELECT @xiwen_value := 1",
        "SELECT @xiwen_value",
        "SELECT 1 /* comments are not accepted */",
        "SELECT /*!50000 SLEEP(10) */ 1",
        "SELECT 1; -- hidden statement\nDELETE FROM orders",
        "WITH changed AS (DELETE FROM orders RETURNING id) SELECT * FROM changed",
    ],
)
def test_normalize_read_only_sql_rejects_unsafe_statements(sql: str) -> None:
    with pytest.raises(UnsafeSQLError):
        normalize_read_only_sql(sql)


def test_normalize_read_only_sql_rejects_invalid_sql() -> None:
    with pytest.raises(UnsafeSQLError, match="解析"):
        normalize_read_only_sql("SELECT FROM")


@pytest.mark.parametrize(
    ("sql", "max_rows", "expected"),
    [
        ("SELECT id FROM orders", 2, "SELECT id FROM orders LIMIT 3"),
        ("SELECT id FROM orders LIMIT 1", 2, "SELECT id FROM orders LIMIT 1"),
        ("SELECT id FROM orders LIMIT 100", 2, "SELECT id FROM orders LIMIT 3"),
        (
            "SELECT id FROM orders LIMIT 100 OFFSET 4",
            2,
            "SELECT id FROM orders LIMIT 3 OFFSET 4",
        ),
    ],
)
def test_limit_read_only_sql_enforces_database_row_bound(
    sql: str,
    max_rows: int,
    expected: str,
) -> None:
    assert limit_read_only_sql(sql, max_rows=max_rows) == expected


def test_limit_read_only_sql_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError, match="max_rows"):
        limit_read_only_sql("SELECT 1", max_rows=0)
