from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker

from app.conf.app_config import DBConfig, app_config


class MySQLClientManager:
    def __init__(self, db_config: DBConfig):
        self.db_config = db_config
        self.engine: Optional[AsyncEngine] = None
        self.session_factory = None

    def _get_url(self):
        """拼 asyncmy 连接串。"""
        return (
            f"mysql+asyncmy://{self.db_config.user}:{self.db_config.password}"
            f"@{self.db_config.host}:{self.db_config.port}/{self.db_config.database}?charset=utf8mb4"
        )

    def init(self):
        """创建引擎和 session 工厂，启动或热加载时调用。"""
        self.engine = create_async_engine(
            url=self._get_url(),
            pool_size=10,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            autoflush=True,
            expire_on_commit=False,
            autobegin=True,
        )

    async def close(self):
        """释放连接池。"""
        if self.engine:
            await self.engine.dispose()

    async def reload(self):
        """按当前 db_config 重建引擎，再关掉旧池。"""
        old = self.engine
        self.init()
        if old:
            await old.dispose()


dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)
meta_mysql_client_manager = MySQLClientManager(app_config.db_meta)
