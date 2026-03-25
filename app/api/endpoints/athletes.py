from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.exercise import Exercise
from app.models.friendship import Friendship, FriendshipStatus
from app.models.record import PersonalRecord
from app.models.session import SessionSet, WorkoutSession
from app.models.user import User
from app.schemas.friendship import (
    AthleteProfile,
    AthletePublic,
    FriendshipResponse,
    RecordPublic,
    RecentSessionPublic,
)

router = APIRouter(tags=["Athletes"])


# ── helpers ─────────────────────────────────────────────────────────────────


def _friendship_status(f: Friendship | None, current_user_id: int) -> str | None:
    if f is None:
        return None
    if f.status == FriendshipStatus.ACCEPTED:
        return "accepted"
    return "pending_sent" if f.requester_id == current_user_id else "pending_received"


def _to_athlete_public(user: User, f: Friendship | None, current_user_id: int) -> AthletePublic:
    return AthletePublic(
        id=user.id,
        name=user.name,
        avatar_url=user.avatar_url,
        level=user.level,
        total_xp=user.total_xp,
        current_division=user.current_division,
        friendship_id=f.id if f else None,
        friendship_status=_friendship_status(f, current_user_id),
    )


async def _load_friendship_map(db: AsyncSession, current_user_id: int) -> dict[int, Friendship]:
    result = await db.execute(
        select(Friendship).where(
            or_(
                Friendship.requester_id == current_user_id,
                Friendship.addressee_id == current_user_id,
            )
        )
    )
    fmap: dict[int, Friendship] = {}
    for f in result.scalars().all():
        other = f.addressee_id if f.requester_id == current_user_id else f.requester_id
        fmap[other] = f
    return fmap


# ── search athletes ──────────────────────────────────────────────────────────


@router.get("/athletes", response_model=list[AthletePublic])
async def search_athletes(
    search: str | None = Query(None, description="Buscar por nombre"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fmap = await _load_friendship_map(db, current_user.id)

    q = select(User).where(User.id != current_user.id)
    if search and search.strip():
        q = q.where(User.name.ilike(f"%{search.strip()}%"))
    q = q.order_by(User.total_xp.desc()).offset((page - 1) * limit).limit(limit)

    result = await db.execute(q)
    athletes = result.scalars().all()

    return [_to_athlete_public(a, fmap.get(a.id), current_user.id) for a in athletes]


# ── athlete profile (friend-gated) ──────────────────────────────────────────


@router.get("/athletes/{user_id}", response_model=AthleteProfile)
async def get_athlete_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Use /api/auth/me for your own profile")

    athlete = await db.get(User, user_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")

    fmap = await _load_friendship_map(db, current_user.id)
    f = fmap.get(user_id)
    base = _to_athlete_public(athlete, f, current_user.id)

    # Only friends can see detailed data
    is_friend = f is not None and f.status == FriendshipStatus.ACCEPTED
    if not is_friend:
        return AthleteProfile(**base.model_dump(), sessions_30d=0, total_sessions=0, records=[], recent_sessions=[])

    # Total sessions
    total_result = await db.execute(
        select(func.count(WorkoutSession.id)).where(WorkoutSession.user_id == user_id)
    )
    total_sessions = total_result.scalar() or 0

    # Sessions last 30 days
    since = datetime.now(timezone.utc) - timedelta(days=30)
    recent_count_result = await db.execute(
        select(func.count(WorkoutSession.id)).where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.started_at >= since,
        )
    )
    sessions_30d = recent_count_result.scalar() or 0

    # Top 5 personal records with exercise name
    records_result = await db.execute(
        select(PersonalRecord, Exercise.name)
        .join(Exercise, PersonalRecord.exercise_id == Exercise.id)
        .where(PersonalRecord.user_id == user_id)
        .order_by(PersonalRecord.achieved_at.desc())
        .limit(5)
    )
    records = [
        RecordPublic(
            id=pr.id,
            exercise_id=pr.exercise_id,
            exercise_name=ex_name,
            record_type=pr.record_type.value,
            value=pr.value,
            achieved_at=pr.achieved_at,
        )
        for pr, ex_name in records_result.all()
    ]

    # Recent 5 sessions
    sessions_result = await db.execute(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user_id)
        .order_by(WorkoutSession.started_at.desc())
        .limit(5)
        .options(selectinload(WorkoutSession.sets))
    )
    recent_sessions_raw = sessions_result.scalars().all()

    recent_sessions = [
        RecentSessionPublic(
            id=s.id,
            started_at=s.started_at,
            finished_at=s.finished_at,
            total_duration_sec=s.total_duration_sec,
            exercise_count=len({ss.exercise_id for ss in s.sets}),
            set_count=len(s.sets),
        )
        for s in recent_sessions_raw
    ]

    return AthleteProfile(
        **base.model_dump(),
        sessions_30d=sessions_30d,
        total_sessions=total_sessions,
        records=records,
        recent_sessions=recent_sessions,
    )


# ── send friend request ──────────────────────────────────────────────────────


@router.post("/friends/request/{user_id}", response_model=FriendshipResponse, status_code=201)
async def send_friend_request(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes enviarte una solicitud a ti mismo")

    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Check existing in either direction
    existing = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == user_id),
                and_(Friendship.requester_id == user_id, Friendship.addressee_id == current_user.id),
            )
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Ya existe una relación con este usuario")

    f = Friendship(requester_id=current_user.id, addressee_id=user_id)
    db.add(f)
    await db.commit()
    await db.refresh(f)

    return FriendshipResponse(
        id=f.id,
        requester_id=f.requester_id,
        addressee_id=f.addressee_id,
        status=f.status,
        created_at=f.created_at,
        other_user=_to_athlete_public(target, f, current_user.id),
    )


# ── list friends ─────────────────────────────────────────────────────────────


@router.get("/friends", response_model=list[FriendshipResponse])
async def list_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Friendship)
        .where(
            Friendship.status == FriendshipStatus.ACCEPTED,
            or_(
                Friendship.requester_id == current_user.id,
                Friendship.addressee_id == current_user.id,
            ),
        )
        .options(selectinload(Friendship.requester), selectinload(Friendship.addressee))
    )
    friendships = result.scalars().all()

    out = []
    for f in friendships:
        other = f.addressee if f.requester_id == current_user.id else f.requester
        out.append(
            FriendshipResponse(
                id=f.id,
                requester_id=f.requester_id,
                addressee_id=f.addressee_id,
                status=f.status,
                created_at=f.created_at,
                other_user=_to_athlete_public(other, f, current_user.id),
            )
        )
    return out


# ── pending requests received ────────────────────────────────────────────────


@router.get("/friends/requests", response_model=list[FriendshipResponse])
async def list_friend_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Friendship)
        .where(
            Friendship.addressee_id == current_user.id,
            Friendship.status == FriendshipStatus.PENDING,
        )
        .options(selectinload(Friendship.requester))
    )
    friendships = result.scalars().all()

    return [
        FriendshipResponse(
            id=f.id,
            requester_id=f.requester_id,
            addressee_id=f.addressee_id,
            status=f.status,
            created_at=f.created_at,
            other_user=_to_athlete_public(f.requester, f, current_user.id),
        )
        for f in friendships
    ]


# ── accept request ───────────────────────────────────────────────────────────


@router.post("/friends/requests/{friendship_id}/accept", response_model=FriendshipResponse)
async def accept_friend_request(
    friendship_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    f = await db.get(Friendship, friendship_id, options=[selectinload(Friendship.requester)])
    if not f or f.addressee_id != current_user.id:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if f.status != FriendshipStatus.PENDING:
        raise HTTPException(status_code=409, detail="La solicitud ya fue procesada")

    f.status = FriendshipStatus.ACCEPTED
    await db.commit()
    await db.refresh(f)

    return FriendshipResponse(
        id=f.id,
        requester_id=f.requester_id,
        addressee_id=f.addressee_id,
        status=f.status,
        created_at=f.created_at,
        other_user=_to_athlete_public(f.requester, f, current_user.id),
    )


# ── decline / cancel request ─────────────────────────────────────────────────


@router.delete("/friends/requests/{friendship_id}", status_code=204)
async def delete_friend_request(
    friendship_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    f = await db.get(Friendship, friendship_id)
    if not f:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    # Requester can cancel; addressee can decline
    if f.requester_id != current_user.id and f.addressee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    await db.delete(f)
    await db.commit()


# ── unfriend ─────────────────────────────────────────────────────────────────


@router.delete("/friends/{user_id}", status_code=204)
async def unfriend(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Friendship).where(
            Friendship.status == FriendshipStatus.ACCEPTED,
            or_(
                and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == user_id),
                and_(Friendship.requester_id == user_id, Friendship.addressee_id == current_user.id),
            ),
        )
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Amistad no encontrada")

    await db.delete(f)
    await db.commit()
