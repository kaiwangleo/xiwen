from dataclasses import asdict

from elasticsearch import AsyncElasticsearch

from app.conf.app_config import app_config
from app.entities.value_info import ValueInfo


class ValueESRepository:
    index_mappings = {
        "dynamic": False,
        "properties": {
            "id": {"type": "keyword"},
            "value": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_max_word"},
            "column_id": {"type": "keyword"}
        }
    }

    def __init__(self, client: AsyncElasticsearch):
        self.client = client

    @property
    def index_name(self) -> str:
        return app_config.es.index_name

    async def reset_index(self):
        """删掉并重建取值索引。"""
        if await self.client.indices.exists(index=self.index_name):
            await self.client.indices.delete(index=self.index_name)
        await self.ensure_index()

    async def ensure_index(self):
        """索引不存在时按 IK 映射创建。"""
        if not await self.client.indices.exists(index=self.index_name):
            await self.client.indices.create(index=self.index_name, mappings=self.index_mappings)

    async def index(self, value_infos: list[ValueInfo], batch_size=20):
        """批量写入字段枚举取值。"""
        for i in range(0, len(value_infos), batch_size):
            batch = value_infos[i:i + batch_size]
            operations = []
            for value_info in batch:
                operations.append({"index": {"_index": self.index_name, "_id": value_info.id}})
                operations.append(asdict(value_info))
            await self.client.bulk(operations=operations)

    async def search(self, keyword: str, score_threshold: float = 0.6, limit: int = 5) -> list[ValueInfo]:
        """IK 分词检索字段取值。"""
        result = await self.client.search(index=self.index_name,
                                          query={
                                              "match": {
                                                  "value": keyword
                                              }
                                          },
                                          min_score=score_threshold,
                                          size=limit)
        return [ValueInfo(**hit['_source']) for hit in result['hits']['hits']]
