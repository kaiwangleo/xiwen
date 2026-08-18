import asyncio
import json

import pytest
from fastapi import HTTPException

from app.api.routers import query_router as query_router_module
from app.api.routers.query_router import health
from app.api.routers.query_router import query as query_endpoint
from app.api.schemas.query_schema import QuerySchema
from app.conf.app_config import app_config


class FakeQueryService:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def query(self, query: str):
        self.queries.append(query)
        yield "data: {}\n\n"


class ConnectedRequest:
    async def receive(self) -> dict:
        await asyncio.Future()


class BlockingQueryService:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cleaned = asyncio.Event()

    async def query(self, _query: str):
        try:
            self.started.set()
            await asyncio.Future()
            yield "data: {}\n\n"
        finally:
            self.cleaned.set()


class DisconnectingRequest:
    def __init__(self, service: BlockingQueryService) -> None:
        self.service = service

    async def receive(self) -> dict:
        await self.service.started.wait()
        return {"type": "http.disconnect"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"status": "ok", "dependencies": {"mysql_dw": "ok"}}, 200),
        ({"status": "degraded", "dependencies": {"mysql_dw": "unavailable"}}, 503),
    ],
)
async def test_health_endpoint_maps_readiness_to_http_status(
    monkeypatch,
    payload: dict,
    expected_status: int,
) -> None:
    async def fake_health() -> dict:
        return payload

    monkeypatch.setattr(query_router_module, "check_health", fake_health)

    response = await health()

    assert response.status_code == expected_status
    assert json.loads(response.body) == payload


@pytest.mark.asyncio
async def test_query_endpoint_rejects_blank_query() -> None:
    with pytest.raises(HTTPException) as exc:
        await query_endpoint(
            ConnectedRequest(), QuerySchema(query="   "), FakeQueryService()
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_query_endpoint_rejects_oversized_query(monkeypatch) -> None:
    monkeypatch.setattr(app_config.api, "max_query_chars", 5)

    with pytest.raises(HTTPException) as exc:
        await query_endpoint(
            ConnectedRequest(), QuerySchema(query="123456"), FakeQueryService()
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_query_endpoint_trims_query(monkeypatch) -> None:
    service = FakeQueryService()
    monkeypatch.setattr(app_config.api, "max_query_chars", 100)

    response = await query_endpoint(
        ConnectedRequest(), QuerySchema(query="  统计销售额  "), service
    )
    chunks = [chunk async for chunk in response.body_iterator]

    assert service.queries == ["统计销售额"]
    assert chunks == ["data: {}\n\n"]
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"


@pytest.mark.asyncio
async def test_query_endpoint_cancels_service_on_disconnect(monkeypatch) -> None:
    service = BlockingQueryService()
    monkeypatch.setattr(app_config.api, "max_query_chars", 100)

    response = await query_endpoint(
        DisconnectingRequest(service), QuerySchema(query="统计销售额"), service
    )
    chunks = [chunk async for chunk in response.body_iterator]

    assert chunks == []
    assert service.cleaned.is_set()
