from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.xp import XPReason
from app.services.xp import deduct_xp
from app.models.plan import Plan
from app.models.training_center import (
    CenterClass,
    ClassBooking,
    ClassBookingStatus,
    ClassStatus,
    CenterMemberRole,
    CenterMemberStatus,
    CenterMembership,
    CenterPlan,
    CenterSubscription,
    CenterSubscriptionStatus,
    TrainingCenter,
)
from app.models.user import User
from app.schemas.training_center import (
    CenterClassCreate,
    CenterClassResponse,
    CenterMembershipResponse,
    CenterPlanResponse,
    CenterSubscriptionResponse,
    ClassBookingResponse,
    JoinCenterRequest,
    PublishPlanRequest,
    SubscribeToCenterRequest,
    TrainingCenterCreate,
    TrainingCenterListItem,
    TrainingCenterResponse,
    TrainingCenterUpdate,
    UpdateMembershipRequest,
)

router = APIRouter(prefix="/centers", tags=["Training Centers"])


# ── helpers ──────────────────────────────────────────────────────────────────


async def _member_count(db: AsyncSession, center_id: int) -> int:
    r = await db.execute(
        select(func.count(CenterMembership.id)).where(
            CenterMembership.center_id == center_id,
            CenterMembership.status == CenterMemberStatus.ACTIVE,
        )
    )
    return r.scalar_one()


async def _require_center_admin(
    db: AsyncSession, center_id: int, user: User
) -> CenterMembership:
    """User must be center owner, admin member, or platform admin."""
    # Platform admin always passes
    if user.role == "admin":
        return None

    center_res = await db.execute(
        select(TrainingCenter).where(TrainingCenter.id == center_id)
    )
    center = center_res.scalar_one_or_none()
    if not center:
        raise HTTPException(404, "Centro no encontrado")
    if center.owner_id == user.id:
        return None  # owner always passes

    mem_res = await db.execute(
        select(CenterMembership).where(
            CenterMembership.center_id == center_id,
            CenterMembership.user_id == user.id,
            CenterMembership.status == CenterMemberStatus.ACTIVE,
            CenterMembership.role == CenterMemberRole.ADMIN,
        )
    )
    mem = mem_res.scalar_one_or_none()
    if not mem:
        raise HTTPException(403, "No tienes permisos de administrador en este centro")
    return mem


# ── CRUD centers ─────────────────────────────────────────────────────────────


@router.post("", response_model=TrainingCenterResponse, status_code=status.HTTP_201_CREATED)
async def create_center(
    data: TrainingCenterCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    center = TrainingCenter(**data.model_dump(), owner_id=current_user.id)
    db.add(center)
    await db.flush()

    # Auto-add owner as ADMIN member
    membership = CenterMembership(
        center_id=center.id,
        user_id=current_user.id,
        role=CenterMemberRole.ADMIN,
        status=CenterMemberStatus.ACTIVE,
    )
    db.add(membership)
    await db.flush()

    return TrainingCenterResponse(
        **{c.name: getattr(center, c.name) for c in center.__table__.columns},
        member_count=1,
    )


@router.get("", response_model=list[TrainingCenterListItem])
async def list_centers(
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            TrainingCenter,
            func.count(CenterMembership.id).label("member_count"),
        )
        .outerjoin(
            CenterMembership,
            (CenterMembership.center_id == TrainingCenter.id)
            & (CenterMembership.status == CenterMemberStatus.ACTIVE),
        )
        .where(TrainingCenter.is_active == True)  # noqa: E712
        .group_by(TrainingCenter.id)
        .order_by(TrainingCenter.name)
        .limit(limit)
        .offset(offset)
    )
    if q:
        query = query.where(TrainingCenter.name.ilike(f"%{q}%"))

    result = await db.execute(query)
    rows = result.all()

    return [
        TrainingCenterListItem(
            id=c.id,
            name=c.name,
            description=c.description,
            city=c.city,
            logo_url=c.logo_url,
            monthly_xp=c.monthly_xp,
            member_count=cnt,
            is_active=c.is_active,
        )
        for c, cnt in rows
    ]


@router.get("/{center_id}", response_model=TrainingCenterResponse)
async def get_center(
    center_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingCenter).where(TrainingCenter.id == center_id)
    )
    center = result.scalar_one_or_none()
    if not center:
        raise HTTPException(404, "Centro no encontrado")

    count = await _member_count(db, center_id)
    return TrainingCenterResponse(
        **{c.name: getattr(center, c.name) for c in center.__table__.columns},
        member_count=count,
    )


@router.put("/{center_id}", response_model=TrainingCenterResponse)
async def update_center(
    center_id: int,
    data: TrainingCenterUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_center_admin(db, center_id, current_user)
    result = await db.execute(
        select(TrainingCenter).where(TrainingCenter.id == center_id)
    )
    center = result.scalar_one_or_none()
    if not center:
        raise HTTPException(404, "Centro no encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(center, field, value)
    await db.flush()

    count = await _member_count(db, center_id)
    return TrainingCenterResponse(
        **{c.name: getattr(center, c.name) for c in center.__table__.columns},
        member_count=count,
    )


# ── Memberships ──────────────────────────────────────────────────────────────


@router.post("/{center_id}/join", response_model=CenterMembershipResponse, status_code=201)
async def join_center(
    center_id: int,
    data: JoinCenterRequest = JoinCenterRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request to join a training center (status = pending until approved)."""
    # Check center exists
    center_res = await db.execute(
        select(TrainingCenter).where(TrainingCenter.id == center_id, TrainingCenter.is_active == True)  # noqa: E712
    )
    center = center_res.scalar_one_or_none()
    if not center:
        raise HTTPException(404, "Centro no encontrado")

    # Check not already member
    existing = await db.execute(
        select(CenterMembership).where(
            CenterMembership.center_id == center_id,
            CenterMembership.user_id == current_user.id,
            CenterMembership.status.in_([CenterMemberStatus.PENDING, CenterMemberStatus.ACTIVE]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Ya tienes una solicitud o perteneces a este centro")

    membership = CenterMembership(
        center_id=center_id,
        user_id=current_user.id,
        role=data.role,
        status=CenterMemberStatus.PENDING,
    )
    db.add(membership)
    await db.flush()

    return CenterMembershipResponse(
        id=membership.id,
        center_id=center_id,
        center_name=center.name,
        user_id=current_user.id,
        user_name=current_user.name,
        role=membership.role,
        status=membership.status,
        created_at=membership.created_at,
    )


@router.get("/{center_id}/members", response_model=list[CenterMembershipResponse])
async def list_members(
    center_id: int,
    status_filter: CenterMemberStatus | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(CenterMembership, User.name.label("uname"), TrainingCenter.name.label("cname"))
        .join(User, CenterMembership.user_id == User.id)
        .join(TrainingCenter, CenterMembership.center_id == TrainingCenter.id)
        .where(CenterMembership.center_id == center_id)
    )
    if status_filter:
        query = query.where(CenterMembership.status == status_filter)
    query = query.order_by(CenterMembership.created_at.desc())

    result = await db.execute(query)
    rows = result.all()

    return [
        CenterMembershipResponse(
            id=m.id,
            center_id=m.center_id,
            center_name=cname,
            user_id=m.user_id,
            user_name=uname,
            role=m.role,
            status=m.status,
            created_at=m.created_at,
        )
        for m, uname, cname in rows
    ]


@router.patch("/{center_id}/members/{membership_id}", response_model=CenterMembershipResponse)
async def update_membership(
    center_id: int,
    membership_id: int,
    data: UpdateMembershipRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve, reject or change role of a member (admin only)."""
    await _require_center_admin(db, center_id, current_user)

    result = await db.execute(
        select(CenterMembership).where(
            CenterMembership.id == membership_id,
            CenterMembership.center_id == center_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(404, "Miembro no encontrado")

    if data.status is not None:
        membership.status = data.status
    if data.role is not None:
        membership.role = data.role
    await db.flush()

    # Reload names
    user_res = await db.execute(select(User.name).where(User.id == membership.user_id))
    center_res = await db.execute(select(TrainingCenter.name).where(TrainingCenter.id == center_id))

    return CenterMembershipResponse(
        id=membership.id,
        center_id=membership.center_id,
        center_name=center_res.scalar_one(),
        user_id=membership.user_id,
        user_name=user_res.scalar_one(),
        role=membership.role,
        status=membership.status,
        created_at=membership.created_at,
    )


@router.get("/my/memberships", response_model=list[CenterMembershipResponse])
async def my_memberships(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all centers the current user belongs to."""
    result = await db.execute(
        select(CenterMembership, User.name.label("uname"), TrainingCenter.name.label("cname"))
        .join(User, CenterMembership.user_id == User.id)
        .join(TrainingCenter, CenterMembership.center_id == TrainingCenter.id)
        .where(CenterMembership.user_id == current_user.id)
        .order_by(CenterMembership.created_at.desc())
    )
    rows = result.all()
    return [
        CenterMembershipResponse(
            id=m.id,
            center_id=m.center_id,
            center_name=cname,
            user_id=m.user_id,
            user_name=uname,
            role=m.role,
            status=m.status,
            created_at=m.created_at,
        )
        for m, uname, cname in rows
    ]


# ── Center Plans ─────────────────────────────────────────────────────────────


@router.post("/{center_id}/plans", response_model=CenterPlanResponse, status_code=201)
async def publish_plan_to_center(
    center_id: int,
    data: PublishPlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish a plan to a training center (must be center admin or plan owner)."""
    await _require_center_admin(db, center_id, current_user)

    plan_res = await db.execute(select(Plan).where(Plan.id == data.plan_id))
    plan = plan_res.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Plan no encontrado")

    # Check not already published
    existing = await db.execute(
        select(CenterPlan).where(
            CenterPlan.center_id == center_id, CenterPlan.plan_id == data.plan_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Este plan ya está publicado en este centro")

    cp = CenterPlan(center_id=center_id, plan_id=data.plan_id)
    db.add(cp)
    await db.flush()

    return CenterPlanResponse(
        id=cp.id,
        center_id=center_id,
        plan_id=data.plan_id,
        plan_name=plan.name,
        published_at=cp.published_at,
    )


@router.get("/{center_id}/plans", response_model=list[CenterPlanResponse])
async def list_center_plans(
    center_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CenterPlan, Plan.name.label("pname"))
        .join(Plan, CenterPlan.plan_id == Plan.id)
        .where(CenterPlan.center_id == center_id)
        .order_by(CenterPlan.published_at.desc())
    )
    rows = result.all()
    return [
        CenterPlanResponse(
            id=cp.id,
            center_id=cp.center_id,
            plan_id=cp.plan_id,
            plan_name=pname,
            published_at=cp.published_at,
        )
        for cp, pname in rows
    ]


# ── Center Subscriptions ────────────────────────────────────────────


@router.post("/{center_id}/subscribe", response_model=CenterSubscriptionResponse, status_code=201)
async def subscribe_to_center(
    center_id: int,
    data: SubscribeToCenterRequest = SubscribeToCenterRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete requests a subscription to a training center."""
    center_res = await db.execute(
        select(TrainingCenter).where(TrainingCenter.id == center_id, TrainingCenter.is_active == True)  # noqa: E712
    )
    center = center_res.scalar_one_or_none()
    if not center:
        raise HTTPException(404, "Centro no encontrado")

    existing = await db.execute(
        select(CenterSubscription).where(
            CenterSubscription.center_id == center_id,
            CenterSubscription.athlete_id == current_user.id,
            CenterSubscription.status.in_([
                CenterSubscriptionStatus.PENDING,
                CenterSubscriptionStatus.ACTIVE,
            ]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Ya tienes una suscripción activa o pendiente con este centro")

    sub = CenterSubscription(
        center_id=center_id,
        athlete_id=current_user.id,
        status=CenterSubscriptionStatus.PENDING,
        xp_per_month=center.monthly_xp,
    )
    db.add(sub)
    await db.flush()

    return CenterSubscriptionResponse(
        id=sub.id,
        center_id=center_id,
        center_name=center.name,
        athlete_id=current_user.id,
        athlete_name=current_user.name,
        status=sub.status,
        xp_per_month=sub.xp_per_month,
        started_at=sub.started_at,
        expires_at=sub.expires_at,
        created_at=sub.created_at,
    )


@router.get("/{center_id}/subscriptions", response_model=list[CenterSubscriptionResponse])
async def list_center_subscriptions(
    center_id: int,
    sub_status: CenterSubscriptionStatus | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List subscriptions for a center (admin only)."""
    await _require_center_admin(db, center_id, current_user)

    query = (
        select(CenterSubscription, User.name.label("uname"), TrainingCenter.name.label("cname"))
        .join(User, CenterSubscription.athlete_id == User.id)
        .join(TrainingCenter, CenterSubscription.center_id == TrainingCenter.id)
        .where(CenterSubscription.center_id == center_id)
    )
    if sub_status:
        query = query.where(CenterSubscription.status == sub_status)
    query = query.order_by(CenterSubscription.created_at.desc())

    result = await db.execute(query)
    rows = result.all()
    return [
        CenterSubscriptionResponse(
            id=s.id,
            center_id=s.center_id,
            center_name=cname,
            athlete_id=s.athlete_id,
            athlete_name=uname,
            status=s.status,
            xp_per_month=s.xp_per_month,
            started_at=s.started_at,
            expires_at=s.expires_at,
            created_at=s.created_at,
        )
        for s, uname, cname in rows
    ]


@router.patch("/{center_id}/subscriptions/{sub_id}", response_model=CenterSubscriptionResponse)
async def update_center_subscription(
    center_id: int,
    sub_id: int,
    accept: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept or reject an athlete's center subscription request (admin only)."""
    await _require_center_admin(db, center_id, current_user)

    result = await db.execute(
        select(CenterSubscription).where(
            CenterSubscription.id == sub_id,
            CenterSubscription.center_id == center_id,
            CenterSubscription.status == CenterSubscriptionStatus.PENDING,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Solicitud no encontrada")

    if accept:
        # Deduct XP from the athlete before activating
        if sub.xp_per_month > 0:
            center_name_res = await db.execute(
                select(TrainingCenter.name).where(TrainingCenter.id == center_id)
            )
            cname = center_name_res.scalar_one()
            try:
                await deduct_xp(
                    db, sub.athlete_id, sub.xp_per_month,
                    XPReason.SUBSCRIPTION_PAYMENT,
                    f"Suscripción mensual: {cname}",
                )
            except ValueError as e:
                raise HTTPException(402, str(e))
        now = datetime.now(timezone.utc)
        sub.status = CenterSubscriptionStatus.ACTIVE
        sub.started_at = now
        sub.expires_at = now + timedelta(days=30)
    else:
        sub.status = CenterSubscriptionStatus.CANCELLED
    await db.flush()

    user_res = await db.execute(select(User.name).where(User.id == sub.athlete_id))
    center_res = await db.execute(select(TrainingCenter.name).where(TrainingCenter.id == center_id))
    return CenterSubscriptionResponse(
        id=sub.id,
        center_id=sub.center_id,
        center_name=center_res.scalar_one(),
        athlete_id=sub.athlete_id,
        athlete_name=user_res.scalar_one(),
        status=sub.status,
        xp_per_month=sub.xp_per_month,
        started_at=sub.started_at,
        expires_at=sub.expires_at,
        created_at=sub.created_at,
    )


@router.get("/my/subscriptions", response_model=list[CenterSubscriptionResponse])
async def my_center_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all center subscriptions for the current user."""
    result = await db.execute(
        select(CenterSubscription, TrainingCenter.name.label("cname"))
        .join(TrainingCenter, CenterSubscription.center_id == TrainingCenter.id)
        .where(CenterSubscription.athlete_id == current_user.id)
        .order_by(CenterSubscription.created_at.desc())
    )
    rows = result.all()
    return [
        CenterSubscriptionResponse(
            id=s.id,
            center_id=s.center_id,
            center_name=cname,
            athlete_id=s.athlete_id,
            athlete_name=current_user.name,
            status=s.status,
            xp_per_month=s.xp_per_month,
            started_at=s.started_at,
            expires_at=s.expires_at,
            created_at=s.created_at,
        )
        for s, cname in rows
    ]


# ── Center Classes ───────────────────────────────────────────────


@router.post("/{center_id}/classes", response_model=CenterClassResponse, status_code=201)
async def create_class(
    center_id: int,
    data: CenterClassCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a scheduled class (admin or coach of the center)."""
    await _require_center_admin(db, center_id, current_user)

    cls = CenterClass(
        center_id=center_id,
        coach_id=current_user.id,
        name=data.name,
        description=data.description,
        scheduled_at=data.scheduled_at,
        duration_min=data.duration_min,
        max_capacity=data.max_capacity,
        template_id=data.template_id,
        status=ClassStatus.SCHEDULED,
    )
    db.add(cls)
    await db.flush()

    return CenterClassResponse(
        id=cls.id,
        center_id=cls.center_id,
        coach_id=cls.coach_id,
        coach_name=current_user.name,
        name=cls.name,
        description=cls.description,
        scheduled_at=cls.scheduled_at,
        duration_min=cls.duration_min,
        max_capacity=cls.max_capacity,
        template_id=cls.template_id,
        status=cls.status,
        booking_count=0,
        created_at=cls.created_at,
    )


@router.get("/{center_id}/classes", response_model=list[CenterClassResponse])
async def list_classes(
    center_id: int,
    upcoming_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List classes for a center."""
    query = (
        select(
            CenterClass,
            User.name.label("coach_name"),
            func.count(ClassBooking.id).label("booking_count"),
        )
        .join(User, CenterClass.coach_id == User.id)
        .outerjoin(
            ClassBooking,
            (ClassBooking.class_id == CenterClass.id)
            & (ClassBooking.status == ClassBookingStatus.RESERVED),
        )
        .where(
            CenterClass.center_id == center_id,
            CenterClass.status == ClassStatus.SCHEDULED,
        )
        .group_by(CenterClass.id, User.name)
        .order_by(CenterClass.scheduled_at)
    )
    if upcoming_only:
        query = query.where(CenterClass.scheduled_at >= datetime.now(timezone.utc))

    result = await db.execute(query)
    rows = result.all()
    return [
        CenterClassResponse(
            id=cls.id,
            center_id=cls.center_id,
            coach_id=cls.coach_id,
            coach_name=coach_name,
            name=cls.name,
            description=cls.description,
            scheduled_at=cls.scheduled_at,
            duration_min=cls.duration_min,
            max_capacity=cls.max_capacity,
            template_id=cls.template_id,
            status=cls.status,
            booking_count=booking_count,
            created_at=cls.created_at,
        )
        for cls, coach_name, booking_count in rows
    ]


@router.post("/{center_id}/classes/{class_id}/book", response_model=ClassBookingResponse, status_code=201)
async def book_class(
    center_id: int,
    class_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete books a spot in a class (requires active center subscription)."""
    # Check active subscription
    sub_res = await db.execute(
        select(CenterSubscription).where(
            CenterSubscription.center_id == center_id,
            CenterSubscription.athlete_id == current_user.id,
            CenterSubscription.status == CenterSubscriptionStatus.ACTIVE,
        )
    )
    if not sub_res.scalar_one_or_none():
        raise HTTPException(403, "Necesitas una suscripción activa en este centro para reservar clases")

    # Check class exists and is scheduled
    cls_res = await db.execute(
        select(CenterClass).where(
            CenterClass.id == class_id,
            CenterClass.center_id == center_id,
            CenterClass.status == ClassStatus.SCHEDULED,
        )
    )
    cls = cls_res.scalar_one_or_none()
    if not cls:
        raise HTTPException(404, "Clase no encontrada")

    # Check not already booked
    existing = await db.execute(
        select(ClassBooking).where(
            ClassBooking.class_id == class_id,
            ClassBooking.athlete_id == current_user.id,
            ClassBooking.status == ClassBookingStatus.RESERVED,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Ya tienes una reserva en esta clase")

    # Check capacity
    if cls.max_capacity is not None:
        count_res = await db.execute(
            select(func.count(ClassBooking.id)).where(
                ClassBooking.class_id == class_id,
                ClassBooking.status == ClassBookingStatus.RESERVED,
            )
        )
        if count_res.scalar_one() >= cls.max_capacity:
            raise HTTPException(409, "La clase está completa")

    booking = ClassBooking(
        class_id=class_id,
        athlete_id=current_user.id,
        status=ClassBookingStatus.RESERVED,
    )
    db.add(booking)
    await db.flush()

    return ClassBookingResponse(
        id=booking.id,
        class_id=class_id,
        athlete_id=current_user.id,
        athlete_name=current_user.name,
        status=booking.status,
        booked_at=booking.booked_at,
    )


@router.get("/{center_id}/classes/{class_id}/bookings", response_model=list[ClassBookingResponse])
async def list_class_bookings(
    center_id: int,
    class_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List bookings for a class (admin or coach)."""
    await _require_center_admin(db, center_id, current_user)

    result = await db.execute(
        select(ClassBooking, User.name.label("uname"))
        .join(User, ClassBooking.athlete_id == User.id)
        .where(
            ClassBooking.class_id == class_id,
            ClassBooking.status == ClassBookingStatus.RESERVED,
        )
        .order_by(ClassBooking.booked_at)
    )
    rows = result.all()
    return [
        ClassBookingResponse(
            id=b.id,
            class_id=b.class_id,
            athlete_id=b.athlete_id,
            athlete_name=uname,
            status=b.status,
            booked_at=b.booked_at,
        )
        for b, uname in rows
    ]


@router.delete("/{center_id}/classes/{class_id}/book", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    center_id: int,
    class_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel athlete's booking for a class."""
    result = await db.execute(
        select(ClassBooking).where(
            ClassBooking.class_id == class_id,
            ClassBooking.athlete_id == current_user.id,
            ClassBooking.status == ClassBookingStatus.RESERVED,
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Reserva no encontrada")
    booking.status = ClassBookingStatus.CANCELLED
    await db.flush()
