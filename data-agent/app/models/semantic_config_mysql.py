from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base


class SemanticConfigMySQL(Base):
    __tablename__ = "semantic_config"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="配置编号")
    config: Mapped[dict] = mapped_column(JSON, nullable=False, comment="语义配置")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="更新时间")
