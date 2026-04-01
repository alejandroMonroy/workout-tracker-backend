from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import distinct, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.coach_athlete import CoachSubscription, CoachTier
from app.models.exercise import Exercise  # noqa: F401 – keep for stats query
from app.models.message import CoachMessage
from app.models.plan import Plan, PlanSubscription, PlanTag, PlanWorkout
from app.models.record import PersonalRecord
from app.models.session import SessionSet, WorkoutSession
from app.models.user import User, UserRole
from app.models.xp import XPReason, XPTransaction
from app.schemas.coaches import (
    CoachPublic,
    CoachSubscriberEntry,
    CoachSubscriptionResponse,
    CoachTierCreate,
    CoachTierResponse,
    CoachTierUpdate,
    SetPriceRequest,
    SubscribeRequest,
)
from app.schemas.session import SessionListResponse

router = APIRouter(prefix="/coaches", tags=["Coaches"])


# ── Helper ────────────────────────────────────────────────────────────────────

async def _build_coach_public(
    coach: User,
    plan_counts: dict[int, int],
    sub_counts: dict[int, int],
    subscribed_coach_ids: set[int],
    tiers_by_coach: dict[int, list[CoachTier]],
    current_tier_by_coach: dict[int, int | None] | None = None,
) -> CoachPublic:
    return CoachPublic(
        id=coach.id,
        name=coach.name,
        avatar_url=coach.avatar_url,
        subscription_xp_price=coach.subscription_xp_price,
        plan_count=plan_counts.get(coach.id, 0),
        subscriber_count=sub_counts.get(coach.id, 0),
        is_subscribed=coach.id in subscribed_coach_ids,
        current_tier_id=(current_tier_by_coach or {}).get(coach.id),
        tiers=[CoachTierResponse.model_validate(t) for t in tiers_by_coach.get(coach.id, [])],
    )


async def _load_coach_metrics(
    coach_ids: list[int],
    current_user_id: int,
    db: AsyncSession,
) -> tuple[dict[int, int], dict[int, int], set[int], dict[int, list[CoachTier]]]:
    """Returns (plan_counts, sub_counts, subscribed_coach_ids, tiers_by_coach)."""
    plan_counts_result = await db.execute(
        select(Plan.created_by, func.count(Plan.id))
        .where(Plan.created_by.in_(coach_ids))
        .group_by(Plan.created_by)
    )
    plan_counts = {row[0]: row[1] for row in plan_counts_result.all()}

    sub_counts_result = await db.execute(
        select(CoachSubscription.coach_id, func.count(CoachSubscription.id))
        .where(CoachSubscription.coach_id.in_(coach_ids))
        .group_by(CoachSubscription.coach_id)
    )
    sub_counts = {row[0]: row[1] for row in sub_counts_result.all()}

    subs_result = await db.execute(
        select(CoachSubscription.coach_id, CoachSubscription.tier_id).where(
            CoachSubscription.athlete_id == current_user_id
        )
    )
    subs_rows = subs_result.all()
    subscribed_coach_ids = {row[0] for row in subs_rows}
    current_tier_by_coach: dict[int, int | None] = {row[0]: row[1] for row in subs_rows}

    tiers_result = await db.execute(
        select(CoachTier)
        .options(selectinload(CoachTier.tags))
        .where(CoachTier.coach_id.in_(coach_ids))
        .order_by(CoachTier.xp_per_month)
    )
    tiers = tiers_result.scalars().all()
    tiers_by_coach: dict[int, list[CoachTier]] = {}
    for t in tiers:
        tiers_by_coach.setdefault(t.coach_id, []).append(t)

    return plan_counts, sub_counts, subscribed_coach_ids, tiers_by_coach, current_tier_by_coach


# ── Public coach listing ───────────────────────────────────────────────────────

@router.get("", response_model=list[CoachPublic])
async def list_coaches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List coaches that have at least one subscription tier."""
    coaches_result = await db.execute(
        select(User).where(
            User.role == UserRole.COACH,
            exists(select(CoachTier.id).where(CoachTier.coach_id == User.id)),
        )
    )
    coaches = coaches_result.scalars().all()
    if not coaches:
        return []

    coach_ids = [c.id for c in coaches]
    plan_counts, sub_counts, subscribed_coach_ids, tiers_by_coach, current_tier_by_coach = await _load_coach_metrics(
        coach_ids, current_user.id, db
    )

    return [
        await _build_coach_public(c, plan_counts, sub_counts, subscribed_coach_ids, tiers_by_coach, current_tier_by_coach)
        for c in coaches
    ]


@router.get("/me", response_model=CoachPublic)
async def get_my_coach_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.COACH:
        raise HTTPException(status_code=403, detail="Solo coaches pueden acceder a este recurso")

    plan_counts, sub_counts, _, tiers_by_coach, __ = await _load_coach_metrics(
        [current_user.id], current_user.id, db
    )
    return CoachPublic(
        id=current_user.id,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        subscription_xp_price=current_user.subscription_xp_price,
        plan_count=plan_counts.get(current_user.id, 0),
        subscriber_count=sub_counts.get(current_user.id, 0),
        is_subscribed=False,
        tiers=[CoachTierResponse.model_validate(t) for t in tiers_by_coach.get(current_user.id, [])],
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

    plan_counts, sub_counts, _, tiers_by_coach, __ = await _load_coach_metrics(
        [current_user.id], current_user.id, db
    )
    return CoachPublic(
        id=current_user.id,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        subscription_xp_price=current_user.subscription_xp_price,
        plan_count=plan_counts.get(current_user.id, 0),
        subscriber_count=sub_counts.get(current_user.id, 0),
        is_subscribed=False,
        tiers=[CoachTierResponse.model_validate(t) for t in tiers_by_coach.get(current_user.id, [])],
    )


# ── Tier management ───────────────────────────────────────────────────────────

@router.get("/me/tiers", response_model=list[CoachTierResponse])
async def list_my_tiers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.COACH:
        raise HTTPException(status_code=403, detail="Solo coaches pueden acceder")
    result = await db.execute(
        select(CoachTier)
        .options(selectinload(CoachTier.tags))
        .where(CoachTier.coach_id == current_user.id)
        .order_by(CoachTier.xp_per_month)
    )
    return result.scalars().all()


@router.post("/me/tiers", response_model=CoachTierResponse, status_code=status.HTTP_201_CREATED)
async def create_tier(
    data: CoachTierCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.COACH:
        raise HTTPException(status_code=403, detail="Solo coaches pueden crear tiers")

    tags: list[PlanTag] = []
    if data.tag_ids:
        tags_result = await db.execute(
            select(PlanTag).where(PlanTag.id.in_(data.tag_ids), PlanTag.created_by == current_user.id)
        )
        tags = list(tags_result.scalars().all())

    tier = CoachTier(
        coach_id=current_user.id,
        name=data.name.strip(),
        description=data.description,
        xp_per_month=data.xp_per_month,
        tags=tags,
    )
    db.add(tier)
    await db.flush()

    result = await db.execute(
        select(CoachTier).options(selectinload(CoachTier.tags)).where(CoachTier.id == tier.id)
    )
    return result.scalar_one()


@router.put("/me/tiers/{tier_id}", response_model=CoachTierResponse)
async def update_tier(
    tier_id: int,
    data: CoachTierUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CoachTier).options(selectinload(CoachTier.tags)).where(CoachTier.id == tier_id)
    )
    tier = result.scalar_one_or_none()
    if not tier:
        raise HTTPException(status_code=404, detail="Tier no encontrado")
    if tier.coach_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes editar este tier")

    update_data = data.model_dump(exclude_unset=True, exclude={"tag_ids"})
    for field, value in update_data.items():
        setattr(tier, field, value)

    if data.tag_ids is not None:
        if data.tag_ids:
            tags_result = await db.execute(
                select(PlanTag).where(PlanTag.id.in_(data.tag_ids), PlanTag.created_by == current_user.id)
            )
            tier.tags = list(tags_result.scalars().all())
        else:
            tier.tags = []

    await db.flush()
    result = await db.execute(
        select(CoachTier).options(selectinload(CoachTier.tags)).where(CoachTier.id == tier.id)
    )
    return result.scalar_one()


@router.delete("/me/tiers/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tier(
    tier_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CoachTier).where(CoachTier.id == tier_id))
    tier = result.scalar_one_or_none()
    if not tier:
        raise HTTPException(status_code=404, detail="Tier no encontrado")
    if tier.coach_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar este tier")
    await db.delete(tier)


# ── Subscriptions ─────────────────────────────────────────────────────────────

@router.get("/subscriptions", response_model=list[CoachSubscriptionResponse])
async def list_my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete: list all coaches I'm subscribed to."""
    rows = await db.execute(
        select(CoachSubscription, User)
        .options(selectinload(CoachSubscription.tier).selectinload(CoachTier.tags))
        .join(User, User.id == CoachSubscription.coach_id)
        .where(CoachSubscription.athlete_id == current_user.id)
        .order_by(CoachSubscription.subscribed_at.desc())
    )
    results = []
    for sub, coach in rows.all():
        tier = CoachTierResponse.model_validate(sub.tier) if sub.tier else None
        results.append(CoachSubscriptionResponse(
            id=sub.id,
            coach_id=coach.id,
            coach_name=coach.name,
            coach_avatar_url=coach.avatar_url,
            xp_per_month=sub.xp_per_month,
            subscribed_at=sub.subscribed_at,
            tier=tier,
        ))
    return results


@router.post("/{coach_id}/subscribe", response_model=CoachSubscriptionResponse)
async def subscribe_to_coach(
    coach_id: int,
    data: SubscribeRequest = SubscribeRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    coach = await db.get(User, coach_id)
    if not coach or coach.role != UserRole.COACH:
        raise HTTPException(status_code=404, detail="Coach no encontrado")
    if coach_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes suscribirte a ti mismo")

    # Resolve tier
    tier: CoachTier | None = None
    if data.tier_id is not None:
        tier_result = await db.execute(
            select(CoachTier).options(selectinload(CoachTier.tags)).where(CoachTier.id == data.tier_id)
        )
        tier = tier_result.scalar_one_or_none()
        if not tier or tier.coach_id != coach_id:
            raise HTTPException(status_code=404, detail="Tier no encontrado")
        price = tier.xp_per_month
    else:
        # Fall back to flat price
        if coach.subscription_xp_price is None:
            raise HTTPException(status_code=400, detail="Este coach no ha habilitado suscripciones")
        price = coach.subscription_xp_price

    existing = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.coach_id == coach_id,
            CoachSubscription.athlete_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya estás suscrito a este coach")

    if current_user.total_xp < price:
        raise HTTPException(status_code=400, detail="XP insuficiente para suscribirse")

    current_user.total_xp -= price
    db.add(XPTransaction(
        user_id=current_user.id,
        amount=-price,
        reason=XPReason.SUBSCRIPTION_PAYMENT,
        description=f"Suscripción al coach {coach.name}",
    ))

    sub = CoachSubscription(
        coach_id=coach_id,
        athlete_id=current_user.id,
        xp_per_month=price,
        tier_id=tier.id if tier else None,
    )
    db.add(sub)
    await db.flush()

    tier_response = CoachTierResponse.model_validate(tier) if tier else None
    return CoachSubscriptionResponse(
        id=sub.id,
        coach_id=coach.id,
        coach_name=coach.name,
        coach_avatar_url=coach.avatar_url,
        xp_per_month=sub.xp_per_month,
        subscribed_at=sub.subscribed_at,
        tier=tier_response,
    )


@router.patch("/{coach_id}/subscribe", response_model=CoachSubscriptionResponse)
async def change_coach_tier(
    coach_id: int,
    data: SubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete: change the tier on an existing coach subscription."""
    sub_result = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.coach_id == coach_id,
            CoachSubscription.athlete_id == current_user.id,
        )
    )
    sub = sub_result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No estás suscrito a este coach")

    if data.tier_id is None:
        raise HTTPException(status_code=400, detail="Debes indicar un tier")

    tier_result = await db.execute(
        select(CoachTier).options(selectinload(CoachTier.tags)).where(CoachTier.id == data.tier_id)
    )
    tier = tier_result.scalar_one_or_none()
    if not tier or tier.coach_id != coach_id:
        raise HTTPException(status_code=404, detail="Tier no encontrado")

    if tier.id == sub.tier_id:
        raise HTTPException(status_code=400, detail="Ya estás suscrito a este tier")

    # Only charge extra XP when upgrading — no refunds on downgrade
    price_diff = tier.xp_per_month - sub.xp_per_month
    if price_diff > 0:
        if current_user.total_xp < price_diff:
            raise HTTPException(status_code=400, detail="XP insuficiente para cambiar de tier")
        current_user.total_xp -= price_diff
        db.add(XPTransaction(
            user_id=current_user.id,
            amount=-price_diff,
            reason=XPReason.SUBSCRIPTION_PAYMENT,
            description=f"Cambio de tier al coach — {tier.name}",
        ))

    sub.tier_id = tier.id
    sub.xp_per_month = tier.xp_per_month

    # Unsubscribe plans no longer accessible with the new tier.
    # If the new tier has no tag restrictions it grants full access — nothing to revoke.
    new_tier_tag_ids = {t.id for t in tier.tags}
    if new_tier_tag_ids:
        # Find private plan subscriptions from this coach
        subs_result = await db.execute(
            select(PlanSubscription)
            .join(Plan, Plan.id == PlanSubscription.plan_id)
            .where(
                PlanSubscription.athlete_id == current_user.id,
                Plan.created_by == coach_id,
                Plan.is_public.is_(False),
            )
        )
        plan_subs = subs_result.scalars().all()

        if plan_subs:
            plan_ids = [ps.plan_id for ps in plan_subs]
            plans_result = await db.execute(
                select(Plan).options(selectinload(Plan.tags)).where(Plan.id.in_(plan_ids))
            )
            plans_by_id = {p.id: p for p in plans_result.scalars().all()}

            for ps in plan_subs:
                plan = plans_by_id.get(ps.plan_id)
                if plan:
                    plan_tag_ids = {t.id for t in plan.tags}
                    if not (plan_tag_ids and plan_tag_ids & new_tier_tag_ids):
                        await db.delete(ps)

    await db.flush()

    coach = await db.get(User, coach_id)
    return CoachSubscriptionResponse(
        id=sub.id,
        coach_id=coach_id,
        coach_name=coach.name,
        coach_avatar_url=coach.avatar_url,
        xp_per_month=sub.xp_per_month,
        subscribed_at=sub.subscribed_at,
        tier=CoachTierResponse.model_validate(tier),
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
        .options(selectinload(CoachSubscription.tier))
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
            tier_name=sub.tier.name if sub.tier else None,
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

    total_athletes = (await db.execute(
        select(func.count(CoachSubscription.id)).where(CoachSubscription.coach_id == coach_id)
    )).scalar_one()

    xp_monthly = (await db.execute(
        select(func.coalesce(func.sum(CoachSubscription.xp_per_month), 0))
        .where(CoachSubscription.coach_id == coach_id)
    )).scalar_one()

    athlete_ids_result = await db.execute(
        select(CoachSubscription.athlete_id).where(CoachSubscription.coach_id == coach_id)
    )
    athlete_ids = [row[0] for row in athlete_ids_result.all()]

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
        .join(PlanWorkout, WorkoutSession.plan_workout_id == PlanWorkout.id)
        .join(Plan, PlanWorkout.plan_id == Plan.id)
        .where(
            WorkoutSession.user_id == athlete_id,
            Plan.created_by == current_user.id,
        )
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
    if current_user.id != coach_id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    rows = await db.execute(
        select(CoachSubscription, User)
        .options(selectinload(CoachSubscription.tier))
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
            tier_name=sub.tier.name if sub.tier else None,
        )
        for sub, athlete in rows.all()
    ]
