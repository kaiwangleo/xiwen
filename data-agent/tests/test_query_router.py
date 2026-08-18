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
        await query_endpoint(QuerySchema(query="   "), FakeQueryService())

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_query_endpoint_rejects_oversized_query(monkeypatch) -> None:
    monkeypatch.setattr(app_config.api, "max_query_chars", 5)

    with pytest.raises(HTTPException) as exc:
        await query_endpoint(QuerySchema(query="123456"), FakeQueryService())

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_query_endpoint_trims_query(monkeypatch) -> None:
    service = FakeQueryService()
    monkeypatch.setattr(app_config.api, "max_query_chars", 100)

    response = await query_endpoint(QuerySchema(query="  统计销售额  "), service)
    chunks = [chunk async for chunk in response.body_iterator]

    assert service.queries == ["统计销售额"]
    assert chunks == ["data: {}\n\n"]
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
