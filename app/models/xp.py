import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class XPReason(str, enum.Enum):
    SESSION_COMPLETE = "session_complete"
    PERSONAL_RECORD = "personal_record"
    STREAK_BONUS = "streak_bonus"
    FIRST_SESSION = "first_session"
    EXERCISE_VARIETY = "exercise_variety"
    LONG_SESSION = "long_session"
    HIGH_VOLUME = "high_volume"
    CONSISTENCY = "consistency"
    MANUAL = "manual"


# Level thresholds: XP needed to reach each level
# Level 1 = 0 XP, Level 2 = 100 XP, ... grows quadratically
def xp_for_level(level: int) -> int:
    """XP required to reach a given level."""
    if level <= 1:
        return 0
    exponent = 1.5 + 0.01 * level
    return int(50 * (level - 1) ** exponent)


def level_from_xp(total_xp: int) -> int:
    """Calculate level from total XP."""
    level = 1
    while xp_for_level(level + 1) <= total_xp:
        level += 1
    return level


# XP award amounts
XP_AWARDS = {
    XPReason.SESSION_COMPLETE: 50,       # Per finished session
    XPReason.PERSONAL_RECORD: 25,        # Per new PR
    XPReason.STREAK_BONUS: 25,           # Per consecutive day in streak
    XPReason.FIRST_SESSION: 200,         # Very first session ever
    XPReason.EXERCISE_VARIETY: 30,       # 5+ distinct exercises in one session
    XPReason.LONG_SESSION: 40,           # Session > 60 min
    XPReason.HIGH_VOLUME: 35,            # Session volume > 5000 kg
    XPReason.CONSISTENCY: 150,           # 7-day streak milestone
}


class XPTransaction(Base):
    __tablename__ = "xp_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[XPReason] = mapped_column(
        Enum(XPReason, values_callable=lambda x: [e.value for e in x])
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_sessions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="xp_transactions")  # noqa: F821
    session: Mapped["WorkoutSession | None"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<XPTransaction {self.id} user={self.user_id} +{self.amount}xp>"
