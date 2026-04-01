from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.coach_athlete import CoachSubscription, CoachTier
from app.models.plan import Plan, PlanSubscription, PlanTag, PlanWorkout
from app.models.session import WorkoutSession
from app.models.template import TemplateBlock, WorkoutTemplate
from app.models.user import User
from app.schemas.plan import PlanCreate, PlanResponse, PlanSubscriberResponse, PlanUpdate

router = APIRouter(prefix="/plans", tags=["Plans"])

_PLAN_OPTIONS = [
    selectinload(Plan.workouts).selectinload(PlanWorkout.template).selectinload(
        WorkoutTemplate.blocks
    ).selectinload(TemplateBlock.exercise),
    selectinload(Plan.tags),
]


def _with_sub(plan: Plan, subscription_id: int | None, creator_name: str = "") -> PlanResponse:
    return PlanResponse.model_validate(plan).model_copy(
        update={"subscription_id": subscription_id, "creator_name": creator_name}
    )


async def _sub_map(user_id: int, db: AsyncSession) -> dict[int, int]:
    """Return {plan_id: subscription_id} for the given user."""
    res = await db.execute(
        select(PlanSubscription.plan_id, PlanSubscription.id).where(
            PlanSubscription.athlete_id == user_id
        )
    )
    return {row[0]: row[1] for row in res.all()}


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    mine_only: bool = Query(False),
    subscribed_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if subscribed_only:
        query = (
            select(Plan)
            .options(*_PLAN_OPTIONS)
            .join(PlanSubscription, PlanSubscription.plan_id == Plan.id)
            .where(PlanSubscription.athlete_id == current_user.id)
            .order_by(Plan.id.desc()).limit(limit).offset(offset)
        )
        result = await db.execute(query)
        plans = result.scalars().unique().all()
    elif mine_only:
        query = (
            select(Plan)
            .options(*_PLAN_OPTIONS)
            .where(Plan.created_by == current_user.id)
            .order_by(Plan.id.desc()).limit(limit).offset(offset)
        )
        result = await db.execute(query)
        plans = result.scalars().unique().all()
    else:
        # Build tier-based access map for subscribed coaches
        subs_result = await db.execute(
            select(CoachSubscription)
            .options(selectinload(CoachSubscription.tier).selectinload(CoachTier.tags))
            .where(CoachSubscription.athlete_id == current_user.id)
        )
        coach_subs = subs_result.scalars().all()

        # access_map: coach_id -> None (all plans) or set[tag_id] (only plans with these tags)
        access_map: dict[int, set[int] | None] = {}
        for sub in coach_subs:
            if sub.tier is None or len(sub.tier.tags) == 0:
                access_map[sub.coach_id] = None
            else:
                tier_tags = {t.id for t in sub.tier.tags}
                if sub.coach_id not in access_map:
                    access_map[sub.coach_id] = tier_tags
                elif access_map[sub.coach_id] is not None:
                    # union tags (multiple tiers); None means full access — don't downgrade
                    access_map[sub.coach_id] = access_map[sub.coach_id] | tier_tags

        all_access_ids = [cid for cid, v in access_map.items() if v is None]
        restricted_ids = [cid for cid, v in access_map.items() if v is not None]

        where_parts = [Plan.is_public.is_(True), Plan.created_by == current_user.id]
        if all_access_ids:
            where_parts.append(Plan.created_by.in_(all_access_ids))
        if restricted_ids:
            where_parts.append(Plan.created_by.in_(restricted_ids))

        result = await db.execute(
            select(Plan).options(*_PLAN_OPTIONS)
            .where(or_(*where_parts))
            .order_by(Plan.id.desc())
        )
        all_plans = result.scalars().unique().all()

        # Python-side filter for tag-restricted coaches
        filtered: list[Plan] = []
        for plan in all_plans:
            if plan.is_public or plan.created_by == current_user.id:
                filtered.append(plan)
            elif plan.created_by in all_access_ids:
                filtered.append(plan)
            elif plan.created_by in restricted_ids:
                plan_tag_ids = {t.id for t in plan.tags}
                tier_tag_ids = access_map[plan.created_by]
                if plan_tag_ids and plan_tag_ids & tier_tag_ids:
                    filtered.append(plan)

        plans = filtered[offset: offset + limit]

    subs = await _sub_map(current_user.id, db)
    creator_ids = {p.created_by for p in plans}
    names_result = await db.execute(
        select(User.id, User.name).where(User.id.in_(creator_ids))
    )
    name_map: dict[int, str] = {row[0]: row[1] for row in names_result.all()}
    return [_with_sub(p, subs.get(p.id), name_map.get(p.created_by, "")) for p in plans]


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan).options(*_PLAN_OPTIONS).where(Plan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if not plan.is_public and plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este plan")

    subs = await _sub_map(current_user.id, db)
    return _with_sub(plan, subs.get(plan.id))


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    data: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.workouts:
        template_ids = [w.template_id for w in data.workouts]
        res = await db.execute(
            select(WorkoutTemplate.id).where(WorkoutTemplate.id.in_(template_ids))
        )
        found = set(res.scalars().all())
        missing = set(template_ids) - found
        if missing:
            raise HTTPException(status_code=400, detail=f"Workouts no encontrados: {missing}")

    plan = Plan(
        name=data.name,
        description=data.description,
        is_public=data.is_public,
        created_by=current_user.id,
    )
    db.add(plan)
    await db.flush()

    for w in data.workouts:
        db.add(PlanWorkout(
            plan_id=plan.id,
            template_id=w.template_id,
            order=w.order,
            day=w.day,
            notes=w.notes,
        ))

    await db.refresh(plan, attribute_names=["tags"])

    if data.tag_ids:
        tags_res = await db.execute(
            select(PlanTag).where(PlanTag.id.in_(data.tag_ids), PlanTag.created_by == current_user.id)
        )
        plan.tags = list(tags_res.scalars().all())

    await db.flush()
    result = await db.execute(
        select(Plan).options(*_PLAN_OPTIONS).where(Plan.id == plan.id)
        .execution_options(populate_existing=True)
    )
    return _with_sub(result.scalar_one(), None)


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    data: PlanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan).options(selectinload(Plan.workouts), selectinload(Plan.tags)).where(Plan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes editar este plan")

    update_data = data.model_dump(exclude_unset=True, exclude={"workouts", "tag_ids"})
    for field, value in update_data.items():
        setattr(plan, field, value)

    if data.tag_ids is not None:
        if data.tag_ids:
            tags_res = await db.execute(
                select(PlanTag).where(PlanTag.id.in_(data.tag_ids), PlanTag.created_by == current_user.id)
            )
            plan.tags = list(tags_res.scalars().all())
        else:
            plan.tags = []

    if data.workouts is not None:
        if data.workouts:
            template_ids = [w.template_id for w in data.workouts]
            res = await db.execute(
                select(WorkoutTemplate.id).where(WorkoutTemplate.id.in_(template_ids))
            )
            found = set(res.scalars().all())
            missing = set(template_ids) - found
            if missing:
                raise HTTPException(
                    status_code=400, detail=f"Workouts no encontrados: {missing}"
                )

        for pw in plan.workouts:
            await db.delete(pw)
        await db.flush()

        for w in data.workouts:
            db.add(PlanWorkout(
                plan_id=plan.id,
                template_id=w.template_id,
                order=w.order,
                day=w.day,
                notes=w.notes,
            ))

    await db.flush()
    result = await db.execute(
        select(Plan).options(*_PLAN_OPTIONS).where(Plan.id == plan.id)
        .execution_options(populate_existing=True)
    )
    subs = await _sub_map(current_user.id, db)
    return _with_sub(result.scalar_one(), subs.get(plan.id))


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar este plan")
    await db.delete(plan)


# ── Subscriptions ──────────────────────────────────────────────────────────────

@router.post("/{plan_id}/subscribe", response_model=PlanResponse)
async def subscribe_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan).options(*_PLAN_OPTIONS).where(Plan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    if not plan.is_public and plan.created_by != current_user.id:
        # Check if athlete has coach access to this plan
        sub_res = await db.execute(
            select(CoachSubscription)
            .options(selectinload(CoachSubscription.tier).selectinload(CoachTier.tags))
            .where(
                CoachSubscription.athlete_id == current_user.id,
                CoachSubscription.coach_id == plan.created_by,
            )
        )
        coach_sub = sub_res.scalar_one_or_none()
        has_access = False
        if coach_sub is not None:
            if coach_sub.tier is None or len(coach_sub.tier.tags) == 0:
                has_access = True
            else:
                plan_tag_ids = {t.id for t in plan.tags}
                tier_tag_ids = {t.id for t in coach_sub.tier.tags}
                has_access = bool(plan_tag_ids and plan_tag_ids & tier_tag_ids)
        if not has_access:
            raise HTTPException(status_code=403, detail="Este plan no es público")

    existing = await db.execute(
        select(PlanSubscription).where(
            PlanSubscription.plan_id == plan_id,
            PlanSubscription.athlete_id == current_user.id,
        )
    )
    sub = existing.scalar_one_or_none()
    if sub:
        return _with_sub(plan, sub.id)

    new_sub = PlanSubscription(plan_id=plan_id, athlete_id=current_user.id)
    db.add(new_sub)
    await db.flush()
    return _with_sub(plan, new_sub.id)


@router.delete("/{plan_id}/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlanSubscription).where(
            PlanSubscription.plan_id == plan_id,
            PlanSubscription.athlete_id == current_user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No estás suscrito a este plan")
    await db.delete(sub)


@router.get("/{plan_id}/subscribers", response_model=list[PlanSubscriberResponse])
async def list_plan_subscribers(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta información")

    rows = await db.execute(
        select(PlanSubscription, User)
        .join(User, User.id == PlanSubscription.athlete_id)
        .where(PlanSubscription.plan_id == plan_id)
        .order_by(PlanSubscription.subscribed_at.desc())
    )
    return [
        PlanSubscriberResponse(
            subscription_id=sub.id,
            athlete_id=athlete.id,
            athlete_name=athlete.name,
            athlete_email=athlete.email,
            subscribed_at=sub.subscribed_at,
        )
        for sub, athlete in rows.all()
    ]


@router.get("/{plan_id}/progress", response_model=list[int])
async def get_plan_progress(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return list of plan_workout_ids completed (finished sessions) by the current user for this plan."""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    plan_workout_ids_result = await db.execute(
        select(PlanWorkout.id).where(PlanWorkout.plan_id == plan_id)
    )
    plan_workout_ids = [row[0] for row in plan_workout_ids_result.all()]
    if not plan_workout_ids:
        return []

    rows = await db.execute(
        select(WorkoutSession.plan_workout_id).where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.plan_workout_id.in_(plan_workout_ids),
            WorkoutSession.finished_at.is_not(None),
        )
    )
    return list({row[0] for row in rows.all()})
