from datetime import datetime

from pydantic import BaseModel, Field


class CompetitionPlaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class CompetitionPlaceResponse(BaseModel):
    id: int
    name: str


class CompetitionWorkoutCreate(BaseModel):
    template_id: int
    init_time: datetime
    place_ids: list[int] = Field(min_length=1)
    order: int = 0
    notes: str | None = None


class CompetitionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    location: str = Field(min_length=1, max_length=300)
    init_date: datetime
    end_date: datetime
    inscription_xp_cost: int = Field(ge=0, default=0)


class CompetitionWorkoutResponse(BaseModel):
    id: int
    template_id: int
    template_name: str
    init_time: datetime
    order: int
    notes: str | None
    places: list[CompetitionPlaceResponse]


class CompetitionResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_by: int
    creator_name: str
    location: str
    init_date: datetime
    end_date: datetime
    inscription_xp_cost: int
    subscriber_count: int
    is_subscribed: bool
    created_at: datetime
    places: list[CompetitionPlaceResponse]
    workouts: list[CompetitionWorkoutResponse]


class LeaderboardEntry(BaseModel):
    rank: int
    athlete_id: int
    athlete_name: str
    total_xp: int
    workouts_completed: int


class WorkoutResultSubmit(BaseModel):
    session_id: int


class WorkoutResultEntry(BaseModel):
    id: int
    position: int | None
    athlete_id: int
    athlete_name: str
    finished_at: datetime
    status: str
    xp_awarded: int
    session_id: int
