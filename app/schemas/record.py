from datetime import datetime

from pydantic import BaseModel

from app.models.record import RecordType
from app.schemas.exercise import ExerciseResponse


class RecordResponse(BaseModel):
    id: int
    user_id: int
    exercise_id: int
    exercise: ExerciseResponse | None = None
    record_type: RecordType
    value: float
    achieved_at: datetime
    session_id: int | None = None

    model_config = {"from_attributes": True}
