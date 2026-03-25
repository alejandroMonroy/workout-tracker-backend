import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CoachSubscriptionStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CoachSubscription(Base):
    __tablename__ = "coach_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[CoachSubscriptionStatus] = mapped_column(
        Enum(CoachSubscriptionStatus, values_callable=lambda x: [e.value for e in x]),
        default=CoachSubscriptionStatus.PENDING,
    )
    initiated_by: Mapped[str] = mapped_column(
        String(10), default="athlete", server_default="athlete"
    )
    xp_per_month: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<CoachSubscription coach={self.coach_id} athlete={self.athlete_id}>"
