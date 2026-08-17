import asyncio
import json

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
from starlette.responses import FileResponse, StreamingResponse

from app.api.dependencies import build_knowledge_service
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.conf.app_config import config_file
from app.core.runtime import apply_runtime_changes
from app.prompt.prompt_loader import (
    get_prompt_meta,
    load_manifest,
    load_prompt,
    reset_prompt,
    save_prompt,
)
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.services.semantic_service import load_meta_config, save_meta_config
from app.services.settings_service import config_as_dict, knowledge_warnings, save_config


admin_router = APIRouter(prefix="/api/admin")
_build_lock = asyncio.Lock()


class PromptUpdate(BaseModel):
    content: str


@admin_router.get("/config")
async def get_config():
    """返回打码后的运行时配置和知识构建开关告警。"""
    return {
        "config": config_as_dict(mask=True),
        "warnings": knowledge_warnings(),
    }


@admin_router.put("/config")
async def put_config(payload: dict = Body(...)):
    """保存 YAML 并热加载连接器。"""
    result = save_config(payload)
    runtime = await apply_runtime_changes(result.pop("previous"), result.pop("applied"))
    warnings = list(result.get("warnings") or [])
    warnings.extend(runtime.get("runtime_warnings") or [])
    result.update(runtime)
    result["warnings"] = warnings
    return result


@admin_router.get("/config.yaml")
async def export_config_yaml():
    """下载当前 app_config.yaml。"""
    return FileResponse(
        config_file,
        media_type="application/yaml",
        filename="app_config.yaml",
    )


@admin_router.get("/datasource/tables")
async def list_datasource_tables():
    """读取数仓 information_schema，供语义勾选。"""
    try:
        async with dw_mysql_client_manager.session_factory() as session:
            tables = await DWMySQLRepository(session).list_schema()
        return {"database": dw_mysql_client_manager.db_config.database, "tables": tables}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"读取数据源表失败: {exc}") from exc


@admin_router.get("/meta-config")
async def get_meta_config():
    """读取语义编辑稿（空库会 seed yaml）。"""
    async with meta_mysql_client_manager.session_factory() as session:
        return {"config": await load_meta_config(session)}


@admin_router.put("/meta-config")
async def put_meta_config(payload: dict = Body(...)):
    """校验数仓表结构后写入 semantic_config，不自动构建。"""
    try:
        async with dw_mysql_client_manager.session_factory() as dw_session:
            schema = await DWMySQLRepository(dw_session).list_schema()
        async with meta_mysql_client_manager.session_factory() as session:
            return await save_meta_config(session, payload, schema=schema)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"校验数据源表失败: {exc}") from exc


@admin_router.get("/prompts")
async def list_prompts():
    """列出全部提示词及内容。"""
    items = []
    for meta in load_manifest():
        items.append({**meta, "content": load_prompt(meta["id"])})
    return {"prompts": items}


@admin_router.get("/prompts/{prompt_id}")
async def get_prompt(prompt_id: str):
    """读取单条提示词。"""
    meta = get_prompt_meta(prompt_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"未知提示词: {prompt_id}")
    return {**meta, "content": load_prompt(prompt_id)}


@admin_router.put("/prompts/{prompt_id}")
async def put_prompt(prompt_id: str, body: PromptUpdate):
    """覆盖写入提示词文件。"""
    if not get_prompt_meta(prompt_id):
        raise HTTPException(status_code=404, detail=f"未知提示词: {prompt_id}")
    save_prompt(prompt_id, body.content)
    return {**get_prompt_meta(prompt_id), "content": load_prompt(prompt_id)}


@admin_router.post("/prompts/{prompt_id}/reset")
async def reset_prompt_api(prompt_id: str):
    """从 defaults 恢复提示词。"""
    if not get_prompt_meta(prompt_id):
        raise HTTPException(status_code=404, detail=f"未知提示词: {prompt_id}")
    content = reset_prompt(prompt_id)
    return {**get_prompt_meta(prompt_id), "content": content}


@admin_router.post("/knowledge/build")
async def build_knowledge():
    """后台跑 6 步构建，SSE 推送进度；会话在 runner 内打开。"""
    if _build_lock.locked():
        raise HTTPException(status_code=409, detail="知识库正在构建")

    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: dict):
        await queue.put(event)

    async def runner():
        async with _build_lock:
            try:
                async with (
                    meta_mysql_client_manager.session_factory() as meta_session,
                    dw_mysql_client_manager.session_factory() as dw_session,
                ):
                    service = build_knowledge_service(meta_session, dw_session)
                    await service.build(emit=emit)
            except Exception as exc:
                await queue.put({"type": "error", "message": str(exc)})
            finally:
                await queue.put(None)

    async def stream():
        task = asyncio.create_task(runner())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            await task

    return StreamingResponse(stream(), media_type="text/event-stream; charset=utf-8")
