from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.template import TemplateResponse


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")


class TagResponse(BaseModel):
    id: int
    name: str
    color: str
    created_by: int

    model_config = {"from_attributes": True}


class PlanWorkoutCreate(BaseModel):
    template_id: int
    order: int = 0
    day: int | None = None
    notes: str | None = None


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    is_public: bool = False
    workouts: list[PlanWorkoutCreate] = []
    tag_ids: list[int] = []


class PlanUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    is_public: bool | None = None
    workouts: list[PlanWorkoutCreate] | None = None
    tag_ids: list[int] | None = None


class PlanWorkoutResponse(BaseModel):
    id: int
    plan_id: int
    template_id: int
    order: int
    day: int | None = None
    notes: str | None = None
    template: TemplateResponse | None = None

    model_config = {"from_attributes": True}


class PlanResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_by: int
    creator_name: str = ""
    is_public: bool
    created_at: datetime
    workouts: list[PlanWorkoutResponse] = []
    tags: list[TagResponse] = []
    subscription_id: int | None = None

    model_config = {"from_attributes": True}


class PlanSubscriberResponse(BaseModel):
    subscription_id: int
    athlete_id: int
    athlete_name: str
    athlete_email: str
    subscribed_at: datetime

    model_config = {"from_attributes": True}
