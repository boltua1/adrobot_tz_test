from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class StreamOffer(Base):
    __tablename__ = "stream_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stream_id: Mapped[int] = mapped_column(Integer, ForeignKey("streams.id", ondelete="CASCADE"), index=True)
    keitaro_offer_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=True)
    share: Mapped[int] = mapped_column(Integer, default=100)            # 0 to 100 percentage
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)      # Fixed weight
    is_removed: Mapped[bool] = mapped_column(Boolean, default=False)     # Soft-deleted / grayed out
    is_new: Mapped[bool] = mapped_column(Boolean, default=False)         # Added locally, revertible on cancel

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    stream = relationship("Stream", back_populates="offers")
