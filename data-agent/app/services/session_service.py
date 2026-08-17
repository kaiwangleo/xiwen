from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_session_mysql import ChatSessionMySQL
from app.models.chat_turn_mysql import ChatTurnMySQL
from app.repositories.mysql.session_repository import SessionRepository, ensure_session_tables

__all__ = ["SessionService", "ensure_session_tables"]


def _turn_out(row: ChatTurnMySQL) -> dict:
    """ORM 轮次转前端字段（localText）。"""
    return {
        "id": row.id,
        "query": row.query,
        "kind": row.kind,
        "localText": row.local_text or "",
        "steps": row.steps or [],
        "result": row.result,
        "error": row.error,
        "status": row.status,
    }


def _session_out(
    row: ChatSessionMySQL, turns: list[ChatTurnMySQL] | None = None, turn_count: int | None = None
) -> dict:
    """ORM 会话转 API 结构。"""
    data = {
        "id": row.id,
        "title": row.title,
        "created_at": row.created_at.isoformat(sep=" ", timespec="seconds"),
        "updated_at": row.updated_at.isoformat(sep=" ", timespec="seconds"),
        "turn_count": turn_count if turn_count is not None else (len(turns) if turns is not None else 0),
    }
    if turns is not None:
        data["turns"] = [_turn_out(item) for item in turns]
    return data


class SessionService:
    def __init__(self, session: AsyncSession):
        self.repo = SessionRepository(session)
        self.session = session

    async def list_sessions(self) -> list[dict]:
        """列出全部会话摘要，按更新时间倒序。"""
        rows, counts = await self.repo.list_rows()
        return [_session_out(row, turn_count=counts.get(row.id, 0)) for row in rows]

    async def get_session(self, session_id: str) -> dict | None:
        """取会话整包（含 turns），不存在返回 None。"""
        row = await self.repo.get_row(session_id)
        if not row:
            return None
        turns = await self.repo.list_turns(session_id)
        return _session_out(row, turns=turns)

    async def create_session(self, session_id: str, title: str) -> dict:
        """新建空会话并落库。"""
        row = await self.repo.add_session(session_id, title)
        return _session_out(row, turns=[], turn_count=0)

    async def save_session(self, session_id: str, title: str | None, turns: list[dict] | None) -> dict | None:
        """更新标题和/或整包覆盖轮次；会话不存在返回 None。"""
        row = await self.repo.get_row(session_id)
        if not row:
            return None
        if title:
            row.title = title[:255]
        elif turns:
            row.title = str(turns[0].get("query") or row.title)[:255]
        row.updated_at = datetime.now()
        if turns is None:
            await self.session.commit()
            return await self.get_session(session_id)
        await self.repo.replace_turns(session_id, turns)
        await self.session.commit()
        return await self.get_session(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """删除会话及轮次，不存在返回 False。"""
        row = await self.repo.get_row(session_id)
        if not row:
            return False
        await self.repo.delete(row)
        return True
