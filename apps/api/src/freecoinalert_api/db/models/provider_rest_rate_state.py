from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class ProviderRestRateState(Base):
    __tablename__ = "provider_rest_rate_state"
    __table_args__ = (
        CheckConstraint(
            "reserved_weight >= 0 AND provider_used_weight >= 0",
            name="ck_provider_rest_rate_state_weights_nonnegative",
        ),
        CheckConstraint(
            "provider_limit_weight IS NULL OR provider_limit_weight > 0",
            name="ck_provider_rest_rate_state_limit_positive",
        ),
        CheckConstraint(
            "blocked_reason IS NULL OR blocked_reason IN ('rate_limited', 'ip_banned')",
            name="ck_provider_rest_rate_state_block_reason",
        ),
    )

    provider_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reserved_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_used_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_limit_weight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
