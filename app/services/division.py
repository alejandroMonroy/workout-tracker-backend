"""Division / league system service — handles weekly seasons, group assignment,
promotion / demotion logic and leaderboard computation."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.division import (
    DEMOTE_COUNT,
    DIVISION_DISPLAY,
    GROUP_SIZE,
    PROMOTE_COUNT,
    Division,
    LeagueMembership,
    LeagueSeason,
    demote_division,
    promote_division,
)
from app.models.user import User
from app.models.xp import XPTransaction


# ── helpers ──────────────────────────────────────────────────────────────────


def _week_bounds(d: date | None = None) -> tuple[date, date]:
    """Return (monday, sunday) for the ISO week containing *d*."""
    d = d or date.today()
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _as_utc(d: date, end_of_day: bool = False) -> datetime:
    """Convert a date to a UTC datetime (start or end of day)."""
    t = time.max if end_of_day else time.min
    return datetime.combine(d, t, tzinfo=timezone.utc)


# ── season lifecycle ─────────────────────────────────────────────────────────


async def get_or_create_season(
    db: AsyncSession, monday: date, sunday: date
) -> LeagueSeason:
    result = await db.execute(
        select(LeagueSeason).where(LeagueSeason.week_start == monday)
    )
    season = result.scalar_one_or_none()
    if season:
        return season

    season = LeagueSeason(week_start=monday, week_end=sunday)
    db.add(season)
    await db.flush()
    return season


async def process_previous_season(db: AsyncSession) -> None:
    """If last week's season exists and is unprocessed, compute rankings,
    promotions and demotions for every group."""
    today = date.today()
    prev_monday, prev_sunday = _week_bounds(today - timedelta(days=7))

    result = await db.execute(
        select(LeagueSeason).where(
            LeagueSeason.week_start == prev_monday,
            LeagueSeason.processed == False,  # noqa: E712
        )
    )
    prev_season = result.scalar_one_or_none()
    if not prev_season:
        return

    # Load all memberships
    mem_result = await db.execute(
        select(LeagueMembership).where(
            LeagueMembership.season_id == prev_season.id
        )
    )
    all_memberships = mem_result.scalars().all()
    if not all_memberships:
        prev_season.processed = True
        await db.flush()
        return

    # Compute weekly XP from xp_transactions
    start_dt = _as_utc(prev_season.week_start)
    end_dt = _as_utc(prev_season.week_end + timedelta(days=1))

    for m in all_memberships:
        xp_result = await db.execute(
            select(func.coalesce(func.sum(XPTransaction.amount), 0)).where(
                XPTransaction.user_id == m.user_id,
                XPTransaction.created_at >= start_dt,
                XPTransaction.created_at < end_dt,
            )
        )
        m.weekly_xp = xp_result.scalar_one()

    # Group by (division, group_number)
    groups: dict[tuple[Division, int], list[LeagueMembership]] = {}
    for m in all_memberships:
        groups.setdefault((m.division, m.group_number), []).append(m)

    # Rank & promote / demote
    for (div, _gn), members in groups.items():
        members.sort(key=lambda m: m.weekly_xp, reverse=True)
        group_size = len(members)

        for rank, m in enumerate(members, 1):
            m.final_rank = rank

            if rank <= PROMOTE_COUNT and div != Division.ELITE:
                m.promoted = True
                user_res = await db.execute(
                    select(User).where(User.id == m.user_id)
                )
                user = user_res.scalar_one()
                user.current_division = promote_division(div).value

            elif (
                rank > group_size - DEMOTE_COUNT
                and group_size > DEMOTE_COUNT
                and div != Division.BRONCE
            ):
                m.demoted = True
                user_res = await db.execute(
                    select(User).where(User.id == m.user_id)
                )
                user = user_res.scalar_one()
                user.current_division = demote_division(div).value

    prev_season.processed = True
    await db.flush()


# ── membership ───────────────────────────────────────────────────────────────


async def get_or_create_membership(
    db: AsyncSession, user_id: int, season: LeagueSeason
) -> LeagueMembership:
    result = await db.execute(
        select(LeagueMembership).where(
            LeagueMembership.user_id == user_id,
            LeagueMembership.season_id == season.id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership:
        return membership

    # Get user's current division
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one()
    division = (
        Division(user.current_division)
        if user.current_division
        else Division.BRONCE
    )

    # Ensure user has current_division persisted
    if not user.current_division:
        user.current_division = Division.BRONCE.value

    # Find a group with room
    group_q = await db.execute(
        select(
            LeagueMembership.group_number,
            func.count(LeagueMembership.id).label("cnt"),
        )
        .where(
            LeagueMembership.season_id == season.id,
            LeagueMembership.division == division,
        )
        .group_by(LeagueMembership.group_number)
        .order_by(LeagueMembership.group_number)
    )
    groups = group_q.all()

    group_number = 1
    for gn, count in groups:
        if count < GROUP_SIZE:
            group_number = gn
            break
        group_number = gn + 1

    membership = LeagueMembership(
        user_id=user_id,
        season_id=season.id,
        division=division,
        group_number=group_number,
    )
    db.add(membership)
    await db.flush()
    return membership


async def get_total_groups(
    db: AsyncSession, season_id: int, division: Division
) -> int:
    """Return the number of distinct groups for a division in a season."""
    result = await db.execute(
        select(func.count(func.distinct(LeagueMembership.group_number))).where(
            LeagueMembership.season_id == season_id,
            LeagueMembership.division == division,
        )
    )
    return result.scalar_one() or 1


# ── standings / leaderboard ──────────────────────────────────────────────────


async def get_group_standings(
    db: AsyncSession,
    season: LeagueSeason,
    division: Division,
    group_number: int,
    current_user_id: int,
) -> list[dict]:
    """Return the current standings for a specific group in a season."""
    result = await db.execute(
        select(LeagueMembership, User)
        .join(User, LeagueMembership.user_id == User.id)
        .where(
            LeagueMembership.season_id == season.id,
            LeagueMembership.division == division,
            LeagueMembership.group_number == group_number,
        )
    )
    rows = result.all()

    start_dt = _as_utc(season.week_start)
    end_dt = _as_utc(season.week_end + timedelta(days=1))

    standings: list[dict] = []
    for _membership, user in rows:
        xp_res = await db.execute(
            select(func.coalesce(func.sum(XPTransaction.amount), 0)).where(
                XPTransaction.user_id == user.id,
                XPTransaction.created_at >= start_dt,
                XPTransaction.created_at < end_dt,
            )
        )
        weekly_xp = xp_res.scalar_one()
        standings.append(
            {
                "user_id": user.id,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "weekly_xp": weekly_xp,
                "is_current_user": user.id == current_user_id,
            }
        )

    standings.sort(key=lambda s: s["weekly_xp"], reverse=True)
    group_size = len(standings)

    for i, s in enumerate(standings):
        s["rank"] = i + 1
        s["promoted"] = (
            i < PROMOTE_COUNT and division != Division.ELITE
        )
        s["demoted"] = (
            i >= group_size - DEMOTE_COUNT
            and group_size > DEMOTE_COUNT
            and division != Division.BRONCE
        )

    return standings


# ── history ──────────────────────────────────────────────────────────────────


async def get_user_history(
    db: AsyncSession, user_id: int, limit: int = 10
) -> list[dict]:
    """Return past week results for a user."""
    result = await db.execute(
        select(LeagueMembership, LeagueSeason)
        .join(LeagueSeason, LeagueMembership.season_id == LeagueSeason.id)
        .where(
            LeagueMembership.user_id == user_id,
            LeagueSeason.processed == True,  # noqa: E712
        )
        .order_by(LeagueSeason.week_start.desc())
        .limit(limit)
    )
    rows = result.all()

    history: list[dict] = []
    for mem, season in rows:
        # Count group size
        cnt_res = await db.execute(
            select(func.count(LeagueMembership.id)).where(
                LeagueMembership.season_id == season.id,
                LeagueMembership.division == mem.division,
                LeagueMembership.group_number == mem.group_number,
            )
        )
        group_size = cnt_res.scalar_one()

        history.append(
            {
                "week_start": season.week_start,
                "week_end": season.week_end,
                "division": mem.division,
                "division_display": DIVISION_DISPLAY.get(
                    mem.division, mem.division.value
                ),
                "weekly_xp": mem.weekly_xp,
                "final_rank": mem.final_rank,
                "promoted": mem.promoted,
                "demoted": mem.demoted,
                "group_size": group_size,
            }
        )

    return history
