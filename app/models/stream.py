from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Stream(Base):
    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    keitaro_stream_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=1)
    schema: Mapped[str] = mapped_column(String(50), default="landings")  # "redirect" or "landings"
    action_type: Mapped[str] = mapped_column(String(50), default="http")
    action_options: Mapped[str] = mapped_column(Text, nullable=True)     # JSON string
    filters: Mapped[str] = mapped_column(Text, nullable=True)            # JSON string
    is_dirty: Mapped[bool] = mapped_column(Boolean, default=False)       # True if unpublished changes exist

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    campaign = relationship("Campaign", back_populates="streams")
    offers = relationship("StreamOffer", back_populates="stream", cascade="all, delete-orphan", lazy="selectin")
