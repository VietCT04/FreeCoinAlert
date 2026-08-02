import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Identity, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class SignalFeedStreamEvent(Base):
    __tablename__ = "signal_feed_stream_events"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('signal_created', 'signal_invalidated')",
            name="ck_signal_feed_stream_events_kind",
        ),
        UniqueConstraint(
            "kind",
            "signal_event_id",
            name="uq_signal_feed_stream_events_kind_event",
        ),
        Index("ix_signal_feed_stream_events_created_at", "created_at"),
        Index("ix_signal_feed_stream_events_signal_event_id", "signal_event_id"),
    )

    sequence: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    signal_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("signal_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
