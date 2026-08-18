"""ASGI request-body limit for the Xiwen query endpoint."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.conf.app_config import app_config


class RequestBodyTooLarge(Exception):
    """Raised while receiving a request body that exceeds the configured limit."""


class RequestBodyLimitMiddleware:
    """Reject oversized query bodies before FastAPI parses their JSON payload."""

    def __init__(self, app: ASGIApp, *, path: str = "/api/query") -> None:
        self.app = app
        self.path = path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") != self.path:
            await self.app(scope, receive, send)
            return

        max_bytes = app_config.api.max_request_bytes
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared_bytes = int(content_length)
            except ValueError:
                await self._reject(
                    scope,
                    receive,
                    send,
                    status_code=400,
                    code="INVALID_CONTENT_LENGTH",
                    message="Content-Length 请求头无效",
                )
                return
            if declared_bytes < 0:
                await self._reject(
                    scope,
                    receive,
                    send,
                    status_code=400,
                    code="INVALID_CONTENT_LENGTH",
                    message="Content-Length 请求头无效",
                )
                return
            if declared_bytes > max_bytes:
                await self._reject_too_large(scope, receive, send, max_bytes)
                return

        received_bytes = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > max_bytes:
                    raise RequestBodyTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except RequestBodyTooLarge:
            if response_started:
                raise
            await self._reject_too_large(scope, receive, send, max_bytes)

    @staticmethod
    async def _reject(
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        status_code: int,
        code: str,
        message: str,
    ) -> None:
        response = JSONResponse(
            status_code=status_code,
            content={"detail": message, "code": code},
        )
        await response(scope, receive, send)

    async def _reject_too_large(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        max_bytes: int,
    ) -> None:
        await self._reject(
            scope,
            receive,
            send,
            status_code=413,
            code="REQUEST_BODY_TOO_LARGE",
            message=f"请求体不能超过 {max_bytes} 字节",
        )
