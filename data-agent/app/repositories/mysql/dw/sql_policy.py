"""Conservative MySQL read-only query validation and result bounding."""

from sqlglot import exp, parse
from sqlglot.errors import ParseError, TokenError


class UnsafeSQLError(ValueError):
    """Raised when SQL is invalid or can mutate state."""


_DISALLOWED_NODE_KEYS = {
    "into",
    "lock",
}

_DISALLOWED_FUNCTIONS = {
    "BENCHMARK",
    "GET_LOCK",
    "IS_FREE_LOCK",
    "IS_USED_LOCK",
    "LOAD_FILE",
    "MASTER_POS_WAIT",
    "RELEASE_ALL_LOCKS",
    "RELEASE_LOCK",
    "SLEEP",
    "SOURCE_POS_WAIT",
    "SYS_EVAL",
    "SYS_EXEC",
    "UUID_SHORT",
}


def _function_name(node: exp.Func) -> str:
    """Return the SQL function name for built-in and anonymous functions."""
    if isinstance(node, exp.Anonymous):
        return node.name.upper()
    return node.sql_name().upper()


def _parse_read_only_query(sql: str) -> exp.Query:
    """Parse exactly one MySQL query and reject stateful or ambiguous syntax."""
    candidate = sql.strip()
    if not candidate:
        raise UnsafeSQLError("SQL 不能为空")

    try:
        statements = parse(candidate, read="mysql")
    except (ParseError, TokenError) as exc:
        raise UnsafeSQLError(f"SQL 解析失败: {exc}") from exc

    if len(statements) != 1 or statements[0] is None:
        raise UnsafeSQLError("只允许执行一条 SQL")

    statement = statements[0]
    if not isinstance(statement, exp.Query):
        raise UnsafeSQLError("只允许 SELECT 或只读 CTE 查询")

    for node in statement.walk():
        if node.comments:
            raise UnsafeSQLError("SQL 中不允许使用注释")
        if isinstance(
            node,
            (exp.DDL, exp.DML, exp.Command, exp.Grant, exp.Set, exp.Transaction),
        ):
            raise UnsafeSQLError("查询中不允许嵌套数据修改或管理语句")
        if node.key in _DISALLOWED_NODE_KEYS:
            raise UnsafeSQLError(f"不允许只读查询中的 {node.key.upper()} 子句")
        if isinstance(node, (exp.Parameter, exp.PropertyEQ)):
            raise UnsafeSQLError("不允许读取或修改 MySQL 会话变量")
        if isinstance(node, exp.Func) and _function_name(node) in _DISALLOWED_FUNCTIONS:
            raise UnsafeSQLError(f"不允许调用函数 {_function_name(node)}")

    return statement


def normalize_read_only_sql(sql: str) -> str:
    """Return normalized SQL after enforcing the read-only policy."""
    statement = _parse_read_only_query(sql)
    return statement.sql(dialect="mysql", pretty=False).strip().rstrip(";")


def limit_read_only_sql(sql: str, *, max_rows: int) -> str:
    """Return validated SQL whose database-side row limit is at most max_rows + 1."""
    if max_rows <= 0:
        raise ValueError("max_rows 必须大于 0")

    statement = _parse_read_only_query(sql)
    fetch_limit = max_rows + 1
    limit = statement.args.get("limit")
    existing_limit: int | None = None
    if isinstance(limit, exp.Limit) and isinstance(limit.expression, exp.Literal):
        try:
            existing_limit = int(limit.expression.this)
        except (TypeError, ValueError):
            existing_limit = None

    if existing_limit is None or existing_limit > fetch_limit:
        statement = statement.limit(fetch_limit, copy=True)

    return statement.sql(dialect="mysql", pretty=False).strip().rstrip(";")
