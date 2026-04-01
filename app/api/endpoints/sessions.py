from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.exercise import Exercise
from app.models.record import PersonalRecord, RecordType
from app.models.session import SessionSet, WorkoutSession
from app.models.template import TemplateBlock, WorkoutTemplate
from app.models.user import User
from app.models.xp import XPTransaction, level_from_xp
from app.models.message import CoachMessage
from app.schemas.session import (
    SessionCreate,
    SessionFinish,
    SessionListResponse,
    SessionResponse,
    SessionSetCreate,
    SessionSetResponse,
    SessionSummaryResponse,
)
from app.services.xp import award_session_xp

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=list[SessionListResponse])
async def list_sessions(
    exercise_id: int | None = Query(None, description="Filtrar por ejercicio"),
    date_from: datetime | None = Query(None, description="Desde fecha"),
    date_to: datetime | None = Query(None, description="Hasta fecha"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(WorkoutSession).where(WorkoutSession.user_id == current_user.id)

    if date_from:
        query = query.where(WorkoutSession.started_at >= date_from)
    if date_to:
        query = query.where(WorkoutSession.started_at <= date_to)
    if exercise_id:
        query = query.where(
            WorkoutSession.id.in_(
                select(SessionSet.session_id)
                .where(SessionSet.exercise_id == exercise_id)
                .distinct()
            )
        )

    query = query.order_by(WorkoutSession.started_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    sessions = result.scalars().all()

    response = []
    for session in sessions:
        # Count sets and distinct exercises
        sets_result = await db.execute(
            select(
                func.coalesce(func.sum(SessionSet.sets_count), func.count(SessionSet.id)),
                func.count(func.distinct(SessionSet.exercise_id)),
            ).where(SessionSet.session_id == session.id)
        )
        set_count, exercise_count = sets_result.one()

        # Check if session has personal records
        has_records_result = await db.execute(
            select(
                exists(
                    select(PersonalRecord.id).where(
                        PersonalRecord.session_id == session.id
                    )
                )
            )
        )
        has_records = has_records_result.scalar_one()

        session_data = SessionListResponse.model_validate(session)
        session_data.set_count = set_count
        session_data.has_records = has_records
        if session.template_id:
            tmpl = await db.get(WorkoutTemplate, session.template_id)
            session_data.template_name = tmpl.name if tmpl else None
            if exercise_count == 0:
                block_count_result = await db.execute(
                    select(func.count(TemplateBlock.id)).where(
                        TemplateBlock.template_id == session.template_id
                    )
                )
                exercise_count = block_count_result.scalar_one()
        session_data.exercise_count = exercise_count
        response.append(session_data)

    return response


@router.get("/{session_id}", response_model=SessionSummaryResponse)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets).selectinload(SessionSet.exercise))
        .where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    summary = SessionSummaryResponse.model_validate(session)

    if session.finished_at:
        # XP earned for this session
        xp_result = await db.execute(
            select(func.coalesce(func.sum(XPTransaction.amount), 0)).where(
                XPTransaction.session_id == session.id,
                XPTransaction.user_id == current_user.id,
                XPTransaction.amount > 0,
            )
        )
        summary.xp_earned = xp_result.scalar_one()

        # PR count for this session
        pr_result = await db.execute(
            select(func.count(PersonalRecord.id)).where(
                PersonalRecord.session_id == session.id,
                PersonalRecord.user_id == current_user.id,
            )
        )
        summary.pr_count = pr_result.scalar_one()

        # Total volume
        summary.total_volume_kg = sum(
            (s.reps or 0) * (s.weight_kg or 0.0) for s in session.sets
        )

        # Coach message
        msg_result = await db.execute(
            select(CoachMessage)
            .options(selectinload(CoachMessage.coach))
            .where(CoachMessage.session_id == session.id)
            .order_by(CoachMessage.sent_at.desc())
            .limit(1)
        )
        coach_msg = msg_result.scalar_one_or_none()
        if coach_msg:
            summary.coach_message = coach_msg.body
            summary.coach_name = coach_msg.coach.name

    return summary


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = WorkoutSession(
        user_id=current_user.id,
        template_id=data.template_id,
        plan_workout_id=data.plan_workout_id,
        notes=data.notes,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    result = await db.execute(
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets))
        .where(WorkoutSession.id == session.id)
    )
    return result.scalar_one()


@router.post("/{session_id}/sets", response_model=SessionSetResponse, status_code=status.HTTP_201_CREATED)
async def add_set(
    session_id: int,
    data: SessionSetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify session belongs to user and is not finished
    result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if session.finished_at:
        raise HTTPException(status_code=400, detail="La sesión ya está finalizada")

    # Verify exercise exists
    ex_result = await db.execute(select(Exercise).where(Exercise.id == data.exercise_id))
    exercise = ex_result.scalar_one_or_none()
    if not exercise:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")

    session_set = SessionSet(
        session_id=session_id,
        exercise_id=data.exercise_id,
        set_number=data.set_number,
        sets_count=data.sets_count,
        reps=data.reps,
        weight_kg=data.weight_kg,
        distance_m=data.distance_m,
        duration_sec=data.duration_sec,
        calories=data.calories,
        rpe=data.rpe,
        notes=data.notes,
    )
    db.add(session_set)
    await db.flush()
    await db.refresh(session_set)

    # Reload with exercise relationship
    result = await db.execute(
        select(SessionSet)
        .options(selectinload(SessionSet.exercise))
        .where(SessionSet.id == session_set.id)
    )
    return result.scalar_one()


@router.delete("/{session_id}/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_set(
    session_id: int,
    set_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify session belongs to user
    sess_result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == current_user.id,
        )
    )
    session = sess_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if session.finished_at:
        raise HTTPException(status_code=400, detail="La sesión ya está finalizada")

    result = await db.execute(
        select(SessionSet).where(
            SessionSet.id == set_id,
            SessionSet.session_id == session_id,
        )
    )
    session_set = result.scalar_one_or_none()
    if not session_set:
        raise HTTPException(status_code=404, detail="Set no encontrado")
    await db.delete(session_set)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a session and clean up related XP and records."""
    result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Sum XP that was awarded for this session
    xp_result = await db.execute(
        select(func.coalesce(func.sum(XPTransaction.amount), 0)).where(
            XPTransaction.session_id == session_id,
            XPTransaction.user_id == current_user.id,
        )
    )
    xp_to_remove = xp_result.scalar_one()

    # Delete XP transactions linked to this session
    await db.execute(
        select(XPTransaction).where(XPTransaction.session_id == session_id)
    )
    from sqlalchemy import delete as sa_delete
    await db.execute(
        sa_delete(XPTransaction).where(XPTransaction.session_id == session_id)
    )

    # Nullify session_id on personal records (keep the records)
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(PersonalRecord)
        .where(PersonalRecord.session_id == session_id)
        .values(session_id=None)
    )

    # Delete the session (sets cascade automatically)
    await db.delete(session)

    # Update user XP totals
    if xp_to_remove > 0:
        current_user.total_xp = max(0, (current_user.total_xp or 0) - xp_to_remove)
        current_user.level = level_from_xp(current_user.total_xp)

    await db.flush()


@router.patch("/{session_id}/finish", response_model=SessionSummaryResponse)
async def finish_session(
    session_id: int,
    data: SessionFinish,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets).selectinload(SessionSet.exercise))
        .where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if session.finished_at:
        raise HTTPException(status_code=400, detail="La sesión ya está finalizada")

    now = datetime.now(timezone.utc)
    session.finished_at = now
    session.total_duration_sec = data.duration_sec if data.duration_sec is not None else int((now - session.started_at).total_seconds())
    if data.notes is not None:
        session.notes = data.notes
    if data.rpe is not None:
        session.rpe = data.rpe
    if data.mood is not None:
        session.mood = data.mood

    # Detect personal records
    new_records = await _detect_personal_records(db, session, current_user.id)

    # Award XP
    xp_transactions = await award_session_xp(db, session, current_user.id, new_pr_count=len(new_records))
    xp_earned = sum(tx.amount for tx in xp_transactions)

    # Total volume lifted (reps * weight_kg across all sets)
    total_volume_kg = sum(
        (s.reps or 0) * (s.weight_kg or 0.0)
        for s in session.sets
    )

    # Coach message for this session (most recent)
    coach_message_body: str | None = None
    coach_name: str | None = None
    msg_result = await db.execute(
        select(CoachMessage)
        .options(selectinload(CoachMessage.coach))
        .where(CoachMessage.session_id == session.id)
        .order_by(CoachMessage.sent_at.desc())
        .limit(1)
    )
    coach_msg = msg_result.scalar_one_or_none()
    if coach_msg:
        coach_message_body = coach_msg.body
        coach_name = coach_msg.coach.name

    await db.flush()

    # Reload session with relationships to avoid expired lazy-loads after flush
    reloaded = await db.execute(
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets).selectinload(SessionSet.exercise))
        .where(WorkoutSession.id == session_id)
        .execution_options(populate_existing=True)
    )
    session = reloaded.scalar_one()

    summary = SessionSummaryResponse.model_validate(session)
    summary.xp_earned = xp_earned
    summary.pr_count = len(new_records)
    summary.total_volume_kg = total_volume_kg
    summary.coach_message = coach_message_body
    summary.coach_name = coach_name
    return summary


async def _detect_personal_records(
    db: AsyncSession, session: WorkoutSession, user_id: int
) -> list[PersonalRecord]:
    """Check session sets for new personal records."""
    new_records: list[PersonalRecord] = []

    for s in session.sets:
        # Max weight lifted in a single set
        if s.weight_kg and s.weight_kg > 0:
            current = await db.execute(
                select(PersonalRecord).where(
                    PersonalRecord.user_id == user_id,
                    PersonalRecord.exercise_id == s.exercise_id,
                    PersonalRecord.record_type == RecordType.MAX_WEIGHT,
                )
            )
            existing = current.scalar_one_or_none()

            if not existing or s.weight_kg > existing.value:
                if existing:
                    existing.value = s.weight_kg
                    existing.achieved_at = session.finished_at
                    existing.session_id = session.id
                else:
                    pr = PersonalRecord(
                        user_id=user_id,
                        exercise_id=s.exercise_id,
                        record_type=RecordType.MAX_WEIGHT,
                        value=s.weight_kg,
                        achieved_at=session.finished_at,
                        session_id=session.id,
                    )
                    db.add(pr)
                    new_records.append(pr)

        # Max reps in a single set (bodyweight exercises)
        if s.reps and s.reps > 0 and (not s.weight_kg or s.weight_kg == 0):
            current = await db.execute(
                select(PersonalRecord).where(
                    PersonalRecord.user_id == user_id,
                    PersonalRecord.exercise_id == s.exercise_id,
                    PersonalRecord.record_type == RecordType.MAX_REPS,
                )
            )
            existing = current.scalar_one_or_none()

            if not existing or s.reps > existing.value:
                if existing:
                    existing.value = s.reps
                    existing.achieved_at = session.finished_at
                    existing.session_id = session.id
                else:
                    pr = PersonalRecord(
                        user_id=user_id,
                        exercise_id=s.exercise_id,
                        record_type=RecordType.MAX_REPS,
                        value=float(s.reps),
                        achieved_at=session.finished_at,
                        session_id=session.id,
                    )
                    db.add(pr)
                    new_records.append(pr)

        # Max distance
        if s.distance_m and s.distance_m > 0:
            current = await db.execute(
                select(PersonalRecord).where(
                    PersonalRecord.user_id == user_id,
                    PersonalRecord.exercise_id == s.exercise_id,
                    PersonalRecord.record_type == RecordType.MAX_DISTANCE,
                )
            )
            existing = current.scalar_one_or_none()

            if not existing or s.distance_m > existing.value:
                if existing:
                    existing.value = s.distance_m
                    existing.achieved_at = session.finished_at
                    existing.session_id = session.id
                else:
                    pr = PersonalRecord(
                        user_id=user_id,
                        exercise_id=s.exercise_id,
                        record_type=RecordType.MAX_DISTANCE,
                        value=s.distance_m,
                        achieved_at=session.finished_at,
                        session_id=session.id,
                    )
                    db.add(pr)
                    new_records.append(pr)

    return new_records
