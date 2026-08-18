import json

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.api.body_limit import RequestBodyLimitMiddleware
from app.conf.app_config import app_config


def http_scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/query",
        "raw_path": b"/api/query",
        "query_string": b"",
        "headers": headers or [],
        "client": None,
        "server": None,
    }


async def call_middleware(
    incoming: list[dict],
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[bool, list[dict]]:
    app_called = False
    sent: list[dict] = []
    messages = iter(incoming)

    async def receive() -> dict:
        return next(messages)

    async def send(message: dict) -> None:
        sent.append(message)

    async def app(scope, receive, send) -> None:
        nonlocal app_called
        app_called = True
        while True:
            message = await receive()
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestBodyLimitMiddleware(app)
    await middleware(http_scope(headers), receive, send)
    return app_called, sent


@pytest.mark.asyncio
async def test_body_limit_rejects_declared_oversized_request(monkeypatch) -> None:
    monkeypatch.setattr(app_config.api, "max_request_bytes", 4)

    app_called, sent = await call_middleware(
        [{"type": "http.request", "body": b"12345", "more_body": False}],
        headers=[(b"content-length", b"5")],
    )

    assert app_called is False
    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"])["code"] == "REQUEST_BODY_TOO_LARGE"


@pytest.mark.asyncio
async def test_body_limit_rejects_oversized_chunked_request(monkeypatch) -> None:
    monkeypatch.setattr(app_config.api, "max_request_bytes", 4)

    app_called, sent = await call_middleware(
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"45", "more_body": False},
        ]
    )

    assert app_called is True
    assert sent[0]["status"] == 413


@pytest.mark.asyncio
async def test_body_limit_allows_request_at_limit(monkeypatch) -> None:
    monkeypatch.setattr(app_config.api, "max_request_bytes", 4)

    app_called, sent = await call_middleware(
        [{"type": "http.request", "body": b"1234", "more_body": False}],
        headers=[(b"content-length", b"4")],
    )

    assert app_called is True
    assert sent[0]["status"] == 204


@pytest.mark.asyncio
async def test_body_limit_wraps_starlette_request_parsing(monkeypatch) -> None:
    monkeypatch.setattr(app_config.api, "max_request_bytes", 4)

    async def endpoint(request: Request) -> JSONResponse:
        await request.body()
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/api/query", endpoint, methods=["POST"])])
    app.add_middleware(RequestBodyLimitMiddleware)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/query", content=b"12345")

    assert response.status_code == 413
    assert response.json()["code"] == "REQUEST_BODY_TOO_LARGE"
