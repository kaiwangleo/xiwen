import uuid

from app.clients.embedding_client_manager import LocalEmbeddingClient
from app.conf.app_config import app_config
from app.conf.meta_config import MetaConfig
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.semantic_service import load_meta_config, to_meta_config


class KnowledgeService:
    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        embedding_client: LocalEmbeddingClient,
        value_es_repository: ValueESRepository,
        metric_qdrant_repository: MetricQdrantRepository,
    ):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.embedding_client = embedding_client
        self.value_es_repository = value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository

    async def _save_tables_to_meta_db(
        self, meta_config: MetaConfig, example_limit: int = 10
    ) -> list[ColumnInfo]:
        """覆盖写入 table_info / column_info，并从数仓取样例。"""
        table_infos: list[TableInfo] = []
        column_infos: list[ColumnInfo] = []

        for table in meta_config.tables:
            table_info = TableInfo(
                id=table.name,
                name=table.name,
                role=table.role,
                description=table.description,
            )
            table_infos.append(table_info)

            column_types: dict[str, str] = await self.dw_mysql_repository.get_column_types(table.name)
            for column in table.columns:
                column_values: list = await self.dw_mysql_repository.get_column_values(
                    table.name, column.name, example_limit
                )
                column_info = ColumnInfo(
                    id=f"{table.name}.{column.name}",
                    name=column.name,
                    type=column_types[column.name],
                    role=column.role,
                    examples=column_values,
                    description=column.description,
                    alias=column.alias,
                    table_id=table.name,
                )
                column_infos.append(column_info)

        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.clear_tables_and_columns()
            await self.meta_mysql_repository.save_table_infos(table_infos)
            await self.meta_mysql_repository.save_column_infos(column_infos)

        return column_infos

    async def _save_column_info_to_qdrant(
        self, column_infos: list[ColumnInfo], batch_size: int = 10
    ):
        """重建字段向量集合，按名称/描述/别名各写一条。"""
        await self.column_qdrant_repository.reset_collection()
        points: list[dict] = []
        for column_info in column_infos:
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": column_info.name,
                    "payload": column_info,
                }
            )
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": column_info.description,
                    "payload": column_info,
                }
            )
            for alias in column_info.alias:
                points.append(
                    {"id": uuid.uuid4(), "embedding_text": alias, "payload": column_info}
                )
        embedding_texts = [point["embedding_text"] for point in points]
        embeddings = []
        for i in range(0, len(embedding_texts), batch_size):
            batch_embedding_texts = embedding_texts[i : i + batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(
                batch_embedding_texts
            )
            embeddings.extend(batch_embeddings)

        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]
        await self.column_qdrant_repository.upsert(ids, embeddings, payloads)

    async def _save_value_info_to_es(
        self,
        meta_config: MetaConfig,
        column_infos: list[ColumnInfo],
        value_limit: int = 100000,
    ):
        """重建取值索引，只同步 sync=true 的字段枚举。"""
        await self.value_es_repository.reset_index()

        column2sync: dict[str, bool] = {}
        for table in meta_config.tables:
            for column in table.columns:
                column2sync[f"{table.name}.{column.name}"] = column.sync

        value_infos: list[ValueInfo] = []
        for column_info in column_infos:
            sync = column2sync[column_info.id]
            if sync:
                table_name = column_info.table_id
                column_name = column_info.name
                values = await self.dw_mysql_repository.get_column_values(
                    table_name, column_name, value_limit
                )
                current_value_infos = [
                    ValueInfo(
                        id=f"{column_info.id}.{value}",
                        value=value,
                        column_id=column_info.id,
                    )
                    for value in values
                ]
                value_infos.extend(current_value_infos)
        await self.value_es_repository.index(value_infos)

    async def _save_metrics_to_meta_db(self, meta_config):
        """覆盖写入 metric_info / column_metric。"""
        metric_infos: list[MetricInfo] = []
        column_metrics: list[ColumnMetric] = []
        for metric in meta_config.metrics:
            metric_info = MetricInfo(
                id=metric.name,
                name=metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias,
            )
            metric_infos.append(metric_info)

            for relevant_column in metric.relevant_columns:
                column_metric = ColumnMetric(
                    column_id=relevant_column, metric_id=metric.name
                )
                column_metrics.append(column_metric)
        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.clear_metrics()
            await self.meta_mysql_repository.save_metric_infos(metric_infos)
            await self.meta_mysql_repository.save_column_metrics(column_metrics)

        return metric_infos

    async def _save_metric_info_to_qdrant(
        self, metric_infos: list[MetricInfo], batch_size: int = 10
    ):
        """重建指标向量集合，按名称/描述/别名各写一条。"""
        await self.metric_qdrant_repository.reset_collection()

        points: list[dict] = []
        for metric_info in metric_infos:
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": metric_info.name,
                    "payload": metric_info,
                }
            )
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": metric_info.description,
                    "payload": metric_info,
                }
            )
            for alias in metric_info.alias:
                points.append(
                    {"id": uuid.uuid4(), "embedding_text": alias, "payload": metric_info}
                )

        ids = [point["id"] for point in points]
        embeddings = []
        embedding_texts = [point["embedding_text"] for point in points]
        for i in range(0, len(embedding_texts), batch_size):
            batch_embedding_texts = embedding_texts[i : i + batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(
                batch_embedding_texts
            )
            embeddings.extend(batch_embeddings)
        payloads = [point["payload"] for point in points]
        await self.metric_qdrant_repository.upsert(ids, embeddings, payloads)

    async def build(self, emit=None):
        """按固定 6 步构建知识库，每步通过 emit 推 SSE（step/status/detail）。"""
        kb = app_config.knowledge_build
        ctx: dict = {
            "meta_config": None,
            "column_infos": None,
            "metric_infos": None,
        }

        async def notify(step_id: str, status: str, detail: str = ""):
            if emit:
                await emit({"step": step_id, "status": status, "detail": detail})

        async def run(step_id: str, fn):
            step_cfg = getattr(kb.steps, step_id)
            if not step_cfg.enabled:
                logger.info(f"SKIP {step_id}")
                await notify(step_id, "skipped", f"SKIP {step_id}")
                return
            try:
                await notify(step_id, "running")
                await fn(step_cfg)
            except Exception as exc:
                logger.exception(f"{step_id} 失败: {exc}")
                await notify(step_id, "error", str(exc))
                if kb.on_error == "continue":
                    return
                raise

        async def do_load_config(_cfg):
            data = await load_meta_config(self.meta_mysql_repository.session, seed=True)
            ctx["meta_config"] = to_meta_config(data)
            tables = len(data.get("tables") or [])
            metrics = len(data.get("metrics") or [])
            detail = f"从元数据库读取 {tables} 张表、{metrics} 个指标"
            logger.info(detail)
            await notify("load_config", "success", detail)

        async def do_save_tables(cfg):
            meta_config = ctx["meta_config"]
            if not meta_config or not meta_config.tables:
                logger.info("SKIP save_tables")
                await notify("save_tables", "skipped", "SKIP save_tables")
                return
            ctx["column_infos"] = await self._save_tables_to_meta_db(
                meta_config, cfg.example_limit
            )
            logger.info("保存表信息到meta数据库")
            await notify("save_tables", "success", "保存表信息到meta数据库")

        async def do_index_columns(cfg):
            column_infos = ctx["column_infos"]
            if not column_infos:
                logger.info("SKIP index_columns")
                await notify("index_columns", "skipped", "SKIP index_columns")
                return
            await self._save_column_info_to_qdrant(column_infos, cfg.batch_size)
            logger.info("为字段信息建立向量索引")
            await notify("index_columns", "success", "为字段信息建立向量索引")

        async def do_index_values(cfg):
            meta_config = ctx["meta_config"]
            column_infos = ctx["column_infos"]
            if not meta_config or not column_infos:
                logger.info("SKIP index_values")
                await notify("index_values", "skipped", "SKIP index_values")
                return
            await self._save_value_info_to_es(
                meta_config, column_infos, cfg.value_limit
            )
            logger.info("为字段取值建立全文索引")
            await notify("index_values", "success", "为字段取值建立全文索引")

        async def do_save_metrics(_cfg):
            meta_config = ctx["meta_config"]
            if not meta_config or not meta_config.metrics:
                logger.info("SKIP save_metrics")
                await notify("save_metrics", "skipped", "SKIP save_metrics")
                return
            ctx["metric_infos"] = await self._save_metrics_to_meta_db(meta_config)
            logger.info("保存指标信息到meta数据库")
            await notify("save_metrics", "success", "保存指标信息到meta数据库")

        async def do_index_metrics(cfg):
            metric_infos = ctx["metric_infos"]
            if not metric_infos:
                logger.info("SKIP index_metrics")
                await notify("index_metrics", "skipped", "SKIP index_metrics")
                return
            await self._save_metric_info_to_qdrant(metric_infos, cfg.batch_size)
            logger.info("为指标信息建立向量索引")
            await notify("index_metrics", "success", "为指标信息建立向量索引")

        await run("load_config", do_load_config)
        await run("save_tables", do_save_tables)
        await run("index_columns", do_index_columns)
        await run("index_values", do_index_values)
        await run("save_metrics", do_save_metrics)
        await run("index_metrics", do_index_metrics)
        logger.info("元数据知识库构建完成")
        if emit:
            await emit({"type": "done", "status": "success"})
