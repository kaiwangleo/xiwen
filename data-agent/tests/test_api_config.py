import pytest

from app.conf import app_config as app_config_module
from app.conf.app_config import APIConfig, app_config
from app.conf.paths import APP_CONFIG_EXAMPLE_PATH
from app.services.settings_service import config_as_dict


def test_api_config_has_safe_defaults() -> None:
    assert app_config.api.max_query_chars == 4000
    assert app_config.api.max_request_bytes == 16384
    assert app_config.api.query_timeout_seconds == 120
    assert app_config.api.sql_timeout_seconds == 30
    assert app_config.api.max_result_rows == 200
    assert app_config.api.health_timeout_seconds == 5
    assert app_config.api.auth_token == ""


def test_config_export_masks_api_auth_token() -> None:
    original = app_config.api.auth_token
    app_config.api.auth_token = "xiwen-secret-token"
    try:
        exported = config_as_dict(mask=True)
    finally:
        app_config.api.auth_token = original

    assert exported["api"]["auth_token"] == "****oken"


def test_api_config_rejects_non_positive_limits() -> None:
    with pytest.raises(ValueError, match="max_request_bytes"):
        APIConfig(max_request_bytes=0)


def test_example_config_loads_when_local_config_is_missing(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(app_config_module, "config_file", tmp_path / "missing.yaml")
    monkeypatch.setattr(
        app_config_module,
        "config_example_file",
        APP_CONFIG_EXAMPLE_PATH,
    )

    loaded = app_config_module.load_app_config()

    assert loaded.db_dw.user == "xiwen_readonly"
    assert loaded.api.sql_timeout_seconds == 30
    assert loaded.api.max_request_bytes == 16384
