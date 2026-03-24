import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CoachAthleteStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"


class CoachAthlete(Base):
    __tablename__ = "coach_athletes"

    id: Mapped[int] = mapped_column(primary_key=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[CoachAthleteStatus] = mapped_column(
        Enum(CoachAthleteStatus), default=CoachAthleteStatus.PENDING
    )
    initiated_by: Mapped[str] = mapped_column(
        String(10), default="coach", server_default="coach"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<CoachAthlete coach={self.coach_id} athlete={self.athlete_id}>"
