from app.api.auth import is_api_request_authorized


def test_api_auth_is_disabled_without_configured_token() -> None:
    assert is_api_request_authorized("/api/query", None, "") is True


def test_api_auth_allows_health_without_credentials() -> None:
    assert is_api_request_authorized("/api/health", None, "secret") is True


def test_api_auth_ignores_non_api_paths() -> None:
    assert is_api_request_authorized("/docs", None, "secret") is True


def test_api_auth_accepts_exact_bearer_token() -> None:
    assert is_api_request_authorized("/api/query", "Bearer secret", "secret") is True


def test_api_auth_rejects_missing_or_incorrect_token() -> None:
    assert is_api_request_authorized("/api/query", None, "secret") is False
    assert is_api_request_authorized("/api/query", "Basic secret", "secret") is False
    assert is_api_request_authorized("/api/query", "Bearer wrong", "secret") is False
