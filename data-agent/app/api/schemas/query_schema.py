from pydantic import BaseModel


class QuerySchema(BaseModel):
    """问数请求体。"""
    query: str
