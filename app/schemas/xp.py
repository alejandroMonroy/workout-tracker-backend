from datetime import datetime

from pydantic import BaseModel

from app.models.xp import XPReason


class XPTransactionResponse(BaseModel):
    id: int
    amount: int
    reason: XPReason
    description: str | None = None
    session_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class XPSummaryResponse(BaseModel):
    total_xp: int
    level: int
    xp_for_current_level: int
    xp_for_next_level: int
    xp_progress: int  # XP earned within current level
    xp_needed: int  # XP remaining to next level
    progress_pct: float  # 0-100
    rank: int
    total_users: int


class LeaderboardEntry(BaseModel):
    user_id: int
    name: str
    total_xp: int
    level: int
    rank: int
    avatar_url: str | None = None


class XPAwardResult(BaseModel):
    """Internal result from awarding XP — not an API response."""
    total_awarded: int
    new_total: int
    new_level: int
    level_up: bool
    transactions: list[XPTransactionResponse]
