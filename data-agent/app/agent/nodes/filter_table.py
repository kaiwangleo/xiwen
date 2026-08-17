import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.progress import emit_progress
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt

STEP = "过滤表格"
STACK = ["LLM"]
DESC = "大模型按问题留下相关表和字段，去掉无关列"


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    emit_progress(writer, STEP, "running", stack=STACK, desc=DESC)

    query = state["query"]
    table_infos = state["table_infos"]

    try:
        # 用LLM过滤表信息
        prompt = PromptTemplate(template=load_prompt("filter_table_info"), input_variables=["query", "table_infos"])
        output_parser = JsonOutputParser()

        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {"query": query, "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False)})

        # 利用模型输出过滤table_infos
        # {
        #   'fact_order':['order_amount', 'region_id'],
        #   'dim_region':['region_id', 'region_name']
        # }
        for table_info in table_infos[:]:
            if table_info["name"] not in result:
                table_infos.remove(table_info)
            else:
                selected_columns = result[table_info["name"]]
                for column_info in table_info["columns"][:]:
                    if column_info["name"] not in selected_columns:
                        table_info["columns"].remove(column_info)

        table_detail = "；".join(
            f"{table_info['name']}({', '.join(col['name'] for col in table_info['columns'])})"
            for table_info in table_infos
        ) or "无"
        emit_progress(
            writer,
            STEP,
            "success",
            stack=STACK,
            desc=DESC,
            detail=table_detail,
        )
        logger.info(f"过滤后的表信息: {[table_info['name'] for table_info in table_infos]}")
        return {"table_infos": table_infos}
    except Exception as e:
        emit_progress(writer, STEP, "error", stack=STACK, desc=DESC)
        logger.error(f"过滤表失败:{str(e)}")
        raise
