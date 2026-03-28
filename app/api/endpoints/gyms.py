"""Gym endpoints — owner management + athlete-facing public routes."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import decode_token
from app.websockets.manager import live_manager
from app.models.gym import (
    BookingStatus,
    ClassBooking,
    ClassWaitlist,
    Gym,
    GymClassBlockType,
    GymClassLiveStatus,
    GymClassSchedule,
    GymClassTemplate,
    GymClassWorkout,
    GymClassWorkoutBlock,
    GymClassWorkoutExercise,
    GymLocation,
    GymMembership,
    GymSubscriptionPlan,
    GymTicketWallet,
    GymWeeklySlot,
    MembershipStatus,
    PlanType,
)
from app.models.record import PersonalRecord, RecordType
from app.models.session import SessionSet, SessionType, WorkoutSession
from app.models.user import User, UserRole
from app.models.xp import XPReason, XPTransaction
from app.schemas.gym import (
    BookingPublic,
    ClassLiveStatePublic,
    ClassSessionSaveRequest,
    ClassTemplateCreate,
    ClassTemplatePublic,
    ClassTemplateUpdate,
    GymAnalytics,
    GymClassWorkoutBlockPublic,
    GymClassWorkoutCreate,
    GymClassWorkoutExercisePublic,
    GymClassWorkoutPublic,
    GymClassWorkoutUpdate,
    GymCreate,
    GymPublic,
    GymUpdate,
    LocationCreate,
    LocationPublic,
    LocationUpdate,
    MemberPublic,
    MembershipPublic,
    TicketPurchasePublic,
    PlanCreate,
    PlanPublic,
    PlanUpdate,
    ScheduleCreate,
    SchedulePublic,
    ScheduleUpdate,
    WeeklySlotCreate,
    WeeklySlotPublic,
)
from app.schemas.session import SessionResponse
from app.services.xp import award_session_xp

router = APIRouter(prefix="/gyms", tags=["Gyms"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _require_gym_owner(current_user: User) -> None:
    if current_user.role != UserRole.GYM:
        raise HTTPException(status_code=403, detail="Solo gimnasios pueden acceder a esta función")


async def _get_gym_or_404(db: AsyncSession, gym_id: int, owner_id: int | None = None) -> Gym:
    result = await db.execute(select(Gym).where(Gym.id == gym_id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")
    if owner_id is not None and gym.owner_id != owner_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para este gimnasio")
    return gym


async def _get_or_create_wallet(db: AsyncSession, user_id: int, gym_id: int) -> GymTicketWallet:
    res = await db.execute(
        select(GymTicketWallet).where(
            GymTicketWallet.user_id == user_id,
            GymTicketWallet.gym_id == gym_id,
        )
    )
    wallet = res.scalar_one_or_none()
    if not wallet:
        wallet = GymTicketWallet(user_id=user_id, gym_id=gym_id, tickets_remaining=0)
        db.add(wallet)
        await db.flush()
    return wallet


async def _count_confirmed_bookings(db: AsyncSession, schedule_id: int) -> int:
    result = await db.execute(
        select(func.count(ClassBooking.id)).where(
            ClassBooking.schedule_id == schedule_id,
            ClassBooking.status == BookingStatus.CONFIRMED,
        )
    )
    return result.scalar_one()


async def _enrich_schedule(
    db: AsyncSession, schedule: GymClassSchedule, current_user_id: int | None = None
) -> SchedulePublic:
    booked = await _count_confirmed_bookings(db, schedule.id)
    capacity = schedule.effective_capacity

    user_booking_status = None
    user_on_waitlist = False
    user_waitlist_position = None

    wl_count_res = await db.execute(
        select(func.count(ClassWaitlist.id)).where(ClassWaitlist.schedule_id == schedule.id)
    )
    waitlist_count = wl_count_res.scalar_one()

    if current_user_id:
        b_res = await db.execute(
            select(ClassBooking).where(
                ClassBooking.schedule_id == schedule.id,
                ClassBooking.user_id == current_user_id,
                ClassBooking.status != BookingStatus.CANCELLED,
            )
        )
        booking = b_res.scalar_one_or_none()
        if booking:
            user_booking_status = booking.status
        else:
            w_res = await db.execute(
                select(ClassWaitlist).where(
                    ClassWaitlist.schedule_id == schedule.id,
                    ClassWaitlist.user_id == current_user_id,
                )
            )
            wl = w_res.scalar_one_or_none()
            if wl:
                user_on_waitlist = True
                user_waitlist_position = wl.position

    return SchedulePublic(
        id=schedule.id,
        template_id=schedule.template_id,
        location_id=schedule.location_id,
        starts_at=schedule.starts_at,
        ends_at=schedule.ends_at,
        override_capacity=schedule.override_capacity,
        is_cancelled=schedule.is_cancelled,
        template_name=schedule.template.name if schedule.template else None,
        location_name=schedule.location.name if schedule.location else None,
        gym_name=schedule.location.gym.name if schedule.location and schedule.location.gym else None,
        gym_id=schedule.location.gym_id if schedule.location else None,
        booked_count=booked,
        effective_capacity=capacity,
        tickets_cost=schedule.template.tickets_cost if schedule.template else 1,
        user_booking_status=user_booking_status,
        user_on_waitlist=user_on_waitlist,
        user_waitlist_position=user_waitlist_position,
        waitlist_count=waitlist_count,
        workout_id=getattr(schedule, "workout_id", None),
        live_status=getattr(schedule, "live_status", GymClassLiveStatus.PENDING),
    )


async def _auto_renew_if_needed(db: AsyncSession, membership: GymMembership) -> None:
    """Lazy auto-renewal: if expired + auto_renew, charge XP and extend."""
    if membership.status != MembershipStatus.ACTIVE or not membership.expires_at:
        return
    now = datetime.now(timezone.utc)
    if membership.expires_at > now:
        return
    if not membership.auto_renew or not membership.plan_id:
        membership.status = MembershipStatus.EXPIRED
        await db.flush()
        return

    plan = await db.get(GymSubscriptionPlan, membership.plan_id)
    if not plan or not plan.is_active:
        membership.status = MembershipStatus.EXPIRED
        await db.flush()
        return

    user = await db.get(User, membership.user_id)
    if not user or user.total_xp < plan.xp_price:
        membership.status = MembershipStatus.EXPIRED
        await db.flush()
        return

    # Deduct XP
    user.total_xp -= plan.xp_price
    xp_tx = XPTransaction(
        user_id=user.id,
        amount=-plan.xp_price,
        reason=XPReason.SUBSCRIPTION_PAYMENT,
        description=f"Renovación automática: {plan.name}",
    )
    db.add(xp_tx)

    # Reset membership period (approximate months/years with timedelta)
    if plan.plan_type == PlanType.MONTHLY:
        membership.expires_at = membership.expires_at + timedelta(days=30)
    elif plan.plan_type == PlanType.ANNUAL:
        membership.expires_at = membership.expires_at + timedelta(days=365)
    elif plan.plan_type == PlanType.TICKETS:
        membership.tickets_remaining = (membership.tickets_remaining or 0) + (plan.ticket_count or 0)
        membership.expires_at = None

    membership.sessions_used_this_period = 0
    await db.flush()


# ─── Public directory ─────────────────────────────────────────────────────────

@router.get("", response_model=list[GymPublic])
async def list_gyms(
    search: str = Query("", max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Public gym directory — any authenticated user can browse."""
    q = select(Gym)
    if search:
        q = q.where(Gym.name.ilike(f"%{search}%"))
    result = await db.execute(q.order_by(Gym.name))
    return result.scalars().all()


# ─── Gym owner: my gym ────────────────────────────────────────────────────────

@router.post("/mine", response_model=GymPublic, status_code=201)
async def create_gym(
    body: GymCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    existing = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya tienes un gimnasio registrado")
    gym = Gym(owner_id=current_user.id, **body.model_dump())
    db.add(gym)
    await db.commit()
    await db.refresh(gym)
    return gym


@router.get("/mine", response_model=GymPublic)
async def get_my_gym(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Aún no has creado tu gimnasio")
    return gym


@router.patch("/mine", response_model=GymPublic)
async def update_my_gym(
    body: GymUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Aún no has creado tu gimnasio")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(gym, field, value)
    await db.commit()
    await db.refresh(gym)
    return gym


# ─── Gym owner: locations ─────────────────────────────────────────────────────

@router.post("/mine/locations", response_model=LocationPublic, status_code=201)
async def add_location(
    body: LocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Crea tu gimnasio primero")
    loc = GymLocation(gym_id=gym.id, **body.model_dump())
    db.add(loc)
    await db.commit()
    await db.refresh(loc)
    return loc


@router.get("/mine/locations", response_model=list[LocationPublic])
async def list_my_locations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        return []
    res = await db.execute(select(GymLocation).where(GymLocation.gym_id == gym.id))
    return res.scalars().all()


@router.patch("/mine/locations/{loc_id}", response_model=LocationPublic)
async def update_location(
    loc_id: int,
    body: LocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")
    res = await db.execute(
        select(GymLocation).where(GymLocation.id == loc_id, GymLocation.gym_id == gym.id)
    )
    loc = res.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Sede no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(loc, field, value)
    await db.commit()
    await db.refresh(loc)
    return loc


# ─── Gym owner: plans ─────────────────────────────────────────────────────────

@router.post("/mine/plans", response_model=PlanPublic, status_code=201)
async def create_plan(
    body: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Crea tu gimnasio primero")
    plan = GymSubscriptionPlan(gym_id=gym.id, **body.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get("/mine/plans", response_model=list[PlanPublic])
async def list_my_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        return []
    res = await db.execute(
        select(GymSubscriptionPlan).where(GymSubscriptionPlan.gym_id == gym.id)
    )
    return res.scalars().all()


@router.patch("/mine/plans/{plan_id}", response_model=PlanPublic)
async def update_plan(
    plan_id: int,
    body: PlanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")
    res = await db.execute(
        select(GymSubscriptionPlan).where(
            GymSubscriptionPlan.id == plan_id,
            GymSubscriptionPlan.gym_id == gym.id,
        )
    )
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(plan, field, value)
    await db.commit()
    await db.refresh(plan)
    return plan


# ─── Gym owner: class templates ───────────────────────────────────────────────

@router.post("/mine/templates", response_model=ClassTemplatePublic, status_code=201)
async def create_template(
    body: ClassTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Crea tu gimnasio primero")
    tmpl = GymClassTemplate(gym_id=gym.id, **body.model_dump())
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.get("/mine/templates", response_model=list[ClassTemplatePublic])
async def list_my_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        return []
    res = await db.execute(
        select(GymClassTemplate).where(GymClassTemplate.gym_id == gym.id)
    )
    return res.scalars().all()


@router.patch("/mine/templates/{tmpl_id}", response_model=ClassTemplatePublic)
async def update_template(
    tmpl_id: int,
    body: ClassTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")
    res = await db.execute(
        select(GymClassTemplate).where(
            GymClassTemplate.id == tmpl_id,
            GymClassTemplate.gym_id == gym.id,
        )
    )
    tmpl = res.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(tmpl, field, value)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


# ─── Gym owner: schedules ─────────────────────────────────────────────────────

@router.post("/mine/schedules", response_model=SchedulePublic, status_code=201)
async def create_schedule(
    body: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Crea tu gimnasio primero")
    # Verify template and location belong to this gym
    tmpl_res = await db.execute(
        select(GymClassTemplate).where(
            GymClassTemplate.id == body.template_id,
            GymClassTemplate.gym_id == gym.id,
        )
    )
    if not tmpl_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    loc_res = await db.execute(
        select(GymLocation).where(
            GymLocation.id == body.location_id,
            GymLocation.gym_id == gym.id,
        )
    )
    if not loc_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Sede no encontrada")

    sched = GymClassSchedule(**body.model_dump())
    db.add(sched)
    await db.flush()

    # Reload with relationships
    res = await db.execute(
        select(GymClassSchedule)
        .where(GymClassSchedule.id == sched.id)
        .options(
            selectinload(GymClassSchedule.template),
            selectinload(GymClassSchedule.location).selectinload(GymLocation.gym),
        )
    )
    sched = res.scalar_one()
    await db.commit()
    return await _enrich_schedule(db, sched)


@router.get("/mine/schedules", response_model=list[SchedulePublic])
async def list_my_schedules(
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        return []

    now = datetime.now(timezone.utc)
    q = (
        select(GymClassSchedule)
        .join(GymClassSchedule.template)
        .where(
            GymClassTemplate.gym_id == gym.id,
            GymClassSchedule.starts_at >= (from_dt or now),
        )
        .options(
            selectinload(GymClassSchedule.template),
            selectinload(GymClassSchedule.location).selectinload(GymLocation.gym),
        )
        .order_by(GymClassSchedule.starts_at)
    )
    if to_dt:
        q = q.where(GymClassSchedule.starts_at <= to_dt)
    res = await db.execute(q)
    schedules = res.scalars().all()
    return [await _enrich_schedule(db, s) for s in schedules]


@router.patch("/mine/schedules/{sched_id}", response_model=SchedulePublic)
async def update_schedule(
    sched_id: int,
    body: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")

    res = await db.execute(
        select(GymClassSchedule)
        .join(GymClassSchedule.template)
        .where(GymClassSchedule.id == sched_id, GymClassTemplate.gym_id == gym.id)
        .options(
            selectinload(GymClassSchedule.template),
            selectinload(GymClassSchedule.location).selectinload(GymLocation.gym),
        )
    )
    sched = res.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(sched, field, value)
    await db.commit()
    await db.refresh(sched)
    return await _enrich_schedule(db, sched)


# ─── Gym owner: members ───────────────────────────────────────────────────────

@router.get("/mine/members", response_model=list[MemberPublic])
async def list_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        return []

    res = await db.execute(
        select(GymMembership)
        .where(GymMembership.gym_id == gym.id)
        .options(
            selectinload(GymMembership.user),
            selectinload(GymMembership.plan),
        )
    )
    memberships = res.scalars().all()
    out = []
    for m in memberships:
        out.append(
            MemberPublic(
                membership_id=m.id,
                user_id=m.user_id,
                user_name=m.user.name,
                user_email=m.user.email,
                avatar_url=m.user.avatar_url,
                plan_name=m.plan.name if m.plan else None,
                status=m.status,
                tickets_remaining=m.tickets_remaining,
                sessions_used_this_period=m.sessions_used_this_period,
                started_at=m.started_at,
                expires_at=m.expires_at,
            )
        )
    return out


@router.post("/mine/members/{membership_id}/cancel")
async def owner_cancel_membership(
    membership_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")
    res = await db.execute(
        select(GymMembership).where(
            GymMembership.id == membership_id,
            GymMembership.gym_id == gym.id,
        )
    )
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Membresía no encontrada")
    if m.status == MembershipStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Ya está cancelada")
    m.status = MembershipStatus.CANCELLED
    m.auto_renew = False
    await db.commit()
    return {"ok": True}


@router.get("/mine/members/{user_id}/ticket-purchases", response_model=list[TicketPurchasePublic])
async def member_ticket_purchases(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        return []

    plans_res = await db.execute(
        select(GymSubscriptionPlan).where(
            GymSubscriptionPlan.gym_id == gym.id,
            GymSubscriptionPlan.plan_type == PlanType.TICKETS,
        )
    )
    ticket_plans = {p.name: p.ticket_count for p in plans_res.scalars().all()}

    txs_res = await db.execute(
        select(XPTransaction).where(
            XPTransaction.user_id == user_id,
            XPTransaction.reason == XPReason.SUBSCRIPTION_PAYMENT,
        ).order_by(XPTransaction.created_at.desc())
    )
    txs = txs_res.scalars().all()

    prefix = f"Suscripción: {gym.name} – "
    out = []
    for tx in txs:
        if tx.description and tx.description.startswith(prefix):
            plan_name = tx.description[len(prefix):]
            if plan_name in ticket_plans:
                out.append(TicketPurchasePublic(
                    purchased_at=tx.created_at,
                    plan_name=plan_name,
                    tickets_bought=ticket_plans[plan_name],
                    xp_spent=abs(tx.amount),
                ))
    return out


# ─── Gym owner: check-in ─────────────────────────────────────────────────────

@router.post("/mine/schedules/{sched_id}/checkin/{user_id}", response_model=BookingPublic)
async def check_in_user(
    sched_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")

    res = await db.execute(
        select(ClassBooking).where(
            ClassBooking.schedule_id == sched_id,
            ClassBooking.user_id == user_id,
            ClassBooking.status == BookingStatus.CONFIRMED,
        )
    )
    booking = res.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    booking.status = BookingStatus.ATTENDED
    booking.checked_in_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(booking)
    return booking


# ─── Gym owner: analytics ────────────────────────────────────────────────────

@router.get("/mine/analytics", response_model=GymAnalytics)
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")

    total_res = await db.execute(
        select(func.count(GymMembership.id)).where(GymMembership.gym_id == gym.id)
    )
    total_members = total_res.scalar_one()

    active_res = await db.execute(
        select(func.count(GymMembership.id)).where(
            GymMembership.gym_id == gym.id,
            GymMembership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.TRIAL]),
        )
    )
    active_members = active_res.scalar_one()

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    classes_res = await db.execute(
        select(func.count(GymClassSchedule.id))
        .join(GymClassSchedule.template)
        .where(
            GymClassTemplate.gym_id == gym.id,
            GymClassSchedule.starts_at >= month_start,
            GymClassSchedule.is_cancelled == False,
        )
    )
    total_classes = classes_res.scalar_one()

    bookings_res = await db.execute(
        select(func.count(ClassBooking.id))
        .join(ClassBooking.schedule)
        .join(GymClassSchedule.template)
        .where(
            GymClassTemplate.gym_id == gym.id,
            GymClassSchedule.starts_at >= month_start,
            ClassBooking.status.in_([BookingStatus.CONFIRMED, BookingStatus.ATTENDED]),
        )
    )
    total_bookings = bookings_res.scalar_one()

    avg_attendance = 0.0
    if total_classes > 0:
        avg_attendance = round(total_bookings / total_classes, 2)

    xp_res = await db.execute(
        select(func.coalesce(func.sum(XPTransaction.amount), 0))
        .where(
            XPTransaction.reason == XPReason.SUBSCRIPTION_PAYMENT,
            XPTransaction.created_at >= month_start,
        )
    )
    raw_xp = xp_res.scalar_one()
    revenue_xp = abs(int(raw_xp)) if raw_xp else 0

    return GymAnalytics(
        total_members=total_members,
        active_members=active_members,
        total_classes_this_month=total_classes,
        avg_attendance_rate=avg_attendance,
        revenue_xp_this_month=revenue_xp,
    )


# ─── Gym owner: weekly schedule ───────────────────────────────────────────────

@router.get("/mine/weekly-slots", response_model=list[WeeklySlotPublic])
async def list_weekly_slots(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        return []
    res = await db.execute(
        select(GymWeeklySlot)
        .where(GymWeeklySlot.gym_id == gym.id)
        .order_by(GymWeeklySlot.day_of_week, GymWeeklySlot.start_time)
    )
    return res.scalars().all()


@router.post("/mine/weekly-slots", response_model=WeeklySlotPublic, status_code=201)
async def create_weekly_slot(
    body: WeeklySlotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Crea tu gimnasio primero")
    slot = GymWeeklySlot(gym_id=gym.id, **body.model_dump())
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot


@router.delete("/mine/weekly-slots/{slot_id}", status_code=204)
async def delete_weekly_slot(
    slot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    result = await db.execute(select(Gym).where(Gym.owner_id == current_user.id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")
    res = await db.execute(
        select(GymWeeklySlot).where(GymWeeklySlot.id == slot_id, GymWeeklySlot.gym_id == gym.id)
    )
    slot = res.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot no encontrado")
    await db.delete(slot)
    await db.commit()


# ─── Public: gym detail (must be after /mine routes to avoid path conflicts) ──

@router.get("/{gym_id}", response_model=GymPublic)
async def get_gym(
    gym_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_gym_or_404(db, gym_id)


@router.get("/{gym_id}/locations", response_model=list[LocationPublic])
async def get_gym_locations(
    gym_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_gym_or_404(db, gym_id)
    result = await db.execute(
        select(GymLocation).where(GymLocation.gym_id == gym_id, GymLocation.is_active == True)
    )
    return result.scalars().all()


@router.get("/{gym_id}/plans", response_model=list[PlanPublic])
async def get_gym_plans(
    gym_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_gym_or_404(db, gym_id)
    result = await db.execute(
        select(GymSubscriptionPlan).where(
            GymSubscriptionPlan.gym_id == gym_id,
            GymSubscriptionPlan.is_active == True,
        )
    )
    return result.scalars().all()


@router.get("/{gym_id}/weekly-slots", response_model=list[WeeklySlotPublic])
async def get_gym_weekly_slots(
    gym_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Weekly recurring timetable for a gym (athlete-facing)."""
    await _get_gym_or_404(db, gym_id)
    result = await db.execute(
        select(GymWeeklySlot)
        .where(GymWeeklySlot.gym_id == gym_id)
        .order_by(GymWeeklySlot.day_of_week, GymWeeklySlot.start_time)
    )
    return result.scalars().all()


async def _ensure_schedules_from_slots(db: AsyncSession, gym_id: int, now: datetime) -> None:
    """Auto-generate GymClassSchedule entries from weekly slots for the next 4 weeks.

    For each weekly slot, find or create a matching GymClassTemplate (by name),
    then create schedule instances for upcoming occurrences that don't exist yet.
    Requires at least one active location in the gym.
    """
    slots_res = await db.execute(
        select(GymWeeklySlot).where(GymWeeklySlot.gym_id == gym_id)
    )
    slots = slots_res.scalars().all()
    if not slots:
        return

    loc_res = await db.execute(
        select(GymLocation)
        .where(GymLocation.gym_id == gym_id, GymLocation.is_active == True)
        .limit(1)
    )
    location = loc_res.scalar_one_or_none()
    if not location:
        return

    tmpl_res = await db.execute(
        select(GymClassTemplate).where(GymClassTemplate.gym_id == gym_id)
    )
    templates: dict[str, GymClassTemplate] = {t.name: t for t in tmpl_res.scalars().all()}

    # Start from Monday of the current week so past classes this week are generated too
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = now + timedelta(days=28)
    created_any = False

    for slot in slots:
        template = templates.get(slot.name)
        if not template:
            h1, m1 = map(int, slot.start_time.split(":"))
            h2, m2 = map(int, slot.end_time.split(":"))
            duration = max(1, (h2 * 60 + m2) - (h1 * 60 + m1))
            template = GymClassTemplate(
                gym_id=gym_id,
                name=slot.name,
                duration_minutes=duration,
                max_capacity=slot.capacity,
                tickets_cost=slot.cost,
            )
            db.add(template)
            await db.flush()
            templates[slot.name] = template
            created_any = True

        current = week_start
        while current <= end_dt:
            if current.weekday() == slot.day_of_week:
                h, m = map(int, slot.start_time.split(":"))
                eh, em = map(int, slot.end_time.split(":"))
                starts = current.replace(hour=h, minute=m)
                ends = current.replace(hour=eh, minute=em)
                existing = await db.execute(
                    select(GymClassSchedule).where(
                        GymClassSchedule.template_id == template.id,
                        GymClassSchedule.location_id == location.id,
                        GymClassSchedule.starts_at == starts,
                    )
                )
                if not existing.scalar_one_or_none():
                    db.add(GymClassSchedule(
                        template_id=template.id,
                        location_id=location.id,
                        starts_at=starts,
                        ends_at=ends,
                        override_capacity=slot.capacity,
                    ))
                    created_any = True
            current += timedelta(days=1)

    if created_any:
        await db.commit()


@router.get("/{gym_id}/schedule", response_model=list[SchedulePublic])
async def get_gym_schedule(
    gym_id: int,
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    location_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upcoming classes at a gym (athlete-facing)."""
    await _get_gym_or_404(db, gym_id)
    now = datetime.now(timezone.utc)
    await _ensure_schedules_from_slots(db, gym_id, now)

    q = (
        select(GymClassSchedule)
        .join(GymClassSchedule.template)
        .join(GymClassSchedule.location)
        .where(
            GymClassTemplate.gym_id == gym_id,
            GymClassSchedule.is_cancelled == False,
            GymClassSchedule.starts_at >= (from_dt or now),
        )
        .options(
            selectinload(GymClassSchedule.template),
            selectinload(GymClassSchedule.location).selectinload(GymLocation.gym),
        )
        .order_by(GymClassSchedule.starts_at)
    )
    if to_dt:
        q = q.where(GymClassSchedule.starts_at <= to_dt)
    if location_id:
        q = q.where(GymClassSchedule.location_id == location_id)

    result = await db.execute(q)
    schedules = result.scalars().all()
    return [await _enrich_schedule(db, s, current_user.id) for s in schedules]


# ─── Athlete: subscribe to a gym ─────────────────────────────────────────────

@router.post("/{gym_id}/subscribe/{plan_id}", response_model=MembershipPublic)
async def subscribe(
    gym_id: int,
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    gym = await _get_gym_or_404(db, gym_id)

    plan_res = await db.execute(
        select(GymSubscriptionPlan).where(
            GymSubscriptionPlan.id == plan_id,
            GymSubscriptionPlan.gym_id == gym_id,
            GymSubscriptionPlan.is_active == True,
        )
    )
    plan = plan_res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    # Check existing active membership
    existing_res = await db.execute(
        select(GymMembership)
        .where(
            GymMembership.gym_id == gym_id,
            GymMembership.user_id == current_user.id,
            GymMembership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.TRIAL, MembershipStatus.FROZEN]),
        )
        .options(selectinload(GymMembership.plan))
    )
    existing = existing_res.scalar_one_or_none()

    if current_user.total_xp < plan.xp_price:
        raise HTTPException(status_code=400, detail="XP insuficiente para este plan")

    # Deduct XP
    current_user.total_xp -= plan.xp_price
    xp_tx = XPTransaction(
        user_id=current_user.id,
        amount=-plan.xp_price,
        reason=XPReason.SUBSCRIPTION_PAYMENT,
        description=f"Suscripción: {gym.name} – {plan.name}",
    )
    db.add(xp_tx)

    now = datetime.now(timezone.utc)

    if plan.plan_type == PlanType.TICKETS:
        # Tickets are independent of the membership: add to the wallet
        wallet = await _get_or_create_wallet(db, current_user.id, gym_id)
        wallet.tickets_remaining += plan.ticket_count or 0

        # If no active (non-trial) membership exists, create one so the user can book
        needs_membership = not existing or existing.is_trial
        if needs_membership:
            if existing:
                existing.status = MembershipStatus.CANCELLED
            membership = GymMembership(
                gym_id=gym_id,
                user_id=current_user.id,
                plan_id=plan_id,
                status=MembershipStatus.ACTIVE,
                tickets_remaining=None,
                started_at=now,
                expires_at=None,
                auto_renew=False,
                is_trial=False,
            )
            db.add(membership)
            await db.commit()
            await db.refresh(membership)
        else:
            await db.commit()
            await db.refresh(existing)
            membership = existing

        await db.refresh(wallet)
        data = {c.name: getattr(membership, c.name) for c in membership.__table__.columns}
        data["tickets_remaining"] = wallet.tickets_remaining
        mem_plan = membership.plan if hasattr(membership, "plan") and membership.plan else None
        return MembershipPublic(
            **data,
            gym_name=gym.name,
            plan_name=mem_plan.name if mem_plan else plan.name,
            plan_type=mem_plan.plan_type if mem_plan else plan.plan_type,
            sessions_included=mem_plan.sessions_included if mem_plan else plan.sessions_included,
        )

    # MONTHLY / ANNUAL: cancel existing and create new membership
    if existing:
        existing.status = MembershipStatus.CANCELLED

    expires = now + timedelta(days=30 if plan.plan_type == PlanType.MONTHLY else 365)
    membership = GymMembership(
        gym_id=gym_id,
        user_id=current_user.id,
        plan_id=plan_id,
        status=MembershipStatus.ACTIVE,
        tickets_remaining=None,
        started_at=now,
        expires_at=expires,
        auto_renew=True,
        is_trial=False,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    wallet = await _get_or_create_wallet(db, current_user.id, gym_id)
    data = {c.name: getattr(membership, c.name) for c in membership.__table__.columns}
    data["tickets_remaining"] = wallet.tickets_remaining
    return MembershipPublic(
        **data,
        gym_name=gym.name,
        plan_name=plan.name,
        plan_type=plan.plan_type,
        sessions_included=plan.sessions_included,
    )


@router.post("/{gym_id}/trial", response_model=MembershipPublic)
async def subscribe_trial(
    gym_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    gym = await _get_gym_or_404(db, gym_id)
    if not gym.free_trial_enabled:
        raise HTTPException(status_code=400, detail="Este gimnasio no ofrece clase de prueba")

    # Check no previous membership (including trial)
    prev_res = await db.execute(
        select(GymMembership).where(
            GymMembership.gym_id == gym_id,
            GymMembership.user_id == current_user.id,
        )
    )
    if prev_res.scalars().first():
        raise HTTPException(status_code=409, detail="Ya tienes o tuviste una membresía en este gimnasio")

    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=7)

    membership = GymMembership(
        gym_id=gym_id,
        user_id=current_user.id,
        plan_id=None,
        status=MembershipStatus.TRIAL,
        tickets_remaining=1,
        started_at=now,
        expires_at=expires,
        auto_renew=False,
        is_trial=True,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return MembershipPublic(
        **{c.name: getattr(membership, c.name) for c in membership.__table__.columns},
        gym_name=gym.name,
        plan_name=None,
    )


# ─── Athlete: manage my memberships ──────────────────────────────────────────

@router.get("/memberships/mine", response_model=list[MembershipPublic])
async def my_memberships(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(GymMembership)
        .where(GymMembership.user_id == current_user.id)
        .options(
            selectinload(GymMembership.gym),
            selectinload(GymMembership.plan),
        )
    )
    memberships = res.scalars().all()

    # Fetch all wallets for this user in one query
    wallet_res = await db.execute(
        select(GymTicketWallet).where(GymTicketWallet.user_id == current_user.id)
    )
    wallets = {w.gym_id: w for w in wallet_res.scalars().all()}

    out = []
    for m in memberships:
        await _auto_renew_if_needed(db, m)
        wallet = wallets.get(m.gym_id)
        # Trials keep their own tickets_remaining; paid memberships read from the wallet
        if m.is_trial:
            tickets = m.tickets_remaining
        else:
            tickets = wallet.tickets_remaining if wallet else 0
        data = {c.name: getattr(m, c.name) for c in m.__table__.columns}
        data["tickets_remaining"] = tickets
        out.append(
            MembershipPublic(
                **data,
                gym_name=m.gym.name if m.gym else None,
                plan_name=m.plan.name if m.plan else None,
                plan_type=m.plan.plan_type if m.plan else None,
                sessions_included=m.plan.sessions_included if m.plan else None,
            )
        )
    await db.commit()
    return out


@router.post("/memberships/{membership_id}/freeze", response_model=MembershipPublic)
async def freeze_membership(
    membership_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(GymMembership).where(
            GymMembership.id == membership_id,
            GymMembership.user_id == current_user.id,
        )
    )
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Membresía no encontrada")
    if m.status != MembershipStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Solo puedes congelar membresías activas")
    m.status = MembershipStatus.FROZEN
    m.frozen_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(m)
    return MembershipPublic(
        **{c.name: getattr(m, c.name) for c in m.__table__.columns},
    )


@router.post("/memberships/{membership_id}/unfreeze", response_model=MembershipPublic)
async def unfreeze_membership(
    membership_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(GymMembership).where(
            GymMembership.id == membership_id,
            GymMembership.user_id == current_user.id,
        )
    )
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Membresía no encontrada")
    if m.status != MembershipStatus.FROZEN:
        raise HTTPException(status_code=400, detail="La membresía no está congelada")

    now = datetime.now(timezone.utc)
    if m.frozen_at and m.expires_at:
        frozen_duration = now - m.frozen_at
        m.expires_at = m.expires_at + frozen_duration
        m.frozen_days_used += frozen_duration.days
    m.status = MembershipStatus.ACTIVE
    m.frozen_at = None
    await db.commit()
    await db.refresh(m)
    return MembershipPublic(
        **{c.name: getattr(m, c.name) for c in m.__table__.columns},
    )


@router.post("/memberships/{membership_id}/cancel", response_model=MembershipPublic)
async def cancel_membership(
    membership_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(GymMembership).where(
            GymMembership.id == membership_id,
            GymMembership.user_id == current_user.id,
        )
    )
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Membresía no encontrada")
    if m.status == MembershipStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Ya está cancelada")
    m.status = MembershipStatus.CANCELLED
    m.auto_renew = False
    await db.commit()
    await db.refresh(m)
    return MembershipPublic(
        **{c.name: getattr(m, c.name) for c in m.__table__.columns},
    )


# ─── Athlete: booking ────────────────────────────────────────────────────────

@router.get("/schedules/mine", response_model=list[SchedulePublic])
async def get_my_upcoming_bookings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete's upcoming confirmed class bookings."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(GymClassSchedule)
        .join(ClassBooking, ClassBooking.schedule_id == GymClassSchedule.id)
        .where(
            ClassBooking.user_id == current_user.id,
            ClassBooking.status == BookingStatus.CONFIRMED,
            GymClassSchedule.starts_at >= now,
            GymClassSchedule.is_cancelled == False,
        )
        .options(
            selectinload(GymClassSchedule.template),
            selectinload(GymClassSchedule.location).selectinload(GymLocation.gym),
        )
        .order_by(GymClassSchedule.starts_at)
    )
    schedules = result.scalars().all()
    return [await _enrich_schedule(db, s, current_user.id) for s in schedules]


@router.post("/schedules/{sched_id}/book", response_model=BookingPublic)
async def book_class(
    sched_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sched_res = await db.execute(
        select(GymClassSchedule)
        .where(GymClassSchedule.id == sched_id, GymClassSchedule.is_cancelled == False)
        .options(
            selectinload(GymClassSchedule.template),
            selectinload(GymClassSchedule.location).selectinload(GymLocation.gym),
        )
    )
    sched = sched_res.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Clase no encontrada")

    now = datetime.now(timezone.utc)
    if sched.starts_at <= now:
        raise HTTPException(status_code=400, detail="La clase ya ha comenzado")

    # Check existing booking
    existing_res = await db.execute(
        select(ClassBooking).where(
            ClassBooking.schedule_id == sched_id,
            ClassBooking.user_id == current_user.id,
            ClassBooking.status != BookingStatus.CANCELLED,
        )
    )
    if existing_res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya tienes reserva en esta clase")

    gym_id = sched.location.gym_id

    # Get active membership
    mem_res = await db.execute(
        select(GymMembership).where(
            GymMembership.gym_id == gym_id,
            GymMembership.user_id == current_user.id,
            GymMembership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.TRIAL]),
        )
    )
    membership = mem_res.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Necesitas una membresía activa en este gimnasio")

    await _auto_renew_if_needed(db, membership)
    if membership.status not in (MembershipStatus.ACTIVE, MembershipStatus.TRIAL):
        raise HTTPException(status_code=403, detail="Tu membresía ha expirado")

    # Check capacity
    booked_count = await _count_confirmed_bookings(db, sched_id)
    capacity = sched.effective_capacity

    if booked_count >= capacity:
        # Add to waitlist
        wl_res = await db.execute(
            select(func.count(ClassWaitlist.id)).where(ClassWaitlist.schedule_id == sched_id)
        )
        position = wl_res.scalar_one() + 1
        wl = ClassWaitlist(
            schedule_id=sched_id,
            user_id=current_user.id,
            position=position,
        )
        db.add(wl)
        await db.commit()
        raise HTTPException(
            status_code=202,
            detail=f"Clase llena. Añadido a lista de espera (posición {position})",
        )

    # Determine tickets to use
    tickets_used = 0
    plan = None
    if membership.plan_id:
        plan = await db.get(GymSubscriptionPlan, membership.plan_id)

    if plan and plan.plan_type == PlanType.TICKETS:
        # Pure tickets plan: deduct from wallet
        wallet = await _get_or_create_wallet(db, current_user.id, gym_id)
        cost = sched.template.tickets_cost
        if wallet.tickets_remaining < cost:
            raise HTTPException(status_code=400, detail="Tickets insuficientes")
        wallet.tickets_remaining -= cost
        tickets_used = cost
    elif plan and plan.plan_type in (PlanType.MONTHLY, PlanType.ANNUAL):
        if plan.sessions_included is not None:
            if membership.sessions_used_this_period >= plan.sessions_included:
                # Session limit reached — fall back to ticket wallet
                wallet = await _get_or_create_wallet(db, current_user.id, gym_id)
                cost = sched.template.tickets_cost
                if wallet.tickets_remaining < cost:
                    raise HTTPException(status_code=400, detail="Has alcanzado el límite de sesiones de este período")
                wallet.tickets_remaining -= cost
                tickets_used = cost
            else:
                membership.sessions_used_this_period += 1
        else:
            membership.sessions_used_this_period += 1
    elif membership.is_trial:
        if (membership.tickets_remaining or 0) < 1:
            raise HTTPException(status_code=400, detail="Ya usaste tu clase de prueba")
        membership.tickets_remaining -= 1
        tickets_used = 1

    booking = ClassBooking(
        schedule_id=sched_id,
        user_id=current_user.id,
        membership_id=membership.id,
        status=BookingStatus.CONFIRMED,
        tickets_used=tickets_used,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


@router.delete("/schedules/{sched_id}/book", status_code=204)
async def cancel_booking(
    sched_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sched_res = await db.execute(
        select(GymClassSchedule)
        .where(GymClassSchedule.id == sched_id)
        .options(selectinload(GymClassSchedule.template))
    )
    sched = sched_res.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Clase no encontrada")

    # Check cancellation window
    gym_res = await db.execute(
        select(Gym).where(Gym.id == sched.template.gym_id)
    )
    gym = gym_res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    cancel_deadline = sched.starts_at - timedelta(hours=gym.cancellation_hours if gym else 2)
    if now > cancel_deadline:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cancelar con menos de {gym.cancellation_hours if gym else 2}h de antelación",
        )

    res = await db.execute(
        select(ClassBooking).where(
            ClassBooking.schedule_id == sched_id,
            ClassBooking.user_id == current_user.id,
            ClassBooking.status == BookingStatus.CONFIRMED,
        )
    )
    booking = res.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = now

    # Refund tickets / sessions if applicable
    if booking.membership_id:
        mem = await db.get(GymMembership, booking.membership_id)
        if mem:
            if booking.tickets_used > 0:
                if mem.is_trial:
                    # Trial tickets are stored on the membership itself
                    mem.tickets_remaining = (mem.tickets_remaining or 0) + booking.tickets_used
                else:
                    # Paid tickets live in the wallet
                    wallet = await _get_or_create_wallet(db, booking.user_id, mem.gym_id)
                    wallet.tickets_remaining += booking.tickets_used
            elif mem.sessions_used_this_period > 0:
                mem.sessions_used_this_period -= 1

    # Promote first on waitlist
    wl_res = await db.execute(
        select(ClassWaitlist)
        .where(ClassWaitlist.schedule_id == sched_id)
        .order_by(ClassWaitlist.position)
        .limit(1)
    )
    next_wl = wl_res.scalar_one_or_none()
    if next_wl:
        # Auto-book for them (simplified: create booking, remove from waitlist)
        auto_booking = ClassBooking(
            schedule_id=sched_id,
            user_id=next_wl.user_id,
            membership_id=None,
            status=BookingStatus.CONFIRMED,
            tickets_used=0,
        )
        db.add(auto_booking)
        await db.delete(next_wl)

    await db.commit()


# ─── Gym owner: class workouts ────────────────────────────────────────────────

async def _get_my_gym(db: AsyncSession, owner_id: int) -> Gym:
    result = await db.execute(select(Gym).where(Gym.owner_id == owner_id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")
    return gym


async def _build_workout_public(db: AsyncSession, workout: GymClassWorkout) -> GymClassWorkoutPublic:
    """Enrich workout with exercise names."""
    blocks_out = []
    for block in workout.blocks:
        exercises_out = []
        for ex in block.exercises:
            ex_name = ex.exercise.name if ex.exercise else None
            exercises_out.append(
                GymClassWorkoutExercisePublic(
                    id=ex.id,
                    block_id=ex.block_id,
                    exercise_id=ex.exercise_id,
                    exercise_name=ex_name,
                    order=ex.order,
                    target_sets=ex.target_sets,
                    target_reps=ex.target_reps,
                    target_weight_kg=ex.target_weight_kg,
                    target_distance_m=ex.target_distance_m,
                    target_duration_sec=ex.target_duration_sec,
                    notes=ex.notes,
                )
            )
        blocks_out.append(
            GymClassWorkoutBlockPublic(
                id=block.id,
                workout_id=block.workout_id,
                order=block.order,
                name=block.name,
                block_type=block.block_type,
                duration_sec=block.duration_sec,
                rounds=block.rounds,
                work_sec=block.work_sec,
                rest_sec=block.rest_sec,
                exercises=exercises_out,
            )
        )
    return GymClassWorkoutPublic(
        id=workout.id,
        gym_id=workout.gym_id,
        name=workout.name,
        description=workout.description,
        created_at=workout.created_at,
        blocks=blocks_out,
    )


async def _load_workout_full(db: AsyncSession, workout_id: int) -> GymClassWorkout | None:
    res = await db.execute(
        select(GymClassWorkout)
        .where(GymClassWorkout.id == workout_id)
        .options(
            selectinload(GymClassWorkout.blocks).selectinload(GymClassWorkoutBlock.exercises).selectinload(GymClassWorkoutExercise.exercise)
        )
    )
    return res.scalar_one_or_none()


@router.post("/mine/workouts", response_model=GymClassWorkoutPublic, status_code=201)
async def create_class_workout(
    body: GymClassWorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    gym = await _get_my_gym(db, current_user.id)

    workout = GymClassWorkout(
        gym_id=gym.id,
        name=body.name,
        description=body.description,
        created_by=current_user.id,
    )
    db.add(workout)
    await db.flush()

    for b_data in body.blocks:
        block = GymClassWorkoutBlock(
            workout_id=workout.id,
            order=b_data.order,
            name=b_data.name,
            block_type=b_data.block_type,
            duration_sec=b_data.duration_sec,
            rounds=b_data.rounds,
            work_sec=b_data.work_sec,
            rest_sec=b_data.rest_sec,
        )
        db.add(block)
        await db.flush()
        for e_data in b_data.exercises:
            db.add(GymClassWorkoutExercise(
                block_id=block.id,
                exercise_id=e_data.exercise_id,
                order=e_data.order,
                target_sets=e_data.target_sets,
                target_reps=e_data.target_reps,
                target_weight_kg=e_data.target_weight_kg,
                target_distance_m=e_data.target_distance_m,
                target_duration_sec=e_data.target_duration_sec,
                notes=e_data.notes,
            ))

    await db.commit()
    workout = await _load_workout_full(db, workout.id)
    return await _build_workout_public(db, workout)


@router.get("/mine/workouts", response_model=list[GymClassWorkoutPublic])
async def list_class_workouts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    gym = await _get_my_gym(db, current_user.id)

    res = await db.execute(
        select(GymClassWorkout)
        .where(GymClassWorkout.gym_id == gym.id)
        .options(
            selectinload(GymClassWorkout.blocks).selectinload(GymClassWorkoutBlock.exercises).selectinload(GymClassWorkoutExercise.exercise)
        )
        .order_by(GymClassWorkout.created_at.desc())
    )
    workouts = res.scalars().all()
    return [await _build_workout_public(db, w) for w in workouts]


@router.get("/mine/workouts/{workout_id}", response_model=GymClassWorkoutPublic)
async def get_class_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    gym = await _get_my_gym(db, current_user.id)

    workout = await _load_workout_full(db, workout_id)
    if not workout or workout.gym_id != gym.id:
        raise HTTPException(status_code=404, detail="Entrenamiento no encontrado")
    return await _build_workout_public(db, workout)


@router.put("/mine/workouts/{workout_id}", response_model=GymClassWorkoutPublic)
async def update_class_workout(
    workout_id: int,
    body: GymClassWorkoutUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    gym = await _get_my_gym(db, current_user.id)

    workout = await _load_workout_full(db, workout_id)
    if not workout or workout.gym_id != gym.id:
        raise HTTPException(status_code=404, detail="Entrenamiento no encontrado")

    if body.name is not None:
        workout.name = body.name
    if body.description is not None:
        workout.description = body.description

    if body.blocks is not None:
        # Replace all blocks
        for block in list(workout.blocks):
            await db.delete(block)
        await db.flush()

        for b_data in body.blocks:
            block = GymClassWorkoutBlock(
                workout_id=workout.id,
                order=b_data.order,
                name=b_data.name,
                block_type=b_data.block_type,
                duration_sec=b_data.duration_sec,
                rounds=b_data.rounds,
                work_sec=b_data.work_sec,
                rest_sec=b_data.rest_sec,
            )
            db.add(block)
            await db.flush()
            for e_data in b_data.exercises:
                db.add(GymClassWorkoutExercise(
                    block_id=block.id,
                    exercise_id=e_data.exercise_id,
                    order=e_data.order,
                    target_sets=e_data.target_sets,
                    target_reps=e_data.target_reps,
                    target_weight_kg=e_data.target_weight_kg,
                    target_distance_m=e_data.target_distance_m,
                    target_duration_sec=e_data.target_duration_sec,
                    notes=e_data.notes,
                ))

    await db.commit()
    workout = await _load_workout_full(db, workout.id)
    return await _build_workout_public(db, workout)


@router.delete("/mine/workouts/{workout_id}", status_code=204)
async def delete_class_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    gym = await _get_my_gym(db, current_user.id)

    res = await db.execute(
        select(GymClassWorkout).where(
            GymClassWorkout.id == workout_id,
            GymClassWorkout.gym_id == gym.id,
        )
    )
    workout = res.scalar_one_or_none()
    if not workout:
        raise HTTPException(status_code=404, detail="Entrenamiento no encontrado")
    await db.delete(workout)
    await db.commit()


# ─── Gym owner: live class control ───────────────────────────────────────────

async def _get_owner_schedule(db: AsyncSession, sched_id: int, gym_id: int) -> GymClassSchedule:
    res = await db.execute(
        select(GymClassSchedule)
        .join(GymClassSchedule.template)
        .where(GymClassSchedule.id == sched_id, GymClassTemplate.gym_id == gym_id)
        .options(
            selectinload(GymClassSchedule.workout).selectinload(GymClassWorkout.blocks).selectinload(GymClassWorkoutBlock.exercises).selectinload(GymClassWorkoutExercise.exercise),
        )
    )
    sched = res.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    return sched


@router.websocket("/schedules/{sched_id}/live/ws")
async def ws_live_class(
    sched_id: int,
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """WebSocket para estado en vivo de la clase. Auth via ?token=JWT."""
    # Authenticate
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001)
        return

    user_id_str = payload.get("sub")
    if not user_id_str:
        await websocket.close(code=4001)
        return

    user_res = await db.execute(select(User).where(User.id == int(user_id_str)))
    user = user_res.scalar_one_or_none()
    if not user:
        await websocket.close(code=4001)
        return

    # Authorize: gym owner or athlete with a confirmed booking
    if user.role == "gym":
        try:
            gym = await _get_my_gym(db, user.id)
            sched_check = await db.execute(
                select(GymClassSchedule)
                .join(GymClassSchedule.template)
                .where(GymClassSchedule.id == sched_id, GymClassTemplate.gym_id == gym.id)
            )
            if not sched_check.scalar_one_or_none():
                await websocket.close(code=4003)
                return
        except HTTPException:
            await websocket.close(code=4003)
            return
    else:
        booking_res = await db.execute(
            select(ClassBooking).where(
                ClassBooking.schedule_id == sched_id,
                ClassBooking.user_id == user.id,
                ClassBooking.status.in_([BookingStatus.CONFIRMED, BookingStatus.ATTENDED]),
            )
        )
        if not booking_res.scalar_one_or_none():
            await websocket.close(code=4003)
            return

    await live_manager.connect(sched_id, websocket)
    try:
        # Send initial state immediately on connect
        init_res = await db.execute(
            select(GymClassSchedule)
            .where(GymClassSchedule.id == sched_id)
            .options(
                selectinload(GymClassSchedule.workout)
                .selectinload(GymClassWorkout.blocks)
                .selectinload(GymClassWorkoutBlock.exercises)
                .selectinload(GymClassWorkoutExercise.exercise),
            )
        )
        sched = init_res.scalar_one_or_none()
        if sched:
            now = datetime.now(timezone.utc)
            state = _build_live_state(sched, now)
            await websocket.send_json(state.model_dump(mode="json"))

        # Keep alive — client sends periodic pings or we just wait for disconnect
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        live_manager.disconnect(sched_id, websocket)


@router.get("/mine/schedules/{sched_id}/live", response_model=ClassLiveStatePublic)
async def get_live_state_owner(
    sched_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Estado en vivo de la clase para el dueño del gym."""
    _require_gym_owner(current_user)
    gym = await _get_my_gym(db, current_user.id)
    sched = await _get_owner_schedule(db, sched_id, gym.id)
    now = datetime.now(timezone.utc)
    return _build_live_state(sched, now)


@router.post("/mine/schedules/{sched_id}/live/start", response_model=ClassLiveStatePublic)
async def live_start(
    sched_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    gym = await _get_my_gym(db, current_user.id)
    sched = await _get_owner_schedule(db, sched_id, gym.id)

    if sched.live_status != GymClassLiveStatus.PENDING:
        raise HTTPException(status_code=400, detail="La clase ya fue iniciada")

    now = datetime.now(timezone.utc)
    sched.live_status = GymClassLiveStatus.ACTIVE
    sched.live_block_index = 0
    sched.live_timer_started_at = now
    sched.live_timer_paused_at = None
    state = _build_live_state(sched, now)
    await db.commit()
    await live_manager.broadcast(sched_id, state.model_dump(mode="json"))
    return state


@router.post("/mine/schedules/{sched_id}/live/next", response_model=ClassLiveStatePublic)
async def live_next_block(
    sched_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    gym = await _get_my_gym(db, current_user.id)
    sched = await _get_owner_schedule(db, sched_id, gym.id)

    if sched.live_status not in (GymClassLiveStatus.ACTIVE, GymClassLiveStatus.PAUSED):
        raise HTTPException(status_code=400, detail="La clase no está en curso")

    total = len(sched.workout.blocks) if sched.workout else 0
    next_index = sched.live_block_index + 1

    now = datetime.now(timezone.utc)
    if next_index >= total:
        sched.live_status = GymClassLiveStatus.FINISHED
        sched.live_timer_started_at = None
        sched.live_timer_paused_at = None
    else:
        sched.live_block_index = next_index
        sched.live_status = GymClassLiveStatus.ACTIVE
        sched.live_timer_started_at = now
        sched.live_timer_paused_at = None

    state = _build_live_state(sched, now)
    await db.commit()
    await live_manager.broadcast(sched_id, state.model_dump(mode="json"))
    return state


@router.post("/mine/schedules/{sched_id}/live/pause", response_model=ClassLiveStatePublic)
async def live_pause(
    sched_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    gym = await _get_my_gym(db, current_user.id)
    sched = await _get_owner_schedule(db, sched_id, gym.id)

    if sched.live_status != GymClassLiveStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="La clase no está activa")

    now = datetime.now(timezone.utc)
    sched.live_status = GymClassLiveStatus.PAUSED
    sched.live_timer_paused_at = now
    state = _build_live_state(sched, now)
    await db.commit()
    await live_manager.broadcast(sched_id, state.model_dump(mode="json"))
    return state


@router.post("/mine/schedules/{sched_id}/live/resume", response_model=ClassLiveStatePublic)
async def live_resume(
    sched_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    gym = await _get_my_gym(db, current_user.id)
    sched = await _get_owner_schedule(db, sched_id, gym.id)

    if sched.live_status != GymClassLiveStatus.PAUSED:
        raise HTTPException(status_code=400, detail="La clase no está pausada")

    now = datetime.now(timezone.utc)
    # Adjust start time so elapsed is preserved: new_start = now - already_elapsed
    if sched.live_timer_started_at and sched.live_timer_paused_at:
        already_elapsed = sched.live_timer_paused_at - sched.live_timer_started_at
        sched.live_timer_started_at = now - already_elapsed
    else:
        sched.live_timer_started_at = now

    sched.live_status = GymClassLiveStatus.ACTIVE
    sched.live_timer_paused_at = None
    state = _build_live_state(sched, now)
    await db.commit()
    await live_manager.broadcast(sched_id, state.model_dump(mode="json"))
    return state


@router.post("/mine/schedules/{sched_id}/live/finish", response_model=ClassLiveStatePublic)
async def live_finish(
    sched_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_gym_owner(current_user)
    gym = await _get_my_gym(db, current_user.id)
    sched = await _get_owner_schedule(db, sched_id, gym.id)

    if sched.live_status == GymClassLiveStatus.PENDING:
        raise HTTPException(status_code=400, detail="La clase no ha sido iniciada")
    if sched.live_status == GymClassLiveStatus.FINISHED:
        raise HTTPException(status_code=400, detail="La clase ya está finalizada")

    now = datetime.now(timezone.utc)
    sched.live_status = GymClassLiveStatus.FINISHED
    sched.live_timer_started_at = None
    sched.live_timer_paused_at = None
    state = _build_live_state(sched, now)
    await db.commit()
    await live_manager.broadcast(sched_id, state.model_dump(mode="json"))
    return state


def _build_live_state(sched: GymClassSchedule, now: datetime) -> ClassLiveStatePublic:
    """Compute ClassLiveStatePublic from a schedule with loaded workout."""
    workout = sched.workout
    blocks = workout.blocks if workout else []
    total_blocks = len(blocks)
    current_block_data = None

    if blocks and sched.live_block_index < total_blocks:
        b = blocks[sched.live_block_index]
        exercises_out = [
            GymClassWorkoutExercisePublic(
                id=ex.id,
                block_id=ex.block_id,
                exercise_id=ex.exercise_id,
                exercise_name=ex.exercise.name if ex.exercise else None,
                order=ex.order,
                target_sets=ex.target_sets,
                target_reps=ex.target_reps,
                target_weight_kg=ex.target_weight_kg,
                target_distance_m=ex.target_distance_m,
                target_duration_sec=ex.target_duration_sec,
                notes=ex.notes,
            )
            for ex in b.exercises
        ]
        current_block_data = GymClassWorkoutBlockPublic(
            id=b.id,
            workout_id=b.workout_id,
            order=b.order,
            name=b.name,
            block_type=b.block_type,
            duration_sec=b.duration_sec,
            rounds=b.rounds,
            work_sec=b.work_sec,
            rest_sec=b.rest_sec,
            exercises=exercises_out,
        )

    # Compute elapsed and remaining seconds
    elapsed_sec = None
    remaining_sec = None

    if sched.live_status == GymClassLiveStatus.ACTIVE and sched.live_timer_started_at:
        elapsed_sec = int((now - sched.live_timer_started_at).total_seconds())
    elif sched.live_status == GymClassLiveStatus.PAUSED and sched.live_timer_started_at and sched.live_timer_paused_at:
        elapsed_sec = int((sched.live_timer_paused_at - sched.live_timer_started_at).total_seconds())

    if elapsed_sec is not None and current_block_data and current_block_data.duration_sec:
        remaining_sec = max(0, current_block_data.duration_sec - elapsed_sec)

    return ClassLiveStatePublic(
        schedule_id=sched.id,
        live_status=sched.live_status,
        live_block_index=sched.live_block_index,
        total_blocks=total_blocks,
        elapsed_sec=elapsed_sec,
        remaining_sec=remaining_sec,
        current_block=current_block_data,
        workout_id=workout.id if workout else None,
        workout_name=workout.name if workout else None,
    )


# ─── Athlete: live state + save session ───────────────────────────────────────

@router.get("/schedules/{sched_id}/live", response_model=ClassLiveStatePublic)
async def get_live_state(
    sched_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Estado en vivo de la clase para polling del atleta (cada 2-3 s)."""
    res = await db.execute(
        select(GymClassSchedule)
        .where(GymClassSchedule.id == sched_id)
        .options(
            selectinload(GymClassSchedule.workout).selectinload(GymClassWorkout.blocks).selectinload(GymClassWorkoutBlock.exercises).selectinload(GymClassWorkoutExercise.exercise),
        )
    )
    sched = res.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Clase no encontrada")

    # Check user has a booking
    booking_res = await db.execute(
        select(ClassBooking).where(
            ClassBooking.schedule_id == sched_id,
            ClassBooking.user_id == current_user.id,
            ClassBooking.status.in_([BookingStatus.CONFIRMED, BookingStatus.ATTENDED]),
        )
    )
    if not booking_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="No tienes reserva en esta clase")

    now = datetime.now(timezone.utc)
    return _build_live_state(sched, now)


@router.post("/schedules/{sched_id}/save-session", response_model=SessionResponse, status_code=201)
async def save_class_session(
    sched_id: int,
    body: ClassSessionSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """El atleta confirma su sesión al finalizar la clase."""
    # 1. Get schedule
    sched_res = await db.execute(
        select(GymClassSchedule).where(GymClassSchedule.id == sched_id)
    )
    sched = sched_res.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Clase no encontrada")

    if sched.live_status == GymClassLiveStatus.PENDING:
        raise HTTPException(status_code=400, detail="La clase todavía no ha comenzado")

    # 2. Check confirmed booking
    booking_res = await db.execute(
        select(ClassBooking).where(
            ClassBooking.schedule_id == sched_id,
            ClassBooking.user_id == current_user.id,
            ClassBooking.status.in_([BookingStatus.CONFIRMED, BookingStatus.ATTENDED]),
        )
    )
    if not booking_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="No tienes reserva confirmada en esta clase")

    # 3. Check not already saved
    existing_res = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.class_schedule_id == sched_id,
            WorkoutSession.user_id == current_user.id,
        )
    )
    if existing_res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya guardaste tu sesión para esta clase")

    # 4. Create session
    now = datetime.now(timezone.utc)
    session = WorkoutSession(
        user_id=current_user.id,
        template_id=None,
        session_type=SessionType.CLASS,
        class_schedule_id=sched_id,
        started_at=sched.starts_at,
        finished_at=now,
        total_duration_sec=body.total_duration_sec,
        notes=body.notes,
        rpe=body.rpe,
        mood=body.mood,
    )
    db.add(session)
    await db.flush()

    # 5. Create sets
    for set_data in body.sets:
        db.add(SessionSet(
            session_id=session.id,
            exercise_id=set_data.exercise_id,
            set_number=set_data.set_number,
            sets_count=set_data.sets_count,
            reps=set_data.reps,
            weight_kg=set_data.weight_kg,
            distance_m=set_data.distance_m,
            duration_sec=set_data.duration_sec,
            calories=set_data.calories,
            rpe=set_data.rpe,
            notes=set_data.notes,
        ))
    await db.flush()

    # 6. Reload session with sets+exercises for PR detection
    loaded_res = await db.execute(
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets).selectinload(SessionSet.exercise))
        .where(WorkoutSession.id == session.id)
    )
    session = loaded_res.scalar_one()

    # 7. Detect personal records
    new_records = await _detect_personal_records_gym(db, session, current_user.id, now)

    # 8. Award XP
    await award_session_xp(db, session, current_user.id, new_pr_count=len(new_records))

    await db.commit()
    await db.refresh(session)
    return session


async def _detect_personal_records_gym(
    db: AsyncSession, session: WorkoutSession, user_id: int, finished_at: datetime
) -> list[PersonalRecord]:
    """Detect PRs from a class session's sets."""
    new_records: list[PersonalRecord] = []

    for s in session.sets:
        if s.weight_kg and s.weight_kg > 0:
            cur = await db.execute(
                select(PersonalRecord).where(
                    PersonalRecord.user_id == user_id,
                    PersonalRecord.exercise_id == s.exercise_id,
                    PersonalRecord.record_type == RecordType.MAX_WEIGHT,
                )
            )
            existing = cur.scalar_one_or_none()
            if not existing or s.weight_kg > existing.value:
                if existing:
                    existing.value = s.weight_kg
                    existing.achieved_at = finished_at
                    existing.session_id = session.id
                else:
                    pr = PersonalRecord(
                        user_id=user_id,
                        exercise_id=s.exercise_id,
                        record_type=RecordType.MAX_WEIGHT,
                        value=s.weight_kg,
                        achieved_at=finished_at,
                        session_id=session.id,
                    )
                    db.add(pr)
                    new_records.append(pr)

        if s.reps and s.reps > 0 and (not s.weight_kg or s.weight_kg == 0):
            cur = await db.execute(
                select(PersonalRecord).where(
                    PersonalRecord.user_id == user_id,
                    PersonalRecord.exercise_id == s.exercise_id,
                    PersonalRecord.record_type == RecordType.MAX_REPS,
                )
            )
            existing = cur.scalar_one_or_none()
            if not existing or s.reps > existing.value:
                if existing:
                    existing.value = s.reps
                    existing.achieved_at = finished_at
                    existing.session_id = session.id
                else:
                    pr = PersonalRecord(
                        user_id=user_id,
                        exercise_id=s.exercise_id,
                        record_type=RecordType.MAX_REPS,
                        value=float(s.reps),
                        achieved_at=finished_at,
                        session_id=session.id,
                    )
                    db.add(pr)
                    new_records.append(pr)

        if s.distance_m and s.distance_m > 0:
            cur = await db.execute(
                select(PersonalRecord).where(
                    PersonalRecord.user_id == user_id,
                    PersonalRecord.exercise_id == s.exercise_id,
                    PersonalRecord.record_type == RecordType.MAX_DISTANCE,
                )
            )
            existing = cur.scalar_one_or_none()
            if not existing or s.distance_m > existing.value:
                if existing:
                    existing.value = s.distance_m
                    existing.achieved_at = finished_at
                    existing.session_id = session.id
                else:
                    pr = PersonalRecord(
                        user_id=user_id,
                        exercise_id=s.exercise_id,
                        record_type=RecordType.MAX_DISTANCE,
                        value=s.distance_m,
                        achieved_at=finished_at,
                        session_id=session.id,
                    )
                    db.add(pr)
                    new_records.append(pr)

    return new_records
