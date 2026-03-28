from datetime import datetime
from pydantic import BaseModel, Field


class CoachPublic(BaseModel):
    id: int
    name: str
    avatar_url: str | None = None
    subscription_xp_price: int | None = None
    plan_count: int
    subscriber_count: int
    is_subscribed: bool

    model_config = {"from_attributes": True}


class SetPriceRequest(BaseModel):
    price: int = Field(ge=0)


class CoachSubscriptionResponse(BaseModel):
    id: int
    coach_id: int
    coach_name: str
    coach_avatar_url: str | None = None
    xp_per_month: int
    subscribed_at: datetime

    model_config = {"from_attributes": True}


class CoachSubscriberEntry(BaseModel):
    athlete_id: int
    athlete_name: str
    xp_per_month: int
    subscribed_at: datetime
