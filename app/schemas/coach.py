from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class InviteAthleteRequest(BaseModel):
    athlete_email: EmailStr


class AssignTemplateRequest(BaseModel):
    template_id: int
    athlete_id: int


class CoachAthleteResponse(BaseModel):
    id: int
    athlete_id: int
    athlete: UserResponse
    status: str
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
    relationship_status: str | None = None  # None / "pending" / "active"
    relationship_initiated_by: str | None = None  # "coach" / "athlete"

    model_config = {"from_attributes": True}


class CoachRequestResponse(BaseModel):
    """An athlete's pending request to a coach."""
    id: int
    athlete: UserResponse
    created_at: datetime

    model_config = {"from_attributes": True}
