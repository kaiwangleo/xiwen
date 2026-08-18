"""Redact configured credentials before errors enter logs or model context."""

from app.conf.app_config import app_config


def sanitize_error_message(error: BaseException, *, max_chars: int = 1000) -> str:
    """Return one bounded error message with configured credentials removed."""
    message = " ".join(str(error).splitlines())
    secrets = (
        app_config.db_meta.password,
        app_config.db_dw.password,
        app_config.llm.api_key,
        app_config.api.auth_token,
    )
    for secret in secrets:
        if secret:
            message = message.replace(secret, "***")
    return message[:max_chars]
