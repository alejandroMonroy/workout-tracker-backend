from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.coach_athlete import CoachSubscription
from app.models.exercise import Exercise
from app.models.message import CoachMessage
from app.models.plan import Plan
from app.models.record import PersonalRecord
from app.models.session import SessionSet, WorkoutSession
from app.models.user import User, UserRole
from app.models.xp import XPReason, XPTransaction
from app.schemas.coaches import (
    CoachPublic,
    CoachSubscriberEntry,
    CoachSubscriptionResponse,
    SetPriceRequest,
)
from app.schemas.session import SessionListResponse

router = APIRouter(prefix="/coaches", tags=["Coaches"])


@router.get("", response_model=list[CoachPublic])
async def list_coaches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all coaches that have set a subscription price."""
    coaches_result = await db.execute(
        select(User).where(
            User.role == UserRole.COACH,
            User.subscription_xp_price.is_not(None),
        )
    )
    coaches = coaches_result.scalars().all()

    # Subscription map for current user
    subs_result = await db.execute(
        select(CoachSubscription.coach_id).where(
            CoachSubscription.athlete_id == current_user.id
        )
    )
    subscribed_coach_ids = {row[0] for row in subs_result.all()}

    # Plan counts per coach
    plan_counts_result = await db.execute(
        select(Plan.created_by, func.count(Plan.id)).group_by(Plan.created_by)
    )
    plan_counts = {row[0]: row[1] for row in plan_counts_result.all()}

    # Subscriber counts per coach
    sub_counts_result = await db.execute(
        select(CoachSubscription.coach_id, func.count(CoachSubscription.id)).group_by(
            CoachSubscription.coach_id
        )
    )
    sub_counts = {row[0]: row[1] for row in sub_counts_result.all()}

    return [
        CoachPublic(
            id=c.id,
            name=c.name,
            avatar_url=c.avatar_url,
            subscription_xp_price=c.subscription_xp_price,
            plan_count=plan_counts.get(c.id, 0),
            subscriber_count=sub_counts.get(c.id, 0),
            is_subscribed=c.id in subscribed_coach_ids,
        )
        for c in coaches
    ]


@router.get("/me", response_model=CoachPublic)
async def get_my_coach_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.COACH:
        raise HTTPException(status_code=403, detail="Solo coaches pueden acceder a este recurso")

    plan_count_result = await db.execute(
        select(func.count(Plan.id)).where(Plan.created_by == current_user.id)
    )
    plan_count = plan_count_result.scalar() or 0

    sub_count_result = await db.execute(
        select(func.count(CoachSubscription.id)).where(
            CoachSubscription.coach_id == current_user.id
        )
    )
    sub_count = sub_count_result.scalar() or 0

    return CoachPublic(
        id=current_user.id,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        subscription_xp_price=current_user.subscription_xp_price,
        plan_count=plan_count,
        subscriber_count=sub_count,
        is_subscribed=False,
    )


@router.put("/me/price", response_model=CoachPublic)
async def set_subscription_price(
    data: SetPriceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.COACH:
        raise HTTPException(status_code=403, detail="Solo coaches pueden establecer un precio")

    current_user.subscription_xp_price = data.price
    await db.flush()

    plan_count_result = await db.execute(
        select(func.count(Plan.id)).where(Plan.created_by == current_user.id)
    )
    plan_count = plan_count_result.scalar() or 0

    sub_count_result = await db.execute(
        select(func.count(CoachSubscription.id)).where(
            CoachSubscription.coach_id == current_user.id
        )
    )
    sub_count = sub_count_result.scalar() or 0

    return CoachPublic(
        id=current_user.id,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        subscription_xp_price=current_user.subscription_xp_price,
        plan_count=plan_count,
        subscriber_count=sub_count,
        is_subscribed=False,
    )


@router.get("/subscriptions", response_model=list[CoachSubscriptionResponse])
async def list_my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete: list all coaches I'm subscribed to."""
    rows = await db.execute(
        select(CoachSubscription, User)
        .join(User, User.id == CoachSubscription.coach_id)
        .where(CoachSubscription.athlete_id == current_user.id)
        .order_by(CoachSubscription.subscribed_at.desc())
    )
    return [
        CoachSubscriptionResponse(
            id=sub.id,
            coach_id=coach.id,
            coach_name=coach.name,
            coach_avatar_url=coach.avatar_url,
            xp_per_month=sub.xp_per_month,
            subscribed_at=sub.subscribed_at,
        )
        for sub, coach in rows.all()
    ]


@router.post("/{coach_id}/subscribe", response_model=CoachSubscriptionResponse)
async def subscribe_to_coach(
    coach_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    coach = await db.get(User, coach_id)
    if not coach or coach.role != UserRole.COACH:
        raise HTTPException(status_code=404, detail="Coach no encontrado")
    if coach.subscription_xp_price is None:
        raise HTTPException(status_code=400, detail="Este coach no ha habilitado suscripciones")
    if coach_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes suscribirte a ti mismo")

    existing = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.coach_id == coach_id,
            CoachSubscription.athlete_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya estás suscrito a este coach")

    price = coach.subscription_xp_price
    if current_user.total_xp < price:
        raise HTTPException(status_code=400, detail="XP insuficiente para suscribirse")

    # Deduct XP
    current_user.total_xp -= price
    db.add(XPTransaction(
        user_id=current_user.id,
        amount=-price,
        reason=XPReason.SUBSCRIPTION_PAYMENT,
        description=f"Suscripción al coach {coach.name}",
    ))

    sub = CoachSubscription(coach_id=coach_id, athlete_id=current_user.id, xp_per_month=price)
    db.add(sub)
    await db.flush()

    return CoachSubscriptionResponse(
        id=sub.id,
        coach_id=coach.id,
        coach_name=coach.name,
        coach_avatar_url=coach.avatar_url,
        xp_per_month=sub.xp_per_month,
        subscribed_at=sub.subscribed_at,
    )


@router.delete("/{coach_id}/subscribe", status_code=204)
async def unsubscribe_from_coach(
    coach_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.coach_id == coach_id,
            CoachSubscription.athlete_id == current_user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No estás suscrito a este coach")
    await db.delete(sub)


@router.get("/my-athletes", response_model=list[CoachSubscriberEntry])
async def list_my_athletes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Coach: list athletes currently subscribed to me."""
    if current_user.role != UserRole.COACH:
        raise HTTPException(status_code=403, detail="Solo coaches pueden acceder")
    rows = await db.execute(
        select(CoachSubscription, User)
        .join(User, User.id == CoachSubscription.athlete_id)
        .where(CoachSubscription.coach_id == current_user.id)
        .order_by(CoachSubscription.subscribed_at.desc())
    )
    return [
        CoachSubscriberEntry(
            athlete_id=athlete.id,
            athlete_name=athlete.name,
            xp_per_month=sub.xp_per_month,
            subscribed_at=sub.subscribed_at,
        )
        for sub, athlete in rows.all()
    ]


@router.get("/my-stats")
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Coach: aggregate statistics panel."""
    if current_user.role != UserRole.COACH:
        raise HTTPException(status_code=403, detail="Solo coaches pueden acceder")

    coach_id = current_user.id

    # Athletes subscribed
    total_athletes = (await db.execute(
        select(func.count(CoachSubscription.id)).where(CoachSubscription.coach_id == coach_id)
    )).scalar_one()

    # Monthly XP income
    xp_monthly = (await db.execute(
        select(func.coalesce(func.sum(CoachSubscription.xp_per_month), 0))
        .where(CoachSubscription.coach_id == coach_id)
    )).scalar_one()

    # Athlete IDs
    athlete_ids_result = await db.execute(
        select(CoachSubscription.athlete_id).where(CoachSubscription.coach_id == coach_id)
    )
    athlete_ids = [row[0] for row in athlete_ids_result.all()]

    # Sessions completed by all athletes in last 30 days
    since = datetime.now(timezone.utc) - timedelta(days=30)
    total_sessions_30d = 0
    if athlete_ids:
        total_sessions_30d = (await db.execute(
            select(func.count(WorkoutSession.id)).where(
                WorkoutSession.user_id.in_(athlete_ids),
                WorkoutSession.finished_at.is_not(None),
                WorkoutSession.started_at >= since,
            )
        )).scalar_one()

    # Messages
    total_messages = (await db.execute(
        select(func.count(CoachMessage.id)).where(CoachMessage.coach_id == coach_id)
    )).scalar_one()

    unread_messages = (await db.execute(
        select(func.count(CoachMessage.id)).where(
            CoachMessage.coach_id == coach_id,
            CoachMessage.read_at.is_(None),
        )
    )).scalar_one()

    return {
        "total_athletes": total_athletes,
        "xp_monthly_income": int(xp_monthly),
        "total_sessions_30d": total_sessions_30d,
        "total_messages": total_messages,
        "unread_messages": unread_messages,
    }


async def _require_subscriber(coach_id: int, athlete_id: int, db: AsyncSession) -> None:
    result = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.coach_id == coach_id,
            CoachSubscription.athlete_id == athlete_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Este atleta no está suscrito a ti")


@router.get("/my-athletes/{athlete_id}/sessions", response_model=list[SessionListResponse])
async def get_athlete_sessions_for_coach(
    athlete_id: int,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Coach: view recent sessions of a subscribed athlete."""
    if current_user.role != UserRole.COACH:
        raise HTTPException(status_code=403, detail="Solo coaches pueden acceder")
    await _require_subscriber(current_user.id, athlete_id, db)

    result = await db.execute(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == athlete_id)
        .order_by(WorkoutSession.started_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()

    response = []
    for session in sessions:
        counts = await db.execute(
            select(
                func.coalesce(func.sum(SessionSet.sets_count), func.count(SessionSet.id)),
                func.count(distinct(SessionSet.exercise_id)),
            ).where(SessionSet.session_id == session.id)
        )
        set_count, exercise_count = counts.one()
        has_records_result = await db.execute(
            select(exists(select(PersonalRecord.id).where(PersonalRecord.session_id == session.id)))
        )
        has_records = has_records_result.scalar_one()
        s = SessionListResponse.model_validate(session)
        s.set_count = set_count
        s.exercise_count = exercise_count
        s.has_records = has_records
        response.append(s)
    return response


@router.get("/my-athletes/{athlete_id}/stats")
async def get_athlete_stats_for_coach(
    athlete_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Coach: view 30-day training summary of a subscribed athlete."""
    if current_user.role != UserRole.COACH:
        raise HTTPException(status_code=403, detail="Solo coaches pueden acceder")
    await _require_subscriber(current_user.id, athlete_id, db)

    since = datetime.now(timezone.utc) - timedelta(days=30)

    def _base(q):
        return q.where(WorkoutSession.user_id == athlete_id, WorkoutSession.started_at >= since)

    sessions_count = (await db.execute(
        _base(select(func.count(WorkoutSession.id)).where(WorkoutSession.finished_at.is_not(None)))
    )).scalar_one()

    total_volume = (await db.execute(
        _base(
            select(func.sum(func.coalesce(SessionSet.reps, 0) * func.coalesce(SessionSet.weight_kg, 0)))
            .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
            .where(WorkoutSession.finished_at.is_not(None))
        )
    )).scalar_one() or 0

    total_sets = (await db.execute(
        _base(
            select(func.count(SessionSet.id))
            .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
            .where(WorkoutSession.finished_at.is_not(None))
        )
    )).scalar_one()

    total_time = (await db.execute(
        _base(select(func.sum(WorkoutSession.total_duration_sec)).where(WorkoutSession.finished_at.is_not(None)))
    )).scalar_one() or 0

    distinct_exercises = (await db.execute(
        _base(
            select(func.count(distinct(SessionSet.exercise_id)))
            .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
            .where(WorkoutSession.finished_at.is_not(None))
        )
    )).scalar_one()

    avg_rpe = (await db.execute(
        _base(
            select(func.avg(WorkoutSession.rpe))
            .where(WorkoutSession.finished_at.is_not(None), WorkoutSession.rpe.is_not(None))
        )
    )).scalar_one()

    return {
        "period": "month",
        "total_sessions": sessions_count,
        "total_volume_kg": round(float(total_volume), 2),
        "total_sets": total_sets,
        "total_time_sec": total_time,
        "distinct_exercises": distinct_exercises,
        "muscle_distribution": {},
        "avg_rpe": round(float(avg_rpe), 1) if avg_rpe else None,
    }


@router.get("/{coach_id}/subscribers", response_model=list[CoachSubscriberEntry])
async def list_coach_subscribers(
    coach_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Coach: see who is subscribed to me."""
    if current_user.id != coach_id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    rows = await db.execute(
        select(CoachSubscription, User)
        .join(User, User.id == CoachSubscription.athlete_id)
        .where(CoachSubscription.coach_id == coach_id)
        .order_by(CoachSubscription.subscribed_at.desc())
    )
    return [
        CoachSubscriberEntry(
            athlete_id=athlete.id,
            athlete_name=athlete.name,
            xp_per_month=sub.xp_per_month,
            subscribed_at=sub.subscribed_at,
        )
        for sub, athlete in rows.all()
    ]
