from datetime import datetime

from pydantic import BaseModel

from app.models.training_center import (
    CenterMemberRole,
    CenterMemberStatus,
    CenterSubscriptionStatus,
    ClassBookingStatus,
    ClassStatus,
)


# ── Training Center ──────────────────────────────────────────────────────────


class TrainingCenterCreate(BaseModel):
    name: str
    description: str | None = None
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    logo_url: str | None = None


class TrainingCenterUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    logo_url: str | None = None


class TrainingCenterResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    logo_url: str | None = None
    owner_id: int
    is_active: bool
    monthly_xp: int = 0
    member_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingCenterListItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    city: str | None = None
    logo_url: str | None = None
    monthly_xp: int = 0
    member_count: int = 0
    is_active: bool

    model_config = {"from_attributes": True}


# ── Center Membership ────────────────────────────────────────────────────────


class CenterMembershipResponse(BaseModel):
    id: int
    center_id: int
    center_name: str = ""
    user_id: int
    user_name: str = ""
    role: CenterMemberRole
    status: CenterMemberStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class JoinCenterRequest(BaseModel):
    role: CenterMemberRole = CenterMemberRole.MEMBER


class UpdateMembershipRequest(BaseModel):
    status: CenterMemberStatus | None = None
    role: CenterMemberRole | None = None


# ── Center Plan ──────────────────────────────────────────────────────────────


class PublishPlanRequest(BaseModel):
    plan_id: int


class CenterPlanResponse(BaseModel):
    id: int
    center_id: int
    plan_id: int
    plan_name: str = ""
    published_at: datetime

    model_config = {"from_attributes": True}


# ── Center Subscription ───────────────────────────────────────


class CenterSubscriptionResponse(BaseModel):
    id: int
    center_id: int
    center_name: str = ""
    athlete_id: int
    athlete_name: str = ""
    status: CenterSubscriptionStatus
    xp_per_month: int
    started_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscribeToCenterRequest(BaseModel):
    xp_per_month: int = 0


# ── Center Class ─────────────────────────────────────────────


class CenterClassCreate(BaseModel):
    name: str
    description: str | None = None
    scheduled_at: datetime
    duration_min: int | None = None
    max_capacity: int | None = None
    template_id: int | None = None


class CenterClassResponse(BaseModel):
    id: int
    center_id: int
    coach_id: int
    coach_name: str = ""
    name: str
    description: str | None = None
    scheduled_at: datetime
    duration_min: int | None = None
    max_capacity: int | None = None
    template_id: int | None = None
    status: ClassStatus
    booking_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Class Booking ────────────────────────────────────────────


class ClassBookingResponse(BaseModel):
    id: int
    class_id: int
    athlete_id: int
    athlete_name: str = ""
    status: ClassBookingStatus
    booked_at: datetime

    model_config = {"from_attributes": True}
