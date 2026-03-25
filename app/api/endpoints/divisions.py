from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.division import (
    DEMOTE_COUNT,
    DIVISION_DISPLAY,
    DIVISION_ORDER,
    PROMOTE_COUNT,
    Division,
    division_index,
)
from app.models.user import User
from app.schemas.division import (
    CurrentDivisionResponse,
    LeagueStanding,
    WeekHistoryEntry,
)
from app.services.division import (
    _week_bounds,
    get_group_standings,
    get_or_create_membership,
    get_or_create_season,
    get_total_groups,
    get_user_history,
    process_previous_season,
)

router = APIRouter(prefix="/divisions", tags=["Divisions"])


@router.get("/current", response_model=CurrentDivisionResponse)
async def get_current_division(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's current division, group standings and weekly progress."""
    # 1. Process previous week if needed
    await process_previous_season(db)

    # 2. Ensure current season & membership exist
    monday, sunday = _week_bounds()
    season = await get_or_create_season(db, monday, sunday)
    membership = await get_or_create_membership(db, current_user.id, season)

    # 3. Get group standings (live weekly XP)
    raw_standings = await get_group_standings(
        db, season, membership.division, membership.group_number, current_user.id
    )

    standings = [LeagueStanding(**s) for s in raw_standings]

    # Current user's weekly XP
    user_standing = next(
        (s for s in standings if s.is_current_user), None
    )
    weekly_xp = user_standing.weekly_xp if user_standing else 0

    today = date.today()
    days_remaining = max((sunday - today).days, 0)

    # Total groups in this division
    total_groups = await get_total_groups(db, season.id, membership.division)

    return CurrentDivisionResponse(
        division=membership.division,
        division_display=DIVISION_DISPLAY.get(
            membership.division, membership.division.value
        ),
        division_order=division_index(membership.division),
        total_divisions=len(DIVISION_ORDER),
        weekly_xp=weekly_xp,
        days_remaining=days_remaining,
        week_start=monday,
        week_end=sunday,
        group_number=membership.group_number,
        total_groups=total_groups,
        standings=standings,
        promote_count=PROMOTE_COUNT,
        demote_count=DEMOTE_COUNT,
    )


@router.get("/groups/{group_number}", response_model=list[LeagueStanding])
async def get_group_standings_by_number(
    group_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get standings for any group in the current user's division."""
    from fastapi import HTTPException

    monday, sunday = _week_bounds()
    season = await get_or_create_season(db, monday, sunday)
    membership = await get_or_create_membership(db, current_user.id, season)

    total_groups = await get_total_groups(db, season.id, membership.division)
    if group_number < 1 or group_number > total_groups:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    raw = await get_group_standings(
        db, season, membership.division, group_number, current_user.id
    )
    return [LeagueStanding(**s) for s in raw]


@router.get("/history", response_model=list[WeekHistoryEntry])
async def get_division_history(
    limit: int = Query(10, ge=1, le=52),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get past weekly league results for the current user."""
    rows = await get_user_history(db, current_user.id, limit)
    return [WeekHistoryEntry(**r) for r in rows]
