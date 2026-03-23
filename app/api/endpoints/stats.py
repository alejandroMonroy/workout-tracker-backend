from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.exercise import Exercise
from app.models.record import PersonalRecord
from app.models.session import SessionSet, WorkoutSession
from app.models.user import User
from app.schemas.record import RecordResponse

router = APIRouter(prefix="/stats", tags=["Stats"])


class ProgressPoint(dict):
    """Single data point for exercise progress."""
    pass


@router.get("/timeline")
async def get_timeline(
    period: str = Query("month", description="Periodo: week, month, quarter, year, all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-session aggregate metrics for the progress chart."""
    now = datetime.now(timezone.utc)
    date_filter = _get_date_filter(now, period)

    query = (
        select(
            WorkoutSession.id,
            WorkoutSession.started_at,
            WorkoutSession.total_duration_sec,
            WorkoutSession.rpe,
            func.count(SessionSet.id).label("sets"),
            func.count(distinct(SessionSet.exercise_id)).label("exercises"),
            func.sum(
                func.coalesce(SessionSet.reps, 0)
                * func.coalesce(SessionSet.weight_kg, 0)
            ).label("volume"),
        )
        .outerjoin(SessionSet, WorkoutSession.id == SessionSet.session_id)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.finished_at.is_not(None),
        )
    )

    if date_filter:
        query = query.where(WorkoutSession.started_at >= date_filter)

    query = query.group_by(WorkoutSession.id).order_by(WorkoutSession.started_at)

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "date": row.started_at.isoformat(),
            "volume": round(row.volume or 0, 1),
            "duration_min": round((row.total_duration_sec or 0) / 60, 1),
            "sets": row.sets,
            "exercises": row.exercises,
            "rpe": row.rpe,
        }
        for row in rows
    ]


@router.get("/progress")
async def get_progress(
    exercise_id: int = Query(..., description="ID del ejercicio"),
    period: str = Query("month", description="Periodo: week, month, quarter, year, all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get progress data for a specific exercise over time."""
    now = datetime.now(timezone.utc)
    date_filter = _get_date_filter(now, period)

    query = (
        select(
            WorkoutSession.started_at,
            func.max(SessionSet.weight_kg).label("max_weight"),
            func.max(
                case(
                    (
                        SessionSet.reps > 1,
                        SessionSet.weight_kg * (1 + SessionSet.reps / 30.0),
                    ),
                    else_=SessionSet.weight_kg,
                )
            ).label("estimated_1rm"),
            func.sum(
                func.coalesce(SessionSet.reps, 0)
                * func.coalesce(SessionSet.weight_kg, 0)
            ).label("volume"),
            func.max(SessionSet.reps).label("max_reps"),
            func.max(SessionSet.distance_m).label("max_distance"),
            func.count(SessionSet.id).label("total_sets"),
        )
        .join(SessionSet, WorkoutSession.id == SessionSet.session_id)
        .where(
            WorkoutSession.user_id == current_user.id,
            SessionSet.exercise_id == exercise_id,
            WorkoutSession.finished_at.is_not(None),
        )
    )

    if date_filter:
        query = query.where(WorkoutSession.started_at >= date_filter)

    query = query.group_by(WorkoutSession.id, WorkoutSession.started_at).order_by(
        WorkoutSession.started_at
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "date": row.started_at.isoformat(),
            "max_weight": row.max_weight,
            "estimated_1rm": round(row.estimated_1rm, 2) if row.estimated_1rm else None,
            "volume": round(row.volume, 2) if row.volume else 0,
            "max_reps": row.max_reps,
            "max_distance": row.max_distance,
            "total_sets": row.total_sets,
        }
        for row in rows
    ]


@router.get("/summary")
async def get_summary(
    period: str = Query("week", description="Periodo: week, month, year"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get training summary for a given period."""
    now = datetime.now(timezone.utc)
    date_filter = _get_date_filter(now, period)

    # Total sessions in period
    sessions_query = select(func.count(WorkoutSession.id)).where(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.finished_at.is_not(None),
    )
    if date_filter:
        sessions_query = sessions_query.where(WorkoutSession.started_at >= date_filter)
    sessions_count = (await db.execute(sessions_query)).scalar_one()

    # Total volume (sets * reps * weight)
    volume_query = (
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
        )
    )
    if date_filter:
        volume_query = volume_query.where(WorkoutSession.started_at >= date_filter)
    total_volume = (await db.execute(volume_query)).scalar_one() or 0

    # Total sets
    sets_query = (
        select(func.count(SessionSet.id))
        .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.finished_at.is_not(None),
        )
    )
    if date_filter:
        sets_query = sets_query.where(WorkoutSession.started_at >= date_filter)
    total_sets = (await db.execute(sets_query)).scalar_one()

    # Total training time
    time_query = select(
        func.sum(WorkoutSession.total_duration_sec)
    ).where(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.finished_at.is_not(None),
    )
    if date_filter:
        time_query = time_query.where(WorkoutSession.started_at >= date_filter)
    total_time = (await db.execute(time_query)).scalar_one() or 0

    # Distinct exercises used
    exercises_query = (
        select(func.count(distinct(SessionSet.exercise_id)))
        .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.finished_at.is_not(None),
        )
    )
    if date_filter:
        exercises_query = exercises_query.where(WorkoutSession.started_at >= date_filter)
    distinct_exercises = (await db.execute(exercises_query)).scalar_one()

    # Muscle group distribution
    muscle_query = (
        select(
            func.unnest(Exercise.muscle_groups).label("muscle"),
            func.count(SessionSet.id).label("sets"),
        )
        .join(Exercise, Exercise.id == SessionSet.exercise_id)
        .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.finished_at.is_not(None),
        )
    )
    if date_filter:
        muscle_query = muscle_query.where(WorkoutSession.started_at >= date_filter)
    muscle_query = muscle_query.group_by("muscle").order_by(func.count(SessionSet.id).desc())
    muscle_result = await db.execute(muscle_query)
    muscle_distribution = {row.muscle: row.sets for row in muscle_result.all()}

    # Average RPE
    rpe_query = select(func.avg(WorkoutSession.rpe)).where(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.finished_at.is_not(None),
        WorkoutSession.rpe.is_not(None),
    )
    if date_filter:
        rpe_query = rpe_query.where(WorkoutSession.started_at >= date_filter)
    avg_rpe = (await db.execute(rpe_query)).scalar_one()

    return {
        "period": period,
        "total_sessions": sessions_count,
        "total_volume_kg": round(total_volume, 2),
        "total_sets": total_sets,
        "total_time_sec": total_time,
        "distinct_exercises": distinct_exercises,
        "muscle_distribution": muscle_distribution,
        "avg_rpe": round(avg_rpe, 1) if avg_rpe else None,
    }


@router.get("/records", response_model=list[RecordResponse])
async def get_records(
    exercise_id: int | None = Query(None, description="Filtrar por ejercicio"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all personal records for the current user."""
    query = (
        select(PersonalRecord)
        .options(selectinload(PersonalRecord.exercise))
        .where(PersonalRecord.user_id == current_user.id)
    )
    if exercise_id:
        query = query.where(PersonalRecord.exercise_id == exercise_id)

    query = query.order_by(PersonalRecord.achieved_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


def _get_date_filter(now: datetime, period: str) -> datetime | None:
    match period:
        case "week":
            return now - timedelta(weeks=1)
        case "month":
            return now - timedelta(days=30)
        case "quarter":
            return now - timedelta(days=90)
        case "year":
            return now - timedelta(days=365)
        case "all":
            return None
        case _:
            return now - timedelta(days=30)
