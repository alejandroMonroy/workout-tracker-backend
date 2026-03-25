"""XP awarding service — called from session endpoints."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import SessionSet, WorkoutSession
from app.models.xp import XP_AWARDS, XPReason, XPTransaction, level_from_xp


async def award_xp(
    db: AsyncSession,
    user_id: int,
    amount: int,
    reason: XPReason,
    description: str | None = None,
    session_id: int | None = None,
) -> XPTransaction:
    """Create a single XP transaction and update user totals."""
    from app.models.user import User

    tx = XPTransaction(
        user_id=user_id,
        amount=amount,
        reason=reason,
        description=description,
        session_id=session_id,
    )
    db.add(tx)

    # Update cached totals on user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.total_xp = (user.total_xp or 0) + amount
    user.level = level_from_xp(user.total_xp)

    return tx


async def deduct_xp(
    db: AsyncSession,
    user_id: int,
    amount: int,
    reason: XPReason,
    description: str | None = None,
) -> XPTransaction:
    """Deduct XP from a user. Raises ValueError if balance is insufficient."""
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    if (user.total_xp or 0) < amount:
        raise ValueError(f"XP insuficiente: tienes {user.total_xp} XP, necesitas {amount}")

    return await award_xp(db, user_id, -amount, reason, description)


async def award_session_xp(
    db: AsyncSession,
    session: WorkoutSession,
    user_id: int,
    new_pr_count: int = 0,
) -> list[XPTransaction]:
    """Award all applicable XP for a completed session."""
    txs: list[XPTransaction] = []

    # 1. Check if this is the user's very first session
    count_result = await db.execute(
        select(func.count(WorkoutSession.id)).where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.finished_at.is_not(None),
        )
    )
    total_sessions = count_result.scalar_one()

    if total_sessions == 1:
        tx = await award_xp(
            db, user_id, XP_AWARDS[XPReason.FIRST_SESSION],
            XPReason.FIRST_SESSION,
            "¡Primera sesión completada!",
            session.id,
        )
        txs.append(tx)

    # 2. Session complete base XP
    tx = await award_xp(
        db, user_id, XP_AWARDS[XPReason.SESSION_COMPLETE],
        XPReason.SESSION_COMPLETE,
        f"Sesión #{session.id} completada",
        session.id,
    )
    txs.append(tx)

    # 3. Personal records
    for i in range(new_pr_count):
        tx = await award_xp(
            db, user_id, XP_AWARDS[XPReason.PERSONAL_RECORD],
            XPReason.PERSONAL_RECORD,
            f"¡Nuevo récord personal! (#{i + 1})",
            session.id,
        )
        txs.append(tx)

    # 4. Exercise variety (5+ distinct exercises in session)
    variety_result = await db.execute(
        select(func.count(distinct(SessionSet.exercise_id))).where(
            SessionSet.session_id == session.id
        )
    )
    distinct_exercises = variety_result.scalar_one()
    if distinct_exercises >= 5:
        tx = await award_xp(
            db, user_id, XP_AWARDS[XPReason.EXERCISE_VARIETY],
            XPReason.EXERCISE_VARIETY,
            f"{distinct_exercises} ejercicios distintos",
            session.id,
        )
        txs.append(tx)

    # 5. Long session (> 60 min)
    if session.total_duration_sec and session.total_duration_sec > 3600:
        minutes = session.total_duration_sec // 60
        tx = await award_xp(
            db, user_id, XP_AWARDS[XPReason.LONG_SESSION],
            XPReason.LONG_SESSION,
            f"Sesión de {minutes} minutos",
            session.id,
        )
        txs.append(tx)

    # 6. High volume (> 5000 kg total volume)
    vol_result = await db.execute(
        select(
            func.sum(
                func.coalesce(SessionSet.reps, 0)
                * func.coalesce(SessionSet.weight_kg, 0)
            )
        ).where(SessionSet.session_id == session.id)
    )
    total_volume = vol_result.scalar_one() or 0
    if total_volume > 5000:
        tx = await award_xp(
            db, user_id, XP_AWARDS[XPReason.HIGH_VOLUME],
            XPReason.HIGH_VOLUME,
            f"Volumen: {total_volume:,.0f} kg",
            session.id,
        )
        txs.append(tx)

    # 7. Streak — check consecutive days
    streak = await _calculate_streak(db, user_id)
    if streak >= 2:
        # Award streak bonus for each day beyond 1
        bonus = min(streak, 7) * XP_AWARDS[XPReason.STREAK_BONUS]
        tx = await award_xp(
            db, user_id, bonus,
            XPReason.STREAK_BONUS,
            f"Racha de {streak} días · +{bonus} XP",
            session.id,
        )
        txs.append(tx)

    # 8. Consistency milestone — 7-day streak
    if streak >= 7:
        # Check we haven't awarded this for this streak already
        existing = await db.execute(
            select(XPTransaction).where(
                XPTransaction.user_id == user_id,
                XPTransaction.reason == XPReason.CONSISTENCY,
                XPTransaction.created_at >= datetime.now(timezone.utc) - timedelta(days=7),
            )
        )
        if not existing.scalar_one_or_none():
            tx = await award_xp(
                db, user_id, XP_AWARDS[XPReason.CONSISTENCY],
                XPReason.CONSISTENCY,
                "🔥 ¡7 días consecutivos entrenando!",
                session.id,
            )
            txs.append(tx)

    return txs


async def _calculate_streak(db: AsyncSession, user_id: int) -> int:
    """Calculate the current consecutive training days streak."""
    result = await db.execute(
        select(func.date(WorkoutSession.started_at))
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.finished_at.is_not(None),
        )
        .group_by(func.date(WorkoutSession.started_at))
        .order_by(func.date(WorkoutSession.started_at).desc())
    )
    dates = [row[0] for row in result.all()]

    if not dates:
        return 0

    today = datetime.now(timezone.utc).date()
    streak = 0

    for i, d in enumerate(dates):
        expected = today - timedelta(days=i)
        if d == expected:
            streak += 1
        else:
            break

    return streak
