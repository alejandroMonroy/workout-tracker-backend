from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

coach_tier_tag_association = Table(
    "coach_tier_tag_associations",
    Base.metadata,
    Column("tier_id", Integer, ForeignKey("coach_tiers.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("plan_tags.id", ondelete="CASCADE"), primary_key=True),
)


class CoachTier(Base):
    __tablename__ = "coach_tiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    xp_per_month: Mapped[int] = mapped_column(Integer)

    tags: Mapped[list["PlanTag"]] = relationship(secondary=coach_tier_tag_association)  # noqa: F821

    def __repr__(self) -> str:
        return f"<CoachTier {self.name}>"


class CoachSubscription(Base):
    __tablename__ = "coach_subscriptions"
    __table_args__ = (UniqueConstraint("coach_id", "athlete_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    xp_per_month: Mapped[int] = mapped_column(Integer)
    tier_id: Mapped[int | None] = mapped_column(
        ForeignKey("coach_tiers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    subscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tier: Mapped["CoachTier | None"] = relationship()

    def __repr__(self) -> str:
        return f"<CoachSubscription coach={self.coach_id} athlete={self.athlete_id}>"
