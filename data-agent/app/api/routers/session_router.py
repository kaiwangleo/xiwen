import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_meta_session
from app.api.schemas.session_schema import SessionCreate, SessionUpdate
from app.services.session_service import SessionService


session_router = APIRouter(prefix="/api/sessions")


def _svc(session: AsyncSession = Depends(get_meta_session)) -> SessionService:
    """按请求打开的元库会话构造 SessionService。"""
    return SessionService(session)


@session_router.get("")
async def list_sessions(svc: SessionService = Depends(_svc)):
    """列出会话摘要。"""
    return {"sessions": await svc.list_sessions()}


@session_router.post("")
async def create_session(payload: SessionCreate = SessionCreate(), svc: SessionService = Depends(_svc)):
    """新建空会话。"""
    return await svc.create_session(str(uuid.uuid4()), payload.title)


@session_router.get("/{session_id}")
async def get_session(session_id: str, svc: SessionService = Depends(_svc)):
    """取会话整包。"""
    data = await svc.get_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="会话不存在")
    return data


@session_router.put("/{session_id}")
async def put_session(session_id: str, payload: SessionUpdate, svc: SessionService = Depends(_svc)):
    """更新标题或整包覆盖轮次。"""
    data = await svc.save_session(session_id, payload.title, payload.turns)
    if not data:
        raise HTTPException(status_code=404, detail="会话不存在")
    return data


@session_router.delete("/{session_id}")
async def delete_session(session_id: str, svc: SessionService = Depends(_svc)):
    """删除会话。"""
    if not await svc.delete_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}
