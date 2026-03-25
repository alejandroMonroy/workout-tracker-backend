from datetime import datetime

from pydantic import BaseModel

from app.models.friendship import FriendshipStatus


class AthletePublic(BaseModel):
    id: int
    name: str
    avatar_url: str | None = None
    level: int
    total_xp: int
    current_division: str | None = None
    # Friendship context (null when not related)
    friendship_id: int | None = None
    friendship_status: str | None = None  # "pending_sent" | "pending_received" | "accepted"

    model_config = {"from_attributes": True}


class RecordPublic(BaseModel):
    id: int
    exercise_id: int
    exercise_name: str
    record_type: str
    value: float
    achieved_at: datetime


class RecentSessionPublic(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None = None
    total_duration_sec: int | None = None
    exercise_count: int
    set_count: int


class AthleteProfile(AthletePublic):
    sessions_30d: int
    total_sessions: int
    records: list[RecordPublic]
    recent_sessions: list[RecentSessionPublic]


class FriendshipResponse(BaseModel):
    id: int
    requester_id: int
    addressee_id: int
    status: FriendshipStatus
    created_at: datetime
    other_user: AthletePublic

    model_config = {"from_attributes": True}
