"""Aggregated dashboard endpoint — single call for the frontend dashboard."""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.division import DEMOTE_COUNT, DIVISION_DISPLAY, PROMOTE_COUNT, Division, division_index
from app.models.record import PersonalRecord
from app.models.session import SessionSet, WorkoutSession
from app.models.user import User
from app.models.xp import XPTransaction, xp_for_level
from app.services.division import (
    _week_bounds,
    get_group_standings,
    get_or_create_membership,
    get_or_create_season,
    process_previous_season,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Single aggregated payload for the dashboard."""

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # ── 1. Training summary (30 days) ─────────────────────────────────────
    sessions_q = select(func.count(WorkoutSession.id)).where(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.finished_at.is_not(None),
        WorkoutSession.started_at >= thirty_days_ago,
    )
    total_sessions = (await db.execute(sessions_q)).scalar_one()

    volume_q = (
        select(
            func.sum(
                func.coalesce(SessionSet.reps, 0)
                * func.coalesce(SessionSet.weight_kg, 0)
            )
        )
        .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.finished_at.is_not(None),
            WorkoutSession.started_at >= thirty_days_ago,
        )
    )
    total_volume = (await db.execute(volume_q)).scalar_one() or 0

    time_q = select(func.sum(WorkoutSession.total_duration_sec)).where(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.finished_at.is_not(None),
        WorkoutSession.started_at >= thirty_days_ago,
    )
    total_time = (await db.execute(time_q)).scalar_one() or 0

    sets_q = (
        select(func.count(SessionSet.id))
        .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.finished_at.is_not(None),
            WorkoutSession.started_at >= thirty_days_ago,
        )
    )
    total_sets = (await db.execute(sets_q)).scalar_one()

    exercises_q = (
        select(func.count(distinct(SessionSet.exercise_id)))
        .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.finished_at.is_not(None),
            WorkoutSession.started_at >= thirty_days_ago,
        )
    )
    distinct_exercises = (await db.execute(exercises_q)).scalar_one()

    rpe_q = select(func.avg(WorkoutSession.rpe)).where(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.finished_at.is_not(None),
        WorkoutSession.rpe.is_not(None),
        WorkoutSession.started_at >= thirty_days_ago,
    )
    avg_rpe = (await db.execute(rpe_q)).scalar_one()

    # ── 2. Recent sessions (last 5) ──────────────────────────────────────
    recent_q = (
        select(
            WorkoutSession.id,
            WorkoutSession.started_at,
            WorkoutSession.finished_at,
            WorkoutSession.total_duration_sec,
            WorkoutSession.rpe,
            WorkoutSession.mood,
            func.count(distinct(SessionSet.exercise_id)).label("exercise_count"),
            func.count(SessionSet.id).label("set_count"),
        )
        .outerjoin(SessionSet, WorkoutSession.id == SessionSet.session_id)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.finished_at.is_not(None),
        )
        .group_by(WorkoutSession.id)
        .order_by(WorkoutSession.started_at.desc())
        .limit(5)
    )
    recent_rows = (await db.execute(recent_q)).all()
    recent_sessions = [
        {
            "id": r.id,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "total_duration_sec": r.total_duration_sec,
            "exercise_count": r.exercise_count,
            "set_count": r.set_count,
            "rpe": r.rpe,
        }
        for r in recent_rows
    ]

    # ── 3. Session dates for calendar (this month and next) ──────────────
    today = date.today()
    cal_start = today.replace(day=1)
    cal_end = (cal_start + timedelta(days=62)).replace(day=1)  # ~2 months
    day_trunc = func.date_trunc("day", WorkoutSession.started_at)
    session_dates_q = (
        select(
            day_trunc.label("day"),
            func.count(WorkoutSession.id).label("cnt"),
        )
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.finished_at.is_not(None),
            WorkoutSession.started_at >= datetime.combine(cal_start, datetime.min.time(), tzinfo=timezone.utc),
            WorkoutSession.started_at < datetime.combine(cal_end, datetime.min.time(), tzinfo=timezone.utc),
        )
        .group_by(day_trunc)
    )
    session_day_rows = (await db.execute(session_dates_q)).all()
    session_dates = [
        {"date": r.day.strftime("%Y-%m-%d"), "count": r.cnt}
        for r in session_day_rows
    ]

    # ── 4. XP summary ────────────────────────────────────────────────────
    total_xp = current_user.total_xp
    level = current_user.level
    xp_current = xp_for_level(level)
    xp_next = xp_for_level(level + 1)
    xp_progress = total_xp - xp_current
    xp_needed = xp_next - xp_current
    progress_pct = round(xp_progress / xp_needed * 100, 1) if xp_needed > 0 else 100

    # ── 6. League standing (minimal) ─────────────────────────────────────
    league = None
    try:
        await process_previous_season(db)
        monday, sunday = _week_bounds()
        season = await get_or_create_season(db, monday, sunday)
        membership = await get_or_create_membership(db, current_user.id, season)

        raw = await get_group_standings(
            db, season, membership.division, membership.group_number, current_user.id
        )
        user_standing = next((s for s in raw if s["is_current_user"]), None)

        league = {
            "division": membership.division.value,
            "division_display": DIVISION_DISPLAY.get(membership.division, membership.division.value),
            "weekly_xp": user_standing["weekly_xp"] if user_standing else 0,
            "rank": user_standing["rank"] if user_standing else 0,
            "group_size": len(raw),
            "days_remaining": max((sunday - today).days, 0),
        }
    except Exception:
        pass  # league data is optional

    # ── 7. Personal records (top 5 recent) ───────────────────────────────
    records_q = (
        select(PersonalRecord)
        .where(PersonalRecord.user_id == current_user.id)
        .order_by(PersonalRecord.achieved_at.desc())
        .limit(5)
    )
    record_rows = (await db.execute(records_q)).scalars().all()
    records = [
        {
            "id": r.id,
            "exercise_id": r.exercise_id,
            "record_type": r.record_type.value if hasattr(r.record_type, 'value') else r.record_type,
            "value": r.value,
            "achieved_at": r.achieved_at.isoformat(),
        }
        for r in record_rows
    ]

    # ── 8. Streak ─────────────────────────────────────────────────────────
    streak_trunc = func.date_trunc("day", WorkoutSession.started_at)
    streak_q = (
        select(
            streak_trunc.label("day"),
        )
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.finished_at.is_not(None),
        )
        .group_by(streak_trunc)
        .order_by(streak_trunc.desc())
    )
    streak_rows = (await db.execute(streak_q)).all()
    streak = 0
    check_date = today
    for row in streak_rows:
        row_date = row.day.date() if hasattr(row.day, 'date') else row.day
        if row_date == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        elif row_date == check_date - timedelta(days=1):
            check_date = row_date
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    return {
        "training": {
            "total_sessions": total_sessions,
            "total_volume_kg": round(total_volume, 1),
            "total_sets": total_sets,
            "total_time_sec": total_time,
            "distinct_exercises": distinct_exercises,
            "avg_rpe": round(avg_rpe, 1) if avg_rpe else None,
        },
        "recent_sessions": recent_sessions,
        "session_dates": session_dates,
        "xp": {
            "total_xp": total_xp,
            "level": level,
            "xp_progress": xp_progress,
            "xp_needed": xp_needed,
            "progress_pct": progress_pct,
        },
        "league": league,
        "records": records,
        "streak": streak,
    }
