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

STEP = "过滤指标"
STACK = ["LLM"]
DESC = "大模型按问题从召回指标里筛出真正要用的"


async def filter_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    emit_progress(writer, STEP, "running", stack=STACK, desc=DESC)

    query = state["query"]
    metric_infos = state["metric_infos"]
    try:
        # 用LLM过滤表信息
        prompt = PromptTemplate(template=load_prompt("filter_metric_info"), input_variables=["query", "metric_infos"])
        output_parser = JsonOutputParser()

        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {"query": query, "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False)})

        # 利用模型输出过滤metric_infos
        for metric_info in metric_infos[:]:
            if metric_info["name"] not in result:
                metric_infos.remove(metric_info)

        emit_progress(
            writer,
            STEP,
            "success",
            stack=STACK,
            desc=DESC,
            detail="、".join(metric_info["name"] for metric_info in metric_infos) or "无",
        )
        logger.info(f"过滤后的指标: {[metric_info['name'] for metric_info in metric_infos]}")
        return {"metric_infos": metric_infos}
    except Exception as e:
        emit_progress(writer, STEP, "error", stack=STACK, desc=DESC)
        logger.error(f"过滤指标失败:{str(e)}")
        raise
