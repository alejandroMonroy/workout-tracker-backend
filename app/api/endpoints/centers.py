from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.plan import Plan
from app.models.training_center import (
    CenterMemberRole,
    CenterMemberStatus,
    CenterMembership,
    CenterPlan,
    TrainingCenter,
)
from app.models.user import User
from app.schemas.training_center import (
    CenterMembershipResponse,
    CenterPlanResponse,
    JoinCenterRequest,
    PublishPlanRequest,
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
    db: AsyncSession, center_id: int, user_id: int
) -> CenterMembership:
    """User must be center owner or admin member."""
    center_res = await db.execute(
        select(TrainingCenter).where(TrainingCenter.id == center_id)
    )
    center = center_res.scalar_one_or_none()
    if not center:
        raise HTTPException(404, "Centro no encontrado")
    if center.owner_id == user_id:
        return None  # owner always passes

    mem_res = await db.execute(
        select(CenterMembership).where(
            CenterMembership.center_id == center_id,
            CenterMembership.user_id == user_id,
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
    current_user: User = Depends(get_current_user),
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
    await _require_center_admin(db, center_id, current_user.id)
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
    await _require_center_admin(db, center_id, current_user.id)

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
    await _require_center_admin(db, center_id, current_user.id)

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
