from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    workouts: Mapped[list["PlanWorkout"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="PlanWorkout.order"
    )

    def __repr__(self) -> str:
        return f"<Plan {self.name}>"


class PlanWorkout(Base):
    __tablename__ = "plan_workouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"))
    template_id: Mapped[int] = mapped_column(
        ForeignKey("workout_templates.id", ondelete="CASCADE")
    )
    order: Mapped[int] = mapped_column(Integer, default=0)
    day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan: Mapped["Plan"] = relationship(back_populates="workouts")
    template: Mapped["WorkoutTemplate"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<PlanWorkout plan={self.plan_id} order={self.order}>"


class PlanSubscription(Base):
    __tablename__ = "plan_subscriptions"
    __table_args__ = (UniqueConstraint("plan_id", "athlete_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"))
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    plan: Mapped["Plan"] = relationship()

    def __repr__(self) -> str:
        return f"<PlanSubscription plan={self.plan_id} athlete={self.athlete_id}>"
