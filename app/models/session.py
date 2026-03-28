import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SessionType(str, enum.Enum):
    MANUAL = "manual"
    CLASS = "class"


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_templates.id"), nullable=True
    )
    plan_workout_id: Mapped[int | None] = mapped_column(
        ForeignKey("plan_workouts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    class_schedule_id: Mapped[int | None] = mapped_column(
        ForeignKey("gym_class_schedules.id", ondelete="SET NULL"), nullable=True
    )
    session_type: Mapped[SessionType] = mapped_column(
        Enum(SessionType, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=SessionType.MANUAL,
        server_default="manual",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rpe: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # 1-10
    mood: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")  # noqa: F821
    template: Mapped["WorkoutTemplate | None"] = relationship()  # noqa: F821
    sets: Mapped[list["SessionSet"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="SessionSet.id"
    )

    def __repr__(self) -> str:
        return f"<WorkoutSession {self.id} user={self.user_id}>"


class SessionSet(Base):
    __tablename__ = "session_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="CASCADE")
    )
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    set_number: Mapped[int] = mapped_column(Integer)
    sets_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpe: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    session: Mapped["WorkoutSession"] = relationship(back_populates="sets")
    exercise: Mapped["Exercise"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<SessionSet session={self.session_id} set={self.set_number}>"
