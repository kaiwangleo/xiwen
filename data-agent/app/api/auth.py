"""Optional bearer authentication for Xiwen HTTP APIs."""

from hmac import compare_digest


def is_api_request_authorized(
    path: str,
    authorization: str | None,
    configured_token: str,
) -> bool:
    """Return whether one request may pass the configured API token gate."""
    if not path.startswith("/api/") or path == "/api/health" or not configured_token:
        return True
    if authorization is None:
        return False

    scheme, separator, credential = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not credential:
        return False
    return compare_digest(credential, configured_token)
