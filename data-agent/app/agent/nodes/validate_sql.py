from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.progress import emit_progress
from app.agent.state import DataAgentState
from app.conf.app_config import app_config
from app.core.error_sanitizer import sanitize_error_message
from app.core.log import logger

STEP = "验证SQL"
STACK = ["MySQL EXPLAIN"]
DESC = "对生成的 SQL 做 EXPLAIN，语法或权限错误会走校正"


async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    emit_progress(writer, STEP, "running", stack=STACK, desc=DESC)

    dw_mysql_repository = runtime.context["dw_mysql_repository"]

    sql = state["sql"]

    try:
        normalized_sql = await dw_mysql_repository.validate_sql(
            sql,
            timeout_seconds=app_config.api.sql_timeout_seconds,
        )
        emit_progress(
            writer, STEP, "success", stack=STACK, desc=DESC, detail="EXPLAIN 通过"
        )
        logger.info(f"SQL验证成功: {normalized_sql}")
        return {"error": None, "sql": normalized_sql}
    except Exception as e:  # noqa: BLE001 - validation errors feed the correction branch
        safe_error = sanitize_error_message(e)
        emit_progress(
            writer, STEP, "error", stack=STACK, desc=DESC, detail="SQL 校验未通过"
        )
        logger.warning(f"SQL验证失败: {sql}; 原因: {safe_error}")
        return {"error": safe_error}
