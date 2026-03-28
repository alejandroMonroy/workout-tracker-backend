from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.challenge import Challenge, ChallengeStatus
from app.models.session import SessionSet, WorkoutSession
from app.models.user import User
from app.models.xp import XPReason, XPTransaction
from app.schemas.challenge import ChallengeCreate, ChallengeResponse, ChallengeSubmit, ChallengeUserSnippet

router = APIRouter(prefix="/challenges", tags=["Challenges"])

_CHALLENGE_DAYS = 7  # expires if not accepted within 7 days


def _to_response(c: Challenge) -> ChallengeResponse:
    return ChallengeResponse(
        id=c.id,
        challenger=ChallengeUserSnippet(id=c.challenger.id, name=c.challenger.name),
        challenged=ChallengeUserSnippet(id=c.challenged.id, name=c.challenged.name),
        wager_xp=c.wager_xp,
        status=c.status.value,
        challenger_session_id=c.challenger_session_id,
        challenged_session_id=c.challenged_session_id,
        winner_id=c.winner_id,
        created_at=c.created_at,
        expires_at=c.expires_at,
        completed_at=c.completed_at,
    )


async def _get_session_volume(session_id: int, db: AsyncSession) -> float:
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    func.coalesce(SessionSet.reps, 0) * func.coalesce(SessionSet.weight_kg, 0.0)
                ),
                0.0,
            )
        ).where(SessionSet.session_id == session_id)
    )
    return float(result.scalar_one())


async def _load(challenge_id: int, db: AsyncSession) -> Challenge:
    result = await db.execute(
        select(Challenge)
        .where(Challenge.id == challenge_id)
        .options(
            selectinload(Challenge.challenger),
            selectinload(Challenge.challenged),
        )
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Desafío no encontrado")
    return c


# ── Create ──────────────────────────────────────────────────────────────────


@router.post("", response_model=ChallengeResponse, status_code=201)
async def create_challenge(
    data: ChallengeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.challenged_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes desafiarte a ti mismo")

    opponent = await db.get(User, data.challenged_id)
    if not opponent:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if current_user.total_xp < data.wager_xp:
        raise HTTPException(status_code=400, detail="XP insuficiente para la apuesta")

    # Deduct wager from challenger immediately
    current_user.total_xp -= data.wager_xp
    db.add(XPTransaction(
        user_id=current_user.id,
        amount=-data.wager_xp,
        reason=XPReason.CHALLENGE_WAGER,
        description=f"Apuesta de desafío contra {opponent.name}",
    ))

    challenge = Challenge(
        challenger_id=current_user.id,
        challenged_id=data.challenged_id,
        wager_xp=data.wager_xp,
        status=ChallengeStatus.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(days=_CHALLENGE_DAYS),
    )
    db.add(challenge)
    await db.flush()
    await db.refresh(challenge, ["challenger", "challenged"])
    return _to_response(challenge)


# ── List ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ChallengeResponse])
async def list_challenges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Challenge)
        .where(
            or_(
                Challenge.challenger_id == current_user.id,
                Challenge.challenged_id == current_user.id,
            )
        )
        .options(
            selectinload(Challenge.challenger),
            selectinload(Challenge.challenged),
        )
        .order_by(Challenge.created_at.desc())
    )
    return [_to_response(c) for c in result.scalars().all()]


# ── Accept ────────────────────────────────────────────────────────────────────


@router.post("/{challenge_id}/accept", response_model=ChallengeResponse)
async def accept_challenge(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load(challenge_id, db)

    if c.challenged_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")
    if c.status != ChallengeStatus.PENDING:
        raise HTTPException(status_code=409, detail="El desafío ya no está pendiente")
    if datetime.now(timezone.utc) > c.expires_at:
        raise HTTPException(status_code=410, detail="El desafío ha expirado")

    if current_user.total_xp < c.wager_xp:
        raise HTTPException(status_code=400, detail="XP insuficiente para aceptar el desafío")

    current_user.total_xp -= c.wager_xp
    db.add(XPTransaction(
        user_id=current_user.id,
        amount=-c.wager_xp,
        reason=XPReason.CHALLENGE_WAGER,
        description=f"Apuesta de desafío contra {c.challenger.name}",
    ))

    c.status = ChallengeStatus.ACCEPTED
    await db.flush()
    return _to_response(c)


# ── Decline ───────────────────────────────────────────────────────────────────


@router.post("/{challenge_id}/decline", response_model=ChallengeResponse)
async def decline_challenge(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load(challenge_id, db)

    if c.challenged_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")
    if c.status != ChallengeStatus.PENDING:
        raise HTTPException(status_code=409, detail="El desafío ya no está pendiente")

    # Refund challenger
    challenger = await db.get(User, c.challenger_id)
    challenger.total_xp += c.wager_xp
    db.add(XPTransaction(
        user_id=c.challenger_id,
        amount=c.wager_xp,
        reason=XPReason.CHALLENGE_WAGER,
        description=f"Reembolso: desafío rechazado por {current_user.name}",
    ))

    c.status = ChallengeStatus.DECLINED
    await db.flush()
    return _to_response(c)


# ── Cancel ────────────────────────────────────────────────────────────────────


@router.post("/{challenge_id}/cancel", response_model=ChallengeResponse)
async def cancel_challenge(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load(challenge_id, db)

    if c.challenger_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el retador puede cancelar")
    if c.status != ChallengeStatus.PENDING:
        raise HTTPException(status_code=409, detail="Solo se puede cancelar un desafío pendiente")

    # Refund challenger
    current_user.total_xp += c.wager_xp
    db.add(XPTransaction(
        user_id=current_user.id,
        amount=c.wager_xp,
        reason=XPReason.CHALLENGE_WAGER,
        description="Reembolso: desafío cancelado",
    ))

    c.status = ChallengeStatus.CANCELLED
    await db.flush()
    return _to_response(c)


# ── Submit session result ─────────────────────────────────────────────────────


@router.post("/{challenge_id}/submit", response_model=ChallengeResponse)
async def submit_challenge_result(
    challenge_id: int,
    data: ChallengeSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load(challenge_id, db)

    if c.status != ChallengeStatus.ACCEPTED:
        raise HTTPException(status_code=409, detail="El desafío debe estar aceptado para enviar resultado")

    is_challenger = c.challenger_id == current_user.id
    is_challenged = c.challenged_id == current_user.id
    if not is_challenger and not is_challenged:
        raise HTTPException(status_code=403, detail="Sin permiso")

    # Verify session ownership and completion
    session = await db.get(WorkoutSession, data.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not session.finished_at:
        raise HTTPException(status_code=400, detail="La sesión debe estar completada")

    if is_challenger:
        if c.challenger_session_id is not None:
            raise HTTPException(status_code=409, detail="Ya enviaste tu resultado")
        c.challenger_session_id = data.session_id
    else:
        if c.challenged_session_id is not None:
            raise HTTPException(status_code=409, detail="Ya enviaste tu resultado")
        c.challenged_session_id = data.session_id

    await db.flush()

    # Resolve if both have submitted
    if c.challenger_session_id and c.challenged_session_id:
        challenger_vol = await _get_session_volume(c.challenger_session_id, db)
        challenged_vol = await _get_session_volume(c.challenged_session_id, db)

        # Challenger wins on tie
        winner_id = c.challenger_id if challenger_vol >= challenged_vol else c.challenged_id
        loser_id = c.challenged_id if winner_id == c.challenger_id else c.challenger_id

        winner = await db.get(User, winner_id)
        winner.total_xp += c.wager_xp * 2
        db.add(XPTransaction(
            user_id=winner_id,
            amount=c.wager_xp * 2,
            reason=XPReason.CHALLENGE_WIN,
            description=f"Victoria en desafío #{c.id}",
        ))

        c.winner_id = winner_id
        c.status = ChallengeStatus.COMPLETED
        c.completed_at = datetime.now(timezone.utc)

    await db.flush()
    return _to_response(c)
