from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.models.column_info_mysql import ColumnInfoMySQL
from app.models.semantic_config_mysql import SemanticConfigMySQL
from app.models.table_info_mysql import TableInfoMySQL
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper

SEMANTIC_CONFIG_ID = "default"


class MetaMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def clear_tables_and_columns(self):
        """清空字段关联、字段、表快照（构建 save_tables 前调用）。"""
        await self.session.execute(text("DELETE FROM column_metric"))
        await self.session.execute(text("DELETE FROM column_info"))
        await self.session.execute(text("DELETE FROM table_info"))

    async def clear_metrics(self):
        """清空指标关联和指标快照。"""
        await self.session.execute(text("DELETE FROM column_metric"))
        await self.session.execute(text("DELETE FROM metric_info"))

    async def save_table_infos(self, table_infos: list[TableInfo]):
        """批量插入 table_info。"""
        models = [TableInfoMapper.to_model(table_info) for table_info in table_infos]
        self.session.add_all(models)

    async def save_column_infos(self, column_infos: list[ColumnInfo]):
        """批量插入 column_info。"""
        models = [ColumnInfoMapper.to_model(column_info) for column_info in column_infos]
        self.session.add_all(models)

    async def save_metric_infos(self, metric_infos: list[MetricInfo]):
        """批量插入 metric_info。"""
        self.session.add_all([MetricInfoMapper.to_model(metric_info) for metric_info in metric_infos])

    async def save_column_metrics(self, column_metrics: list[ColumnMetric]):
        """批量插入 column_metric。"""
        self.session.add_all([ColumnMetricMapper.to_model(column_metric) for column_metric in column_metrics])

    async def get_column_info_by_id(self, column_id: str) -> ColumnInfo | None:
        """按 id 取构建后字段快照。"""
        result: ColumnInfoMySQL | None = await self.session.get(ColumnInfoMySQL, column_id)
        if result:
            return ColumnInfoMapper.to_entity(result)
        return None

    async def get_table_info_by_id(self, table_id: str) -> TableInfo | None:
        """按 id 取构建后表快照。"""
        result: TableInfoMySQL | None = await self.session.get(TableInfoMySQL, table_id)
        if result:
            return TableInfoMapper.to_entity(result)
        return None

    async def get_semantic_config(self) -> dict | None:
        """读取 default 语义编辑稿，没有则 None。"""
        row = await self.session.get(SemanticConfigMySQL, SEMANTIC_CONFIG_ID)
        return dict(row.config) if row and row.config is not None else None

    async def save_semantic_config(self, config: dict) -> None:
        """写入 default 语义稿，JSON 原地替换需 flag_modified。"""
        row = await self.session.get(SemanticConfigMySQL, SEMANTIC_CONFIG_ID)
        now = datetime.now()
        if row:
            row.config = config
            row.updated_at = now
            flag_modified(row, "config")
        else:
            self.session.add(
                SemanticConfigMySQL(id=SEMANTIC_CONFIG_ID, config=config, updated_at=now)
            )

    async def get_key_columns_by_table_id(self, table_id: str) -> list[ColumnInfo]:
        """取表的主键/外键，供拼 join 上下文。"""
        sql = """
            select * 
            from column_info 
            where table_id = :table_id 
            and role in ('primary_key', 'foreign_key')
        """
        result = await self.session.execute(text(sql), {"table_id": table_id})
        return [ColumnInfo(**row) for row in result.mappings().fetchall()]
