from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.plan import TagResponse


class CoachTierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    xp_per_month: int = Field(ge=0)
    tag_ids: list[int] = []


class CoachTierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    xp_per_month: int | None = Field(None, ge=0)
    tag_ids: list[int] | None = None


class CoachTierResponse(BaseModel):
    id: int
    coach_id: int
    name: str
    description: str | None = None
    xp_per_month: int
    tags: list[TagResponse] = []

    model_config = {"from_attributes": True}


class CoachPublic(BaseModel):
    id: int
    name: str
    avatar_url: str | None = None
    subscription_xp_price: int | None = None
    plan_count: int
    subscriber_count: int
    is_subscribed: bool
    current_tier_id: int | None = None
    tiers: list[CoachTierResponse] = []

    model_config = {"from_attributes": True}


class SetPriceRequest(BaseModel):
    price: int = Field(ge=0)


class SubscribeRequest(BaseModel):
    tier_id: int | None = None


class CoachSubscriptionResponse(BaseModel):
    id: int
    coach_id: int
    coach_name: str
    coach_avatar_url: str | None = None
    xp_per_month: int
    subscribed_at: datetime
    tier: CoachTierResponse | None = None

    model_config = {"from_attributes": True}


class CoachSubscriberEntry(BaseModel):
    athlete_id: int
    athlete_name: str
    xp_per_month: int
    subscribed_at: datetime
    tier_name: str | None = None
