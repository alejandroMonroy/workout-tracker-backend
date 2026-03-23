from pydantic import BaseModel, Field

from app.models.exercise import ExerciseType


# --- Request schemas ---


class ExerciseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: ExerciseType
    muscle_groups: list[str] | None = None
    equipment: str | None = None
    description: str | None = None


class ExerciseUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    type: ExerciseType | None = None
    muscle_groups: list[str] | None = None
    equipment: str | None = None
    description: str | None = None


# --- Response schemas ---


class ExerciseResponse(BaseModel):
    id: int
    name: str
    type: ExerciseType
    muscle_groups: list[str] | None = None
    equipment: str | None = None
    description: str | None = None
    is_global: bool
    created_by: int | None = None

    model_config = {"from_attributes": True}
