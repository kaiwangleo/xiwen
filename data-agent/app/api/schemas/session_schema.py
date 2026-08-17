from pydantic import BaseModel


class SessionCreate(BaseModel):
    title: str = "新会话"


class SessionUpdate(BaseModel):
    title: str | None = None
    turns: list[dict] | None = None
