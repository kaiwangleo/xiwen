from dataclasses import asdict

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from app.conf.app_config import app_config
from app.entities.column_info import ColumnInfo


class ColumnQdrantRepository:
    def __init__(self, client: AsyncQdrantClient):
        self.client = client

    @property
    def collection_name(self) -> str:
        return app_config.qdrant.collections.column

    async def reset_collection(self):
        """删掉并重建字段向量集合。"""
        if await self.client.collection_exists(self.collection_name):
            await self.client.delete_collection(self.collection_name)
        await self.ensure_collection()

    async def ensure_collection(self):
        """集合不存在时按当前向量维度创建。"""
        if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(self.collection_name,
                                                vectors_config=VectorParams(size=app_config.qdrant.embedding_size,
                                                                            distance=Distance.COSINE))

    async def upsert(self, ids: list[str], embeddings: list[list[float]], payloads: list[ColumnInfo],
                     batch_size: int = 20):
        """批量写入字段向量点。"""
        zipped = list(zip(ids, embeddings, payloads))
        for i in range(0, len(zipped), batch_size):
            batch = zipped[i:i + batch_size]
            batch_points = [PointStruct(id=id, vector=embedding, payload=asdict(payload)) for id, embedding, payload in
                            batch]
            await self.client.upsert(collection_name=self.collection_name, points=batch_points)

    async def search(
        self,
        embedding: list[float],
        score_threshold: float | None = None,
        limit: int | None = None,
    ) -> list[ColumnInfo]:
        """按向量召回字段快照。"""
        search = app_config.qdrant.search
        result = await self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            score_threshold=search.score_threshold if score_threshold is None else score_threshold,
            limit=search.limit if limit is None else limit,
        )
        return [ColumnInfo(**point.payload) for point in result.points]
