from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.coach_athlete import CoachSubscription
from app.models.message import CoachMessage
from app.models.session import WorkoutSession
from app.models.user import User, UserRole
from app.schemas.message import CoachMessageCreate, CoachMessageResponse

router = APIRouter(tags=["Messages"])

_MSG_OPTIONS = [selectinload(CoachMessage.athlete), selectinload(CoachMessage.coach)]


def _to_response(m: CoachMessage) -> CoachMessageResponse:
    return CoachMessageResponse(
        id=m.id,
        session_id=m.session_id,
        athlete_id=m.athlete_id,
        athlete_name=m.athlete.name,
        coach_id=m.coach_id,
        body=m.body,
        sent_at=m.sent_at,
        read_at=m.read_at,
    )


# ── Athlete: send message to coach after a session ──────────────────────────

@router.post("/sessions/{session_id}/message", response_model=CoachMessageResponse, status_code=201)
async def send_message_to_coach(
    session_id: int,
    data: CoachMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete sends a message to their coach, linked to a completed session."""
    # Verify session ownership
    result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Find athlete's coach
    result = await db.execute(
        select(CoachSubscription).where(CoachSubscription.athlete_id == current_user.id)
    )
    subscription = result.scalars().first()
    if not subscription:
        raise HTTPException(status_code=400, detail="No tienes un entrenador asignado")

    message = CoachMessage(
        session_id=session_id,
        athlete_id=current_user.id,
        coach_id=subscription.coach_id,
        body=data.body,
    )
    db.add(message)
    await db.flush()

    result = await db.execute(
        select(CoachMessage)
        .options(*_MSG_OPTIONS)
        .where(CoachMessage.id == message.id)
        .execution_options(populate_existing=True)
    )
    return _to_response(result.scalar_one())


# ── Coach: read inbox ────────────────────────────────────────────────────────

@router.get("/messages/inbox", response_model=list[CoachMessageResponse])
async def get_inbox(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Coach retrieves all messages from their athletes."""
    if current_user.role != UserRole.COACH:
        raise HTTPException(status_code=403, detail="Solo entrenadores pueden ver su inbox")

    result = await db.execute(
        select(CoachMessage)
        .options(*_MSG_OPTIONS)
        .where(CoachMessage.coach_id == current_user.id)
        .order_by(CoachMessage.sent_at.desc())
    )
    return [_to_response(m) for m in result.scalars().all()]


@router.patch("/messages/{message_id}/read", response_model=CoachMessageResponse)
async def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Coach marks a message as read."""
    result = await db.execute(
        select(CoachMessage)
        .options(*_MSG_OPTIONS)
        .where(CoachMessage.id == message_id, CoachMessage.coach_id == current_user.id)
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")

    if not message.read_at:
        message.read_at = datetime.now(timezone.utc)
        await db.flush()

    return _to_response(message)
