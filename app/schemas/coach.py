from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class InviteAthleteRequest(BaseModel):
    athlete_email: EmailStr


class AssignTemplateRequest(BaseModel):
    template_id: int
    athlete_id: int


class CoachSubscriptionResponse(BaseModel):
    id: int
    athlete_id: int
    athlete: UserResponse
    status: str
    xp_per_month: int
    started_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Coach discovery ──


class CoachProfileResponse(BaseModel):
    """Public coach profile with stats."""
    id: int
    name: str
    email: str
    avatar_url: str | None = None
    athlete_count: int = 0
    plan_count: int = 0
    xp_per_month: int = 0
    subscription_status: str | None = None  # None / "pending" / "active" / "expired"
    subscription_initiated_by: str | None = None  # "coach" / "athlete"

    model_config = {"from_attributes": True}


class CoachRequestResponse(BaseModel):
    """An athlete's pending subscription request."""
    id: int
    athlete: UserResponse
    xp_per_month: int
    created_at: datetime

    model_config = {"from_attributes": True}
