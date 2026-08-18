from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.services.knowledge_service as knowledge_module
from app.services.knowledge_service import KnowledgeService


@pytest.mark.asyncio
async def test_build_closes_config_read_transaction_before_save_steps(monkeypatch):
    session = SimpleNamespace(commit=AsyncMock())
    repository = SimpleNamespace(session=session)
    disabled = SimpleNamespace(enabled=False)
    monkeypatch.setattr(
        knowledge_module.app_config,
        "knowledge_build",
        SimpleNamespace(
            on_error="abort",
            steps=SimpleNamespace(
                load_config=SimpleNamespace(enabled=True),
                save_tables=disabled,
                index_columns=disabled,
                index_values=disabled,
                save_metrics=disabled,
                index_metrics=disabled,
            ),
        ),
    )
    monkeypatch.setattr(
        knowledge_module,
        "load_meta_config",
        AsyncMock(return_value={"tables": [], "metrics": []}),
    )
    service = KnowledgeService(
        meta_mysql_repository=repository,
        dw_mysql_repository=None,
        column_qdrant_repository=None,
        embedding_client=None,
        value_es_repository=None,
        metric_qdrant_repository=None,
    )

    await service.build()

    session.commit.assert_awaited_once_with()
