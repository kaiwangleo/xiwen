from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.progress import emit_progress
from app.agent.state import DataAgentState, TableInfoState, MetricInfoState, ColumnInfoState
from app.core.log import logger

STEP = "合并召回信息"
STACK = ["MySQL meta"]
DESC = "把字段、取值、指标按表拼起来，并补上主外键"
from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo


async def merge_retrieved_info(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    emit_progress(writer, STEP, "running", stack=STACK, desc=DESC)

    # 已召回信息
    retrieved_columns = state["retrieved_columns"]
    retrieved_values = state["retrieved_values"]
    retrieved_metrics = state["retrieved_metrics"]

    # 获取所需依赖
    meta_mysql_repository = runtime.context["meta_mysql_repository"]

    retrieved_columns_map: dict[str, ColumnInfo] = {retrieved_column.id: retrieved_column for retrieved_column
                                                    in retrieved_columns}

    # 合并表格信息
    table_infos: list[TableInfoState] = []

    try:
        # 将指标信息的相关字段加入字段信息列表
        for retrieved_metric in retrieved_metrics:
            relevant_columns = retrieved_metric.relevant_columns
            for relevant_column in relevant_columns:
                if relevant_column not in retrieved_columns_map:
                    column_info = await meta_mysql_repository.get_column_info_by_id(relevant_column)
                    retrieved_columns_map[relevant_column] = column_info

        # 将字段取值合并到字段信息列表
        for retrieved_value in retrieved_values:
            column_id = retrieved_value.column_id
            column_value = retrieved_value.value
            #
            if column_id not in retrieved_columns_map:
                column_info = await meta_mysql_repository.get_column_info_by_id(column_id)
                retrieved_columns_map[column_id] = column_info
            if column_value not in retrieved_columns_map[column_id].examples:
                retrieved_columns_map[column_id].examples.append(column_value)

        # 按照字段所属的表id进行分组，得到table_id->columns映射
        table_to_columns_map: dict[str, list[ColumnInfo]] = {}
        for column in retrieved_columns_map.values():
            table_id = column.table_id
            if table_id not in table_to_columns_map:
                table_to_columns_map[table_id] = []
            table_to_columns_map[table_id].append(column)

        # 显式的添加每个表的主外键
        for table_id in table_to_columns_map.keys():
            # 查询主外键字段
            key_columns: list[ColumnInfo] = await meta_mysql_repository.get_key_columns_by_table_id(table_id)

            # 当前表已有的所有列的ID
            column_ids = [column.id for column in table_to_columns_map[table_id]]

            for key_column in key_columns:
                if key_column.id not in column_ids:
                    table_to_columns_map[table_id].append(key_column)

        # 将table_id->columns映射 转换为 list[TableInfoState]
        for table_id, columns in table_to_columns_map.items():
            table: TableInfo = await  meta_mysql_repository.get_table_info_by_id(table_id)
            columns = [
                ColumnInfoState(name=column.name, type=column.type, role=column.role, examples=column.examples,
                                description=column.description, alias=column.alias)
                for column in columns]
            table_info_state = TableInfoState(name=table.name,
                                              role=table.role,
                                              description=table.description,
                                              columns=columns)
            table_infos.append(table_info_state)

        # 处理指标信息
        metric_infos: list[MetricInfoState] = [
            MetricInfoState(name=metric_info.name, description=metric_info.description,
                            relevant_columns=metric_info.relevant_columns, alias=metric_info.alias)
            for metric_info in retrieved_metrics]

        table_names = [table_info["name"] for table_info in table_infos]
        metric_names = [metric_info["name"] for metric_info in metric_infos]
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
            detail=f"表：{table_detail}\n指标：{'、'.join(metric_names) or '无'}",
        )
        logger.info(
            f"合并召回信息: 表信息-{table_names},指标信息-{metric_names}")

        return {"table_infos": table_infos, "metric_infos": metric_infos}
    except Exception as e:
        emit_progress(writer, STEP, "error", stack=STACK, desc=DESC)
        logger.error(f"合并召回信息失败: {str(e)}")
        raise
