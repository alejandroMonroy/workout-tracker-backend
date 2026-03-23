import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.template import WorkoutModality


class BlockType(str, enum.Enum):
    WARMUP = "warmup"
    SKILL = "skill"
    STRENGTH = "strength"
    WOD = "wod"
    CARDIO = "cardio"
    COOLDOWN = "cooldown"
    OTHER = "other"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


# ── Plan ──────────────────────────────────────────────


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    creator: Mapped["User"] = relationship(  # noqa: F821
        foreign_keys=[created_by], back_populates="created_plans"
    )
    sessions: Mapped[list["PlanSession"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanSession.day_number",
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Plan {self.name}>"


# ── PlanSession ───────────────────────────────────────


class PlanSession(Base):
    __tablename__ = "plan_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    day_number: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    plan: Mapped["Plan"] = relationship(back_populates="sessions")
    blocks: Mapped[list["SessionBlock"]] = relationship(
        back_populates="plan_session",
        cascade="all, delete-orphan",
        order_by="SessionBlock.order",
    )

    def __repr__(self) -> str:
        return f"<PlanSession {self.name} day={self.day_number}>"


# ── SessionBlock ──────────────────────────────────────


class SessionBlock(Base):
    __tablename__ = "session_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_session_id: Mapped[int] = mapped_column(
        ForeignKey("plan_sessions.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    block_type: Mapped[BlockType] = mapped_column(
        Enum(BlockType), default=BlockType.OTHER
    )
    modality: Mapped[WorkoutModality | None] = mapped_column(
        Enum(WorkoutModality), nullable=True
    )
    rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_cap_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    plan_session: Mapped["PlanSession"] = relationship(back_populates="blocks")
    exercises: Mapped[list["BlockExercise"]] = relationship(
        back_populates="block",
        cascade="all, delete-orphan",
        order_by="BlockExercise.order",
    )

    def __repr__(self) -> str:
        return f"<SessionBlock {self.name} type={self.block_type}>"


# ── BlockExercise ─────────────────────────────────────


class BlockExercise(Base):
    __tablename__ = "block_exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(
        ForeignKey("session_blocks.id", ondelete="CASCADE")
    )
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    order: Mapped[int] = mapped_column(Integer, default=0)
    target_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    block: Mapped["SessionBlock"] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<BlockExercise block={self.block_id} order={self.order}>"


# ── Subscription ──────────────────────────────────────


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE")
    )
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE
    )
    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")
    athlete: Mapped["User"] = relationship(  # noqa: F821
        foreign_keys=[athlete_id], back_populates="subscriptions"
    )

    def __repr__(self) -> str:
        return f"<Subscription plan={self.plan_id} athlete={self.athlete_id}>"
