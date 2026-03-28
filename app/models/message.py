from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CoachMessage(Base):
    __tablename__ = "coach_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    athlete: Mapped["User"] = relationship("User", foreign_keys=[athlete_id])  # type: ignore[name-defined]
    coach: Mapped["User"] = relationship("User", foreign_keys=[coach_id])  # type: ignore[name-defined]
    session: Mapped["WorkoutSession"] = relationship("WorkoutSession", foreign_keys=[session_id])  # type: ignore[name-defined]
