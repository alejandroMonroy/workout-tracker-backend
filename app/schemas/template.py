from pydantic import BaseModel, Field

from app.models.template import WorkoutModality
from app.schemas.exercise import ExerciseResponse


# --- Request schemas ---


class TemplateBlockCreate(BaseModel):
    exercise_id: int
    order: int = 0
    target_sets: int | None = None
    target_reps: int | None = None
    target_weight_kg: float | None = None
    target_distance_m: float | None = None
    target_duration_sec: int | None = None
    rest_sec: int | None = None
    notes: str | None = None


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    modality: WorkoutModality = WorkoutModality.CUSTOM
    rounds: int | None = None
    time_cap_sec: int | None = None
    is_public: bool = False
    blocks: list[TemplateBlockCreate] = []


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    modality: WorkoutModality | None = None
    rounds: int | None = None
    time_cap_sec: int | None = None
    is_public: bool | None = None
    blocks: list[TemplateBlockCreate] | None = None


# --- Response schemas ---


class TemplateBlockResponse(BaseModel):
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


class TemplateResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    modality: WorkoutModality
    rounds: int | None = None
    time_cap_sec: int | None = None
    is_public: bool
    created_by: int
    assigned_by: int | None = None
    blocks: list[TemplateBlockResponse] = []

    model_config = {"from_attributes": True}
