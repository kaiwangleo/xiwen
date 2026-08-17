import uuid

from fastapi import FastAPI, Request

from app.api.routers.admin_router import admin_router
from app.api.routers.query_router import query_router
from app.api.routers.session_router import session_router
from app.core.context import request_id_ctx_var
from app.core.lifespan import lifespan

# 创建FastAPI应用，并注册生命周期函数
app = FastAPI(lifespan=lifespan) 

# 注册路由
app.include_router(query_router)
app.include_router(admin_router)
app.include_router(session_router)


@app.middleware("http")
async def bind_request_id(request: Request, call_next):
    """为每个请求写入 request_id，供日志关联。"""
    request_id_ctx_var.set(uuid.uuid4())
    return await call_next(request)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
