from datetime import datetime

from pydantic import BaseModel, Field

from app.models.session import SessionType
from app.schemas.exercise import ExerciseResponse


# --- Request schemas ---


class SessionSetCreate(BaseModel):
    exercise_id: int
    set_number: int
    sets_count: int | None = 1
    reps: int | None = None
    weight_kg: float | None = None
    distance_m: float | None = None
    duration_sec: int | None = None
    calories: float | None = None
    rpe: int | None = Field(None, ge=1, le=10)
    notes: str | None = None


class SessionCreate(BaseModel):
    template_id: int | None = None  # None = modo libre
    plan_workout_id: int | None = None
    notes: str | None = None


class SessionFinish(BaseModel):
    notes: str | None = None
    rpe: int | None = Field(None, ge=1, le=10)
    mood: str | None = None
    duration_sec: int | None = None  # actual timer elapsed, sent by client


# --- Response schemas ---


class SessionSetResponse(BaseModel):
    id: int
    session_id: int
    exercise_id: int
    exercise: ExerciseResponse | None = None
    set_number: int
    sets_count: int | None = 1
    reps: int | None = None
    weight_kg: float | None = None
    distance_m: float | None = None
    duration_sec: int | None = None
    calories: float | None = None
    rpe: int | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: int
    user_id: int
    template_id: int | None = None
    plan_workout_id: int | None = None
    class_schedule_id: int | None = None
    session_type: SessionType = SessionType.MANUAL
    started_at: datetime
    finished_at: datetime | None = None
    total_duration_sec: int | None = None
    notes: str | None = None
    rpe: int | None = None
    mood: str | None = None
    sets: list[SessionSetResponse] = []

    model_config = {"from_attributes": True}


class SessionSummaryResponse(SessionResponse):
    xp_earned: int = 0
    pr_count: int = 0
    total_volume_kg: float = 0.0
    coach_message: str | None = None
    coach_name: str | None = None


class SessionListResponse(BaseModel):
    id: int
    user_id: int
    template_id: int | None = None
    template_name: str | None = None
    class_schedule_id: int | None = None
    session_type: SessionType = SessionType.MANUAL
    started_at: datetime
    finished_at: datetime | None = None
    total_duration_sec: int | None = None
    notes: str | None = None
    rpe: int | None = None
    mood: str | None = None
    set_count: int = 0
    exercise_count: int = 0
    has_records: bool = False

    model_config = {"from_attributes": True}
