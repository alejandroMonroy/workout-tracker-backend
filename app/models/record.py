import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RecordType(str, enum.Enum):
    ONE_RM = "1rm"
    MAX_REPS = "max_reps"
    BEST_TIME = "best_time"
    MAX_DISTANCE = "max_distance"
    MAX_WEIGHT = "max_weight"


class PersonalRecord(Base):
    __tablename__ = "personal_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    record_type: Mapped[RecordType] = mapped_column(Enum(RecordType))
    value: Mapped[float] = mapped_column(Float)
    achieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_sessions.id"), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="personal_records")  # noqa: F821
    exercise: Mapped["Exercise"] = relationship()  # noqa: F821
    session: Mapped["WorkoutSession | None"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<PersonalRecord {self.record_type.value} exercise={self.exercise_id}>"
