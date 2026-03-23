from datetime import date

from pydantic import BaseModel

from app.models.division import Division


class LeagueStanding(BaseModel):
    user_id: int
    name: str
    avatar_url: str | None = None
    weekly_xp: int
    rank: int
    promoted: bool
    demoted: bool
    is_current_user: bool


class CurrentDivisionResponse(BaseModel):
    division: Division
    division_display: str
    division_order: int
    total_divisions: int
    weekly_xp: int
    days_remaining: int
    week_start: date
    week_end: date
    group_number: int
    total_groups: int
    standings: list[LeagueStanding]
    promote_count: int
    demote_count: int


class WeekHistoryEntry(BaseModel):
    week_start: date
    week_end: date
    division: Division
    division_display: str
    weekly_xp: int
    final_rank: int | None
    promoted: bool
    demoted: bool
    group_size: int
