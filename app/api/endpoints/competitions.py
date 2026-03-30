from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.competition import (
    Competition,
    CompetitionPlace,
    CompetitionResult,
    CompetitionResultStatus,
    CompetitionSubscription,
    CompetitionWorkout,
)
from app.models.session import WorkoutSession
from app.models.user import User
from app.models.xp import XPReason, XPTransaction
from app.schemas.competition import (
    CompetitionCreate,
    CompetitionPlaceCreate,
    CompetitionPlaceResponse,
    CompetitionResponse,
    CompetitionWorkoutCreate,
    CompetitionWorkoutResponse,
    LeaderboardEntry,
    WorkoutResultEntry,
    WorkoutResultSubmit,
)

router = APIRouter(prefix="/competitions", tags=["Competitions"])

_ALLOWED_ROLES = {"coach", "gym"}


def _xp_for_position(position: int) -> int:
    if position == 1:
        return 300
    if position == 2:
        return 200
    if position == 3:
        return 150
    return max(30, 150 - (position - 3) * 15)


async def _load_competition(competition_id: int, db: AsyncSession) -> Competition:
    result = await db.execute(
        select(Competition)
        .where(Competition.id == competition_id)
        .options(
            selectinload(Competition.creator),
            selectinload(Competition.places),
            selectinload(Competition.subscriptions),
            selectinload(Competition.workouts)
            .selectinload(CompetitionWorkout.template),
            selectinload(Competition.workouts)
            .selectinload(CompetitionWorkout.places),
        )
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Competición no encontrada")
    return c


def _workout_response(w: CompetitionWorkout) -> CompetitionWorkoutResponse:
    return CompetitionWorkoutResponse(
        id=w.id,
        template_id=w.template_id,
        template_name=w.template.name,
        init_time=w.init_time,
        order=w.order,
        notes=w.notes,
        places=[CompetitionPlaceResponse(id=p.id, name=p.name) for p in w.places],
    )


def _to_response(c: Competition, current_user_id: int) -> CompetitionResponse:
    subscribed_ids = {s.athlete_id for s in c.subscriptions}
    return CompetitionResponse(
        id=c.id,
        name=c.name,
        description=c.description,
        created_by=c.created_by,
        creator_name=c.creator.name,
        location=c.location,
        init_date=c.init_date,
        end_date=c.end_date,
        inscription_xp_cost=c.inscription_xp_cost,
        subscriber_count=len(c.subscriptions),
        is_subscribed=current_user_id in subscribed_ids,
        created_at=c.created_at,
        places=[CompetitionPlaceResponse(id=p.id, name=p.name) for p in c.places],
        workouts=[_workout_response(w) for w in c.workouts],
    )


# ── Create ────────────────────────────────────────────────────────────────────


@router.post("", response_model=CompetitionResponse, status_code=201)
async def create_competition(
    data: CompetitionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role.value not in _ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Solo entrenadores y gimnasios pueden crear competiciones")
    if data.end_date <= data.init_date:
        raise HTTPException(status_code=400, detail="La fecha de fin debe ser posterior a la de inicio")

    competition = Competition(
        name=data.name,
        description=data.description,
        created_by=current_user.id,
        location=data.location,
        init_date=data.init_date,
        end_date=data.end_date,
        inscription_xp_cost=data.inscription_xp_cost,
    )
    db.add(competition)
    await db.flush()
    await db.refresh(competition, ["creator", "places", "workouts", "subscriptions"])
    return _to_response(competition, current_user.id)


# ── List ──────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[CompetitionResponse])
async def list_competitions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Competition)
        .options(
            selectinload(Competition.creator),
            selectinload(Competition.places),
            selectinload(Competition.subscriptions),
            selectinload(Competition.workouts).selectinload(CompetitionWorkout.template),
            selectinload(Competition.workouts).selectinload(CompetitionWorkout.places),
        )
        .order_by(Competition.init_date.desc())
    )
    return [_to_response(c, current_user.id) for c in result.scalars().all()]


# ── Get detail ────────────────────────────────────────────────────────────────


@router.get("/{competition_id}", response_model=CompetitionResponse)
async def get_competition(
    competition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)
    return _to_response(c, current_user.id)


# ── Delete ────────────────────────────────────────────────────────────────────


@router.delete("/{competition_id}", status_code=204)
async def delete_competition(
    competition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)
    if c.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")
    await db.delete(c)
    await db.flush()


# ── Place management ──────────────────────────────────────────────────────────


@router.post("/{competition_id}/places", response_model=CompetitionPlaceResponse, status_code=201)
async def add_place(
    competition_id: int,
    data: CompetitionPlaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)
    if c.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    place = CompetitionPlace(competition_id=competition_id, name=data.name)
    db.add(place)
    await db.flush()
    return CompetitionPlaceResponse(id=place.id, name=place.name)


@router.delete("/{competition_id}/places/{place_id}", status_code=204)
async def remove_place(
    competition_id: int,
    place_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)
    if c.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    place = next((p for p in c.places if p.id == place_id), None)
    if not place:
        raise HTTPException(status_code=404, detail="Sede no encontrada")
    await db.delete(place)
    await db.flush()


# ── Add workout ───────────────────────────────────────────────────────────────


@router.post("/{competition_id}/workouts", response_model=CompetitionWorkoutResponse, status_code=201)
async def add_workout(
    competition_id: int,
    data: CompetitionWorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)
    if c.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    init_time = data.init_time
    if init_time.tzinfo is None:
        init_time = init_time.replace(tzinfo=timezone.utc)

    if not (c.init_date <= init_time <= c.end_date):
        raise HTTPException(
            status_code=400,
            detail="La fecha del workout debe estar entre la fecha de inicio y fin de la competición",
        )

    # Resolve and validate places
    place_map = {p.id: p for p in c.places}
    invalid = [pid for pid in data.place_ids if pid not in place_map]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Sedes no encontradas: {invalid}")

    workout = CompetitionWorkout(
        competition_id=competition_id,
        template_id=data.template_id,
        init_time=init_time,
        order=data.order,
        notes=data.notes,
        places=[place_map[pid] for pid in data.place_ids],
    )
    db.add(workout)
    await db.flush()
    await db.refresh(workout, ["template", "places"])
    return _workout_response(workout)


# ── Remove workout ────────────────────────────────────────────────────────────


@router.delete("/{competition_id}/workouts/{workout_id}", status_code=204)
async def remove_workout(
    competition_id: int,
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)
    if c.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    workout = next((w for w in c.workouts if w.id == workout_id), None)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout no encontrado")
    await db.delete(workout)
    await db.flush()


# ── Subscribe ─────────────────────────────────────────────────────────────────


@router.post("/{competition_id}/subscribe", status_code=204)
async def subscribe(
    competition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)

    already = next((s for s in c.subscriptions if s.athlete_id == current_user.id), None)
    if already:
        raise HTTPException(status_code=409, detail="Ya estás inscrito en esta competición")

    now = datetime.now(timezone.utc)
    if now > c.end_date:
        raise HTTPException(status_code=400, detail="La competición ya ha terminado")

    if c.inscription_xp_cost > 0:
        if current_user.total_xp < c.inscription_xp_cost:
            raise HTTPException(status_code=400, detail="XP insuficiente para inscribirse")
        current_user.total_xp -= c.inscription_xp_cost
        db.add(XPTransaction(
            user_id=current_user.id,
            amount=-c.inscription_xp_cost,
            reason=XPReason.EVENT_REGISTRATION,
            description=f"Inscripción en competición: {c.name}",
        ))

    db.add(CompetitionSubscription(
        competition_id=competition_id,
        athlete_id=current_user.id,
    ))
    await db.flush()


# ── Unsubscribe ───────────────────────────────────────────────────────────────


@router.delete("/{competition_id}/subscribe", status_code=204)
async def unsubscribe(
    competition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)
    sub = next((s for s in c.subscriptions if s.athlete_id == current_user.id), None)
    if not sub:
        raise HTTPException(status_code=404, detail="No estás inscrito en esta competición")
    await db.delete(sub)
    await db.flush()


# ── Submit session for a competition workout ──────────────────────────────────


@router.post("/{competition_id}/workouts/{workout_id}/submit", response_model=WorkoutResultEntry)
async def submit_workout_result(
    competition_id: int,
    workout_id: int,
    data: WorkoutResultSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session_id = data.session_id
    c = await _load_competition(competition_id, db)

    sub = next((s for s in c.subscriptions if s.athlete_id == current_user.id), None)
    if not sub:
        raise HTTPException(status_code=403, detail="Debes estar inscrito para enviar resultados")

    workout = next((w for w in c.workouts if w.id == workout_id), None)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout no encontrado")

    session = await db.get(WorkoutSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not session.finished_at:
        raise HTTPException(status_code=400, detail="La sesión debe estar completada")

    existing = await db.execute(
        select(CompetitionResult).where(
            CompetitionResult.competition_workout_id == workout_id,
            CompetitionResult.athlete_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya enviaste tu resultado para este workout")

    new_result = CompetitionResult(
        competition_workout_id=workout_id,
        athlete_id=current_user.id,
        session_id=session_id,
        finished_at=session.finished_at,
        status=CompetitionResultStatus.PENDING,
        position=None,
        xp_awarded=0,
    )
    db.add(new_result)
    await db.flush()
    await db.refresh(new_result, ["athlete"])

    return WorkoutResultEntry(
        id=new_result.id,
        position=new_result.position,
        athlete_id=new_result.athlete_id,
        athlete_name=new_result.athlete.name,
        finished_at=new_result.finished_at,
        status=new_result.status.value,
        xp_awarded=new_result.xp_awarded,
        session_id=new_result.session_id,
    )


# ── Workout results ───────────────────────────────────────────────────────────


@router.get("/{competition_id}/workouts/{workout_id}/results", response_model=list[WorkoutResultEntry])
async def get_workout_results(
    competition_id: int,
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)
    workout = next((w for w in c.workouts if w.id == workout_id), None)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout no encontrado")

    is_owner = c.created_by == current_user.id

    q = (
        select(CompetitionResult)
        .where(CompetitionResult.competition_workout_id == workout_id)
        .options(selectinload(CompetitionResult.athlete))
    )
    # Non-owners only see validated results and their own pending/rejected
    if not is_owner:
        from sqlalchemy import or_
        q = q.where(
            or_(
                CompetitionResult.status == CompetitionResultStatus.VALIDATED,
                CompetitionResult.athlete_id == current_user.id,
            )
        )
    q = q.order_by(CompetitionResult.position.asc().nullslast(), CompetitionResult.finished_at.asc())

    result = await db.execute(q)
    rows = result.scalars().all()
    return [
        WorkoutResultEntry(
            id=r.id,
            position=r.position,
            athlete_id=r.athlete_id,
            athlete_name=r.athlete.name,
            finished_at=r.finished_at,
            status=r.status.value,
            xp_awarded=r.xp_awarded,
            session_id=r.session_id,
        )
        for r in rows
    ]


# ── Validate / Reject result (owner only) ────────────────────────────────────


async def _get_result(result_id: int, workout_id: int, db: AsyncSession) -> CompetitionResult:
    r = await db.get(CompetitionResult, result_id)
    if not r or r.competition_workout_id != workout_id:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    return r


async def _recalculate_positions(workout_id: int, competition_id: int, db: AsyncSession) -> None:
    """Recalculate positions and XP for all validated results of a workout."""
    validated_q = await db.execute(
        select(CompetitionResult)
        .where(
            CompetitionResult.competition_workout_id == workout_id,
            CompetitionResult.status == CompetitionResultStatus.VALIDATED,
        )
        .order_by(CompetitionResult.finished_at.asc())
    )
    validated = list(validated_q.scalars().all())

    for idx, r in enumerate(validated):
        new_position = idx + 1
        new_xp = _xp_for_position(new_position)
        xp_diff = new_xp - r.xp_awarded

        r.position = new_position
        r.xp_awarded = new_xp

        if xp_diff != 0:
            athlete = await db.get(User, r.athlete_id)
            athlete.total_xp += xp_diff
            db.add(XPTransaction(
                user_id=r.athlete_id,
                amount=xp_diff,
                reason=XPReason.COMPETITION_WORKOUT,
                description=f"Posición {new_position} en workout de competición #{competition_id}",
            ))


@router.post(
    "/{competition_id}/workouts/{workout_id}/results/{result_id}/validate",
    response_model=WorkoutResultEntry,
)
async def validate_result(
    competition_id: int,
    workout_id: int,
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)
    if c.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el organizador puede validar resultados")

    r = await _get_result(result_id, workout_id, db)
    if r.status != CompetitionResultStatus.PENDING:
        raise HTTPException(status_code=409, detail="El resultado ya fue procesado")

    r.status = CompetitionResultStatus.VALIDATED
    await db.flush()

    await _recalculate_positions(workout_id, competition_id, db)
    await db.flush()
    await db.refresh(r, ["athlete"])

    return WorkoutResultEntry(
        id=r.id,
        position=r.position,
        athlete_id=r.athlete_id,
        athlete_name=r.athlete.name,
        finished_at=r.finished_at,
        status=r.status.value,
        xp_awarded=r.xp_awarded,
        session_id=r.session_id,
    )


@router.post(
    "/{competition_id}/workouts/{workout_id}/results/{result_id}/reject",
    response_model=WorkoutResultEntry,
)
async def reject_result(
    competition_id: int,
    workout_id: int,
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)
    if c.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el organizador puede rechazar resultados")

    r = await _get_result(result_id, workout_id, db)
    if r.status != CompetitionResultStatus.PENDING:
        raise HTTPException(status_code=409, detail="El resultado ya fue procesado")

    r.status = CompetitionResultStatus.REJECTED
    await db.flush()
    await db.refresh(r, ["athlete"])

    return WorkoutResultEntry(
        id=r.id,
        position=r.position,
        athlete_id=r.athlete_id,
        athlete_name=r.athlete.name,
        finished_at=r.finished_at,
        status=r.status.value,
        xp_awarded=r.xp_awarded,
        session_id=r.session_id,
    )


# ── Overall leaderboard ───────────────────────────────────────────────────────


@router.get("/{competition_id}/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    competition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    c = await _load_competition(competition_id, db)

    result = await db.execute(
        select(CompetitionResult)
        .join(CompetitionWorkout, CompetitionResult.competition_workout_id == CompetitionWorkout.id)
        .where(
            CompetitionWorkout.competition_id == competition_id,
            CompetitionResult.status == CompetitionResultStatus.VALIDATED,
        )
        .options(selectinload(CompetitionResult.athlete))
    )
    all_results = result.scalars().all()

    aggregates: dict[int, dict] = {}
    for r in all_results:
        entry = aggregates.setdefault(r.athlete_id, {
            "athlete_id": r.athlete_id,
            "athlete_name": r.athlete.name,
            "total_xp": 0,
            "workouts_completed": 0,
        })
        entry["total_xp"] += r.xp_awarded
        entry["workouts_completed"] += 1

    sorted_entries = sorted(aggregates.values(), key=lambda e: e["total_xp"], reverse=True)
    return [
        LeaderboardEntry(rank=idx + 1, **entry)
        for idx, entry in enumerate(sorted_entries)
    ]
