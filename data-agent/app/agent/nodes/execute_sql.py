from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.progress import emit_progress
from app.agent.state import DataAgentState
from app.conf.app_config import app_config
from app.core.error_sanitizer import sanitize_error_message
from app.core.log import logger

STEP = "执行SQL"
STACK = ["MySQL 数仓"]
DESC = "在数仓执行最终 SQL 并返回结果行"


async def execute_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    emit_progress(writer, STEP, "running", stack=STACK, desc=DESC)

    sql = state["sql"]

    dw_mysql_repository = runtime.context["dw_mysql_repository"]

    try:
        result = await dw_mysql_repository.execute_sql(
            sql,
            max_rows=app_config.api.max_result_rows,
            timeout_seconds=app_config.api.sql_timeout_seconds,
        )

        emit_progress(
            writer,
            STEP,
            "success",
            stack=STACK,
            desc=DESC,
            detail=f"返回 {result.row_count} 行"
            + ("（已截断）" if result.truncated else ""),
        )
        writer(
            {
                "type": "result",
                "data": result.rows,
                "sql": sql,
                "rowCount": result.row_count,
                "truncated": result.truncated,
            }
        )
        logger.info(
            f"SQL执行完成: row_count={result.row_count}, truncated={result.truncated}"
        )

    except Exception as exc:
        safe_error = sanitize_error_message(exc)
        emit_progress(
            writer, STEP, "error", stack=STACK, desc=DESC, detail="SQL 执行失败"
        )
        logger.error(f"执行SQL失败: {safe_error}")
        raise
