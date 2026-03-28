import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChallengeStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    challenger_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    challenged_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    wager_xp: Mapped[int] = mapped_column(Integer)
    status: Mapped[ChallengeStatus] = mapped_column(
        Enum(ChallengeStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=ChallengeStatus.PENDING,
    )
    challenger_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="SET NULL"), nullable=True
    )
    challenged_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="SET NULL"), nullable=True
    )
    winner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    challenger: Mapped["User"] = relationship("User", foreign_keys=[challenger_id])  # type: ignore[name-defined]
    challenged: Mapped["User"] = relationship("User", foreign_keys=[challenged_id])  # type: ignore[name-defined]
    winner: Mapped["User | None"] = relationship("User", foreign_keys=[winner_id])  # type: ignore[name-defined]
    challenger_session: Mapped["WorkoutSession | None"] = relationship(  # type: ignore[name-defined]
        "WorkoutSession", foreign_keys=[challenger_session_id]
    )
    challenged_session: Mapped["WorkoutSession | None"] = relationship(  # type: ignore[name-defined]
        "WorkoutSession", foreign_keys=[challenged_session_id]
    )
