from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.progress import emit_progress
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.metric_info import MetricInfo
from app.prompt.prompt_loader import load_prompt

STEP = "召回指标"
STACK = ["LLM", "Embedding", "Qdrant"]
DESC = "大模型扩展关键词，Embedding 后检索 Qdrant 指标集合"


async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    emit_progress(writer, STEP, "running", stack=STACK, desc=DESC)

    query = state["query"]
    keywords = state["keywords"]

    embedding_client = runtime.context['embedding_client']
    metric_qdrant_repository = runtime.context['metric_qdrant_repository']

    try:
        # 使用LLM扩展关键词
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_metric_recall"), input_variables=["query"])
        output_parser = JsonOutputParser()

        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"query": query})

        # 使用扩展后的关键词召回指标信息
        retrieved_metrics_map: dict[str, MetricInfo] = {}

        keywords = list(set(keywords + result))
        logger.info(f"召回指标信息扩展关键词：{keywords}")
        for keyword in keywords:
            embedding = await embedding_client.aembed_query(keyword)
            payloads: list[MetricInfo] = await metric_qdrant_repository.search(embedding)
            for payload in payloads:
                metric_id = payload.id
                if metric_id not in retrieved_metrics_map:
                    retrieved_metrics_map[metric_id] = payload

        retrieved_metrics = list(retrieved_metrics_map.values())

        emit_progress(
            writer,
            STEP,
            "success",
            stack=STACK,
            desc=DESC,
            detail=(
                f"扩展关键词：{'、'.join(keywords) or '无'}\n"
                f"命中指标：{'、'.join(retrieved_metrics_map.keys()) or '无'}"
            ),
        )
        logger.info(f"召回指标信息：{list(retrieved_metrics_map.keys())}")
        return {"retrieved_metrics": retrieved_metrics}
    except Exception as e:
        emit_progress(writer, STEP, "error", stack=STACK, desc=DESC)
        logger.error(f"召回指标信息失败: {str(e)}")
        raise
