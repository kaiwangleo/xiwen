import uuid

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from app.api.auth import is_api_request_authorized
from app.api.body_limit import RequestBodyLimitMiddleware
from app.api.routers.admin_router import admin_router
from app.api.routers.query_router import query_router
from app.api.routers.session_router import session_router
from app.conf.app_config import app_config
from app.core.context import request_id_ctx_var
from app.core.lifespan import lifespan

# 创建FastAPI应用，并注册生命周期函数
app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestBodyLimitMiddleware)

# 注册路由
app.include_router(query_router)
app.include_router(admin_router)
app.include_router(session_router)


@app.middleware("http")
async def enforce_api_auth(request: Request, call_next):
    """Protect all non-health APIs when api.auth_token is configured."""
    if not is_api_request_authorized(
        request.url.path,
        request.headers.get("authorization"),
        app_config.api.auth_token,
    ):
        return JSONResponse(
            status_code=401,
            content={"detail": "无效或缺失的 API Token", "code": "UNAUTHORIZED"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await call_next(request)


@app.middleware("http")
async def bind_request_id(request: Request, call_next):
    """为每个请求写入 request_id，供日志关联。"""
    request_id_ctx_var.set(uuid.uuid4())
    return await call_next(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
