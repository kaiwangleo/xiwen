from datetime import datetime

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_session_mysql import ChatSessionMySQL
from app.models.chat_turn_mysql import ChatTurnMySQL

ENSURE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS chat_session (
        id         VARCHAR(64)  NOT NULL,
        title      VARCHAR(255) NOT NULL DEFAULT '新会话',
        created_at DATETIME     NOT NULL,
        updated_at DATETIME     NOT NULL,
        PRIMARY KEY (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_turn (
        id         VARCHAR(64)  NOT NULL,
        session_id VARCHAR(64)  NOT NULL,
        seq        INT          NOT NULL DEFAULT 0,
        query      TEXT         NOT NULL,
        kind       VARCHAR(16)  NOT NULL DEFAULT 'query',
        local_text TEXT         NULL,
        steps      JSON         NULL,
        result     JSON         NULL,
        error      TEXT         NULL,
        status     VARCHAR(16)  NOT NULL DEFAULT 'success',
        created_at DATETIME     NOT NULL,
        PRIMARY KEY (id),
        KEY idx_turn_session (session_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]


async def ensure_session_tables(engine) -> None:
    """启动时确保 chat_session / chat_turn 存在。"""
    async with engine.begin() as conn:
        for stmt in ENSURE_SQL:
            await conn.execute(text(stmt))


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_rows(self) -> tuple[list[ChatSessionMySQL], dict[str, int]]:
        """按更新时间倒序列出会话，并统计每会话轮次。"""
        count_stmt = (
            select(ChatTurnMySQL.session_id, func.count().label("n"))
            .group_by(ChatTurnMySQL.session_id)
        )
        counts = {row.session_id: row.n for row in (await self.session.execute(count_stmt)).all()}
        rows = (
            await self.session.execute(
                select(ChatSessionMySQL).order_by(ChatSessionMySQL.updated_at.desc())
            )
        ).scalars().all()
        return list(rows), counts

    async def get_row(self, session_id: str) -> ChatSessionMySQL | None:
        """按 id 取会话行。"""
        return await self.session.get(ChatSessionMySQL, session_id)

    async def list_turns(self, session_id: str) -> list[ChatTurnMySQL]:
        """按序号取会话全部轮次。"""
        return list(
            (
                await self.session.execute(
                    select(ChatTurnMySQL)
                    .where(ChatTurnMySQL.session_id == session_id)
                    .order_by(ChatTurnMySQL.seq.asc(), ChatTurnMySQL.created_at.asc())
                )
            ).scalars().all()
        )

    async def add_session(self, session_id: str, title: str) -> ChatSessionMySQL:
        """插入空会话并提交。"""
        now = datetime.now()
        row = ChatSessionMySQL(
            id=session_id, title=title[:255] or "新会话", created_at=now, updated_at=now
        )
        self.session.add(row)
        await self.session.commit()
        return row

    async def replace_turns(self, session_id: str, turns: list[dict]) -> None:
        """整包覆盖会话轮次，不提交。"""
        await self.session.execute(delete(ChatTurnMySQL).where(ChatTurnMySQL.session_id == session_id))
        now = datetime.now()
        for idx, item in enumerate(turns):
            self.session.add(
                ChatTurnMySQL(
                    id=item["id"],
                    session_id=session_id,
                    seq=idx,
                    query=item.get("query") or "",
                    kind=item.get("kind") or "query",
                    local_text=item.get("localText") or None,
                    steps=item.get("steps") or [],
                    result=item.get("result"),
                    error=item.get("error"),
                    status=item.get("status") or "success",
                    created_at=now,
                )
            )

    async def delete(self, row: ChatSessionMySQL) -> None:
        """删会话及其轮次并提交。"""
        await self.session.execute(delete(ChatTurnMySQL).where(ChatTurnMySQL.session_id == row.id))
        await self.session.delete(row)
        await self.session.commit()
