from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("endpoints.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    authors_json: Mapped[str] = mapped_column(Text, default="[]")
    abstract: Mapped[str] = mapped_column(Text, default="")
    doi: Mapped[str] = mapped_column(String(255), default="")
    article_url: Mapped[str] = mapped_column(String(500), default="")
    year: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(20), default="")
    rights: Mapped[str] = mapped_column(String(255), default="")
    oai_identifier: Mapped[str] = mapped_column(String(255), index=True)
    datestamp: Mapped[str] = mapped_column(String(80), default="")
    set_spec_json: Mapped[str] = mapped_column(Text, default="[]")
    identifiers_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
