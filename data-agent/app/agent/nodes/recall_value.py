from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.progress import emit_progress
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.value_info import ValueInfo
from app.prompt.prompt_loader import load_prompt

STEP = "召回字段取值"
STACK = ["LLM", "Elasticsearch"]
DESC = "大模型抽出取值词，再用 IK 在 Elasticsearch 检索字段枚举"


async def recall_value(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    emit_progress(writer, STEP, "running", stack=STACK, desc=DESC)

    query = state["query"]
    keywords = state["keywords"]

    value_es_repository = runtime.context["value_es_repository"]

    try:
        # 使用LLM扩展关键词
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_value_recall"), input_variables=["query"])
        output_parser = JsonOutputParser()

        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"query": query})

        # 使用扩展后的关键词召回字段取值
        values_map: dict[str, ValueInfo] = {}
        keywords = list(set(keywords + result))
        logger.info(f"召回字段取值扩展关键词：{keywords}")
        for keyword in keywords:
            values: list[ValueInfo] = await value_es_repository.search(keyword)
            for value in values:
                value_id = value.id
                if value_id not in values_map:
                    values_map[value_id] = value

        retrieved_values = list(values_map.values())

        value_detail = "、".join(
            f"{item.column_id}={item.value}" for item in retrieved_values
        ) or "无"
        emit_progress(
            writer,
            STEP,
            "success",
            stack=STACK,
            desc=DESC,
            detail=f"扩展关键词：{'、'.join(keywords) or '无'}\n命中取值：{value_detail}",
        )
        logger.info(f"召回字段取值：{list(values_map.keys())}")

        return {'retrieved_values': retrieved_values}
    except Exception as e:
        emit_progress(writer, STEP, "error", stack=STACK, desc=DESC)
        logger.error(f"召回字段取值失败: {str(e)}")
        raise
