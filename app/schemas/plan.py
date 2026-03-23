from datetime import datetime

from pydantic import BaseModel, Field

from app.models.plan import BlockType, SubscriptionStatus
from app.models.template import WorkoutModality
from app.schemas.exercise import ExerciseResponse


# ── BlockExercise ─────────────────────────────────────


class BlockExerciseCreate(BaseModel):
    exercise_id: int
    order: int = 0
    target_sets: int | None = None
    target_reps: int | None = None
    target_weight_kg: float | None = None
    target_distance_m: float | None = None
    target_duration_sec: int | None = None
    rest_sec: int | None = None
    notes: str | None = None


class BlockExerciseResponse(BaseModel):
    id: int
    exercise_id: int
    exercise: ExerciseResponse | None = None
    order: int
    target_sets: int | None = None
    target_reps: int | None = None
    target_weight_kg: float | None = None
    target_distance_m: float | None = None
    target_duration_sec: int | None = None
    rest_sec: int | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}


# ── SessionBlock ──────────────────────────────────────


class SessionBlockCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    block_type: BlockType = BlockType.OTHER
    modality: WorkoutModality | None = None
    rounds: int | None = None
    time_cap_sec: int | None = None
    work_sec: int | None = None
    rest_sec: int | None = None
    order: int = 0
    exercises: list[BlockExerciseCreate] = []


class SessionBlockResponse(BaseModel):
    id: int
    name: str
    block_type: BlockType
    modality: WorkoutModality | None = None
    rounds: int | None = None
    time_cap_sec: int | None = None
    work_sec: int | None = None
    rest_sec: int | None = None
    order: int
    exercises: list[BlockExerciseResponse] = []

    model_config = {"from_attributes": True}


# ── PlanSession ───────────────────────────────────────


class PlanSessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    day_number: int = 1
    blocks: list[SessionBlockCreate] = []


class PlanSessionResponse(BaseModel):
    id: int
    plan_id: int
    name: str
    description: str | None = None
    day_number: int
    blocks: list[SessionBlockResponse] = []

    model_config = {"from_attributes": True}


# ── Plan ──────────────────────────────────────────────


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    duration_weeks: int | None = None
    is_public: bool = False
    sessions: list[PlanSessionCreate] = []


class PlanUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    duration_weeks: int | None = None
    is_public: bool | None = None


class PlanResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    duration_weeks: int | None = None
    is_public: bool
    created_by: int
    created_at: datetime
    sessions: list[PlanSessionResponse] = []

    model_config = {"from_attributes": True}


class PlanListResponse(BaseModel):
    """Lightweight plan response without deep nested data."""
    id: int
    name: str
    description: str | None = None
    duration_weeks: int | None = None
    is_public: bool
    created_by: int
    created_at: datetime
    session_count: int = 0

    model_config = {"from_attributes": True}


# ── Subscription ──────────────────────────────────────


class SubscriptionCreate(BaseModel):
    plan_id: int


class SubscriptionResponse(BaseModel):
    id: int
    plan_id: int
    athlete_id: int
    status: SubscriptionStatus
    subscribed_at: datetime
    plan: PlanListResponse | None = None

    model_config = {"from_attributes": True}
