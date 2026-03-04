from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Endpoint(Base):
    __tablename__ = "endpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    journal_name: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(80), default="Uncategorized")
    oai_url: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    repository_name: Mapped[str] = mapped_column(String(255), default="")
    metadata_prefix: Mapped[str] = mapped_column(String(50), default="oai_dc")
    admin_email: Mapped[str] = mapped_column(String(255), default="")
    metadata_formats_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
