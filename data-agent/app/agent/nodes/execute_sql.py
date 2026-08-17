from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.progress import emit_progress
from app.agent.state import DataAgentState
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
        result = await dw_mysql_repository.execute_sql(sql)

        emit_progress(
            writer,
            STEP,
            "success",
            stack=STACK,
            desc=DESC,
            detail=f"返回 {len(result)} 行",
        )
        writer({"type": "result", "data": result, "sql": sql})
        logger.info(f"执行SQL结果: {result}")


    except Exception as e:
        emit_progress(writer, STEP, "error", stack=STACK, desc=DESC, detail=str(e))
        logger.error(f"执行SQL失败:{str(e)}")
        raise
