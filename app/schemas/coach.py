from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class InviteAthleteRequest(BaseModel):
    athlete_email: EmailStr


class AssignTemplateRequest(BaseModel):
    template_id: int
    athlete_id: int


class CoachAthleteResponse(BaseModel):
    id: int
    athlete_id: int
    athlete: UserResponse
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
