"""Stable server-sent event contracts exposed by ``POST /api/query``."""

from typing import Literal, NotRequired, TypedDict

type JsonValue = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)


class ProgressEvent(TypedDict):
    type: Literal["progress"]
    step: str
    status: Literal["running", "success", "error"]
    stack: NotRequired[list[str]]
    desc: NotRequired[str]
    detail: NotRequired[str]


class ResultEvent(TypedDict):
    type: Literal["result"]
    data: list[dict[str, JsonValue]]
    sql: str
    rowCount: int
    truncated: bool


class ErrorEvent(TypedDict):
    type: Literal["error"]
    code: str
    message: str


class ChatEvent(TypedDict):
    type: Literal["chat"]
    message: str


type SSEEvent = ProgressEvent | ResultEvent | ErrorEvent | ChatEvent
