from datetime import datetime

from pydantic import BaseModel, Field


class ChallengeCreate(BaseModel):
    challenged_id: int
    wager_xp: int = Field(ge=1)
    session_id: int


class ChallengeUserSnippet(BaseModel):
    id: int
    name: str


class ChallengeResponse(BaseModel):
    id: int
    challenger: ChallengeUserSnippet
    challenged: ChallengeUserSnippet
    wager_xp: int
    status: str
    challenger_session_id: int | None
    challenged_session_id: int | None
    winner_id: int | None
    created_at: datetime
    expires_at: datetime
    completed_at: datetime | None


class ChallengeSubmit(BaseModel):
    session_id: int
