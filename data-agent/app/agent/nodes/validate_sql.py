from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.progress import emit_progress
from app.agent.state import DataAgentState
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
        await dw_mysql_repository.validate_sql(sql)
        emit_progress(writer, STEP, "success", stack=STACK, desc=DESC, detail="EXPLAIN 通过")
        logger.info(f"SQL验证成功: {sql}")
        return {"error": None}
    except Exception as e:
        emit_progress(writer, STEP, "error", stack=STACK, desc=DESC, detail=str(e))
        logger.error(f"SQL验证失败: {sql}")
        return {"error": str(e)}
