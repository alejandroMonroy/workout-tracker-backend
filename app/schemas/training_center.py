from datetime import datetime

from pydantic import BaseModel

from app.models.training_center import CenterMemberRole, CenterMemberStatus


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
    member_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingCenterListItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    city: str | None = None
    logo_url: str | None = None
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
