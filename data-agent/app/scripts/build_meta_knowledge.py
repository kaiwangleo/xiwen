import asyncio
from argparse import ArgumentParser
from pathlib import Path

from omegaconf import OmegaConf

from app.api.dependencies import build_knowledge_service
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.conf.meta_config import MetaConfig
from app.services.semantic_service import _as_dict, save_meta_config


async def build(config_path: Path | None):
    """可选导入 yaml 到 semantic_config，再跑 6 步构建。"""
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()

    async with (
        meta_mysql_client_manager.session_factory() as meta_session,
        dw_mysql_client_manager.session_factory() as dw_session,
    ):
        if config_path:
            context = OmegaConf.load(config_path)
            schema = OmegaConf.structured(MetaConfig)
            await save_meta_config(
                meta_session,
                _as_dict(OmegaConf.to_object(OmegaConf.merge(schema, context))),
            )
        service = build_knowledge_service(meta_session, dw_session)
        await service.build()

    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
    await qdrant_client_manager.close()
    await es_client_manager.close()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-c", "--conf", help="可选：把 yaml 导入元数据库后再构建")
    args = parser.parse_args()
    path = Path(args.conf) if args.conf else None
    asyncio.run(build(path))
