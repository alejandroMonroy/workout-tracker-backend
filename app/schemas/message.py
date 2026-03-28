from datetime import datetime

from pydantic import BaseModel, Field


class CoachMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class CoachMessageResponse(BaseModel):
    id: int
    session_id: int | None
    athlete_id: int
    athlete_name: str
    coach_id: int
    body: str
    sent_at: datetime
    read_at: datetime | None

    model_config = {"from_attributes": True}
