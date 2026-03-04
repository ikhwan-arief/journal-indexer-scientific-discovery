from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JournalProfile(Base):
    __tablename__ = "journal_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("endpoints.id", ondelete="CASCADE"), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(80), default="Uncategorized")
    accreditation_rank: Mapped[str] = mapped_column(String(50), default="Unaccredited")
    indexes_json: Mapped[str] = mapped_column(Text, default="[]")
    publisher: Mapped[str] = mapped_column(String(255), default="")
    issn: Mapped[str] = mapped_column(String(50), default="")
    is_deleted: Mapped[str] = mapped_column(String(8), default="false")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
