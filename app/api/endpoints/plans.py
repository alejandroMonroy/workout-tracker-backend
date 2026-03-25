from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_coach
from app.models.coach_subscription import CoachSubscription, CoachSubscriptionStatus
from app.models.exercise import Exercise
from app.models.plan import (
    BlockExercise,
    Plan,
    PlanEnrollment,
    PlanEnrollmentStatus,
    PlanSession,
    SessionBlock,
)
from app.models.user import User
from app.schemas.plan import (
    PlanCreate,
    PlanEnrollmentCreate,
    PlanEnrollmentResponse,
    PlanListResponse,
    PlanResponse,
    PlanSessionCreate,
    PlanSessionResponse,
    PlanUpdate,
)

router = APIRouter(prefix="/plans", tags=["Plans"])

# ── Eager-loading helper ────────────────────────────────────

_plan_eager = (
    selectinload(Plan.sessions)
    .selectinload(PlanSession.blocks)
    .selectinload(SessionBlock.exercises)
    .selectinload(BlockExercise.exercise)
)


# ══════════════════════════════════════════════════════
#  Plans CRUD
# ══════════════════════════════════════════════════════


@router.get("", response_model=list[PlanListResponse])
async def list_plans(
    search: str | None = Query(None, description="Buscar por nombre"),
    mine_only: bool = Query(False, description="Solo mis planes"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List plans: public + own (or mine_only)."""
    query = select(Plan)

    if mine_only:
        query = query.where(Plan.created_by == current_user.id)
    else:
        query = query.where(
            or_(
                Plan.is_public.is_(True),
                Plan.created_by == current_user.id,
            )
        )

    if search:
        query = query.where(Plan.name.ilike(f"%{search}%"))

    query = query.order_by(Plan.id.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    plans = result.scalars().all()

    # Build response with session counts
    response = []
    for plan in plans:
        count_result = await db.execute(
            select(func.count(PlanSession.id)).where(
                PlanSession.plan_id == plan.id
            )
        )
        session_count = count_result.scalar_one()
        # Get coach name
        coach_result = await db.execute(
            select(User.name).where(User.id == plan.created_by)
        )
        coach_name = coach_result.scalar_one_or_none()
        data = PlanListResponse.model_validate(plan)
        data.session_count = session_count
        data.coach_name = coach_name
        response.append(data)

    return response


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a plan with all sessions, blocks, and exercises."""
    result = await db.execute(
        select(Plan).options(_plan_eager).where(Plan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if not plan.is_public and plan.created_by != current_user.id:
        # Check if athlete is enrolled
        sub_result = await db.execute(
            select(PlanEnrollment).where(
                PlanEnrollment.plan_id == plan_id,
                PlanEnrollment.athlete_id == current_user.id,
                PlanEnrollment.status == PlanEnrollmentStatus.ACTIVE,
            )
        )
        if not sub_result.scalar_one_or_none():
            raise HTTPException(
                status_code=403, detail="No tienes acceso a este plan"
            )
    # Add coach name
    coach_result = await db.execute(
        select(User.name).where(User.id == plan.created_by)
    )
    resp = PlanResponse.model_validate(plan)
    resp.coach_name = coach_result.scalar_one_or_none()
    return resp


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    data: PlanCreate,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Create a plan with optional sessions/blocks/exercises (coach only)."""
    # Validate all exercise IDs
    all_exercise_ids: set[int] = set()
    for s in data.sessions:
        for b in s.blocks:
            for e in b.exercises:
                all_exercise_ids.add(e.exercise_id)

    if all_exercise_ids:
        result = await db.execute(
            select(Exercise.id).where(Exercise.id.in_(all_exercise_ids))
        )
        found_ids = set(result.scalars().all())
        missing = all_exercise_ids - found_ids
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Ejercicios no encontrados: {missing}",
            )

    plan = Plan(
        name=data.name,
        description=data.description,
        duration_weeks=data.duration_weeks,
        is_public=data.is_public,
        created_by=current_user.id,
    )
    db.add(plan)
    await db.flush()

    for session_data in data.sessions:
        session = PlanSession(
            plan_id=plan.id,
            name=session_data.name,
            description=session_data.description,
            day_number=session_data.day_number,
        )
        db.add(session)
        await db.flush()

        for block_data in session_data.blocks:
            block = SessionBlock(
                plan_session_id=session.id,
                name=block_data.name,
                block_type=block_data.block_type,
                modality=block_data.modality,
                rounds=block_data.rounds,
                time_cap_sec=block_data.time_cap_sec,
                work_sec=block_data.work_sec,
                rest_sec=block_data.rest_sec,
                order=block_data.order,
            )
            db.add(block)
            await db.flush()

            for ex_data in block_data.exercises:
                block_ex = BlockExercise(
                    block_id=block.id,
                    exercise_id=ex_data.exercise_id,
                    order=ex_data.order,
                    target_sets=ex_data.target_sets,
                    target_reps=ex_data.target_reps,
                    target_weight_kg=ex_data.target_weight_kg,
                    target_distance_m=ex_data.target_distance_m,
                    target_duration_sec=ex_data.target_duration_sec,
                    rest_sec=ex_data.rest_sec,
                    notes=ex_data.notes,
                )
                db.add(block_ex)

    await db.flush()

    # Reload with relationships
    result = await db.execute(
        select(Plan).options(_plan_eager).where(Plan.id == plan.id)
    )
    return result.scalar_one()


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    data: PlanUpdate,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Update plan metadata (name, description, etc.)."""
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes editar este plan")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    await db.flush()

    result = await db.execute(
        select(Plan).options(_plan_eager).where(Plan.id == plan.id)
    )
    return result.scalar_one()


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Delete a plan and all nested data."""
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar este plan")
    await db.delete(plan)


# ══════════════════════════════════════════════════════
#  Plan Sessions CRUD
# ══════════════════════════════════════════════════════


@router.post(
    "/{plan_id}/sessions",
    response_model=PlanSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_plan_session(
    plan_id: int,
    data: PlanSessionCreate,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Add a session to a plan."""
    plan = await _get_own_plan(db, plan_id, current_user.id)

    # Validate exercise IDs
    all_exercise_ids: set[int] = set()
    for b in data.blocks:
        for e in b.exercises:
            all_exercise_ids.add(e.exercise_id)

    if all_exercise_ids:
        result = await db.execute(
            select(Exercise.id).where(Exercise.id.in_(all_exercise_ids))
        )
        found_ids = set(result.scalars().all())
        missing = all_exercise_ids - found_ids
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Ejercicios no encontrados: {missing}",
            )

    session = PlanSession(
        plan_id=plan.id,
        name=data.name,
        description=data.description,
        day_number=data.day_number,
    )
    db.add(session)
    await db.flush()

    for block_data in data.blocks:
        block = SessionBlock(
            plan_session_id=session.id,
            name=block_data.name,
            block_type=block_data.block_type,
            modality=block_data.modality,
            rounds=block_data.rounds,
            time_cap_sec=block_data.time_cap_sec,
            work_sec=block_data.work_sec,
            rest_sec=block_data.rest_sec,
            order=block_data.order,
        )
        db.add(block)
        await db.flush()

        for ex_data in block_data.exercises:
            block_ex = BlockExercise(
                block_id=block.id,
                exercise_id=ex_data.exercise_id,
                order=ex_data.order,
                target_sets=ex_data.target_sets,
                target_reps=ex_data.target_reps,
                target_weight_kg=ex_data.target_weight_kg,
                target_distance_m=ex_data.target_distance_m,
                target_duration_sec=ex_data.target_duration_sec,
                rest_sec=ex_data.rest_sec,
                notes=ex_data.notes,
            )
            db.add(block_ex)

    await db.flush()

    # Reload
    result = await db.execute(
        select(PlanSession)
        .options(
            selectinload(PlanSession.blocks)
            .selectinload(SessionBlock.exercises)
            .selectinload(BlockExercise.exercise)
        )
        .where(PlanSession.id == session.id)
    )
    return result.scalar_one()


@router.delete(
    "/{plan_id}/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_plan_session(
    plan_id: int,
    session_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Delete a session from a plan."""
    await _get_own_plan(db, plan_id, current_user.id)

    result = await db.execute(
        select(PlanSession).where(
            PlanSession.id == session_id,
            PlanSession.plan_id == plan_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    await db.delete(session)


# ══════════════════════════════════════════════════════
#  Plan Enrollments
# ══════════════════════════════════════════════════════


@router.post(
    "/enroll",
    response_model=PlanEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_in_plan(
    data: PlanEnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete self-enrolls in a public plan."""
    result = await db.execute(
        select(Plan).where(Plan.id == data.plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    if plan.created_by == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes inscribirte en tu propio plan")

    if not plan.is_public:
        # Allow if the athlete has an active subscription to the plan's coach
        sub_res = await db.execute(
            select(CoachSubscription).where(
                CoachSubscription.coach_id == plan.created_by,
                CoachSubscription.athlete_id == current_user.id,
                CoachSubscription.status == CoachSubscriptionStatus.ACTIVE,
            )
        )
        if not sub_res.scalar_one_or_none():
            raise HTTPException(
                status_code=403,
                detail="Este plan es privado. Necesitas una suscripción activa con el coach.",
            )

    existing = await db.execute(
        select(PlanEnrollment).where(
            PlanEnrollment.plan_id == data.plan_id,
            PlanEnrollment.athlete_id == current_user.id,
            PlanEnrollment.status == PlanEnrollmentStatus.ACTIVE,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya estás inscrito en este plan")

    enrollment = PlanEnrollment(
        plan_id=data.plan_id,
        athlete_id=current_user.id,
        assigned_by_coach=False,
        status=PlanEnrollmentStatus.ACTIVE,
    )
    db.add(enrollment)
    await db.flush()
    await db.refresh(enrollment)

    result = await db.execute(
        select(PlanEnrollment)
        .options(selectinload(PlanEnrollment.plan))
        .where(PlanEnrollment.id == enrollment.id)
    )
    enrollment_obj = result.scalar_one()
    enrollment_data = PlanEnrollmentResponse.model_validate(enrollment_obj)
    if enrollment_obj.plan:
        count_result = await db.execute(
            select(func.count(PlanSession.id)).where(
                PlanSession.plan_id == enrollment_obj.plan.id
            )
        )
        enrollment_data.plan.session_count = count_result.scalar_one()  # type: ignore[union-attr]
    return enrollment_data


@router.get("/coach/{coach_id}/available", response_model=list[PlanListResponse])
async def list_coach_plans_for_athlete(
    coach_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List plans from a coach available to the current athlete.

    Returns public plans always. Returns private plans only if athlete
    has an active subscription to that coach.
    """
    # Check if athlete has active subscription to this coach
    sub_res = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.coach_id == coach_id,
            CoachSubscription.athlete_id == current_user.id,
            CoachSubscription.status == CoachSubscriptionStatus.ACTIVE,
        )
    )
    has_subscription = sub_res.scalar_one_or_none() is not None

    query = select(Plan).where(Plan.created_by == coach_id)
    if not has_subscription:
        query = query.where(Plan.is_public.is_(True))
    query = query.order_by(Plan.id.desc())

    result = await db.execute(query)
    plans = result.scalars().all()

    response = []
    for plan in plans:
        count_result = await db.execute(
            select(func.count(PlanSession.id)).where(PlanSession.plan_id == plan.id)
        )
        coach_result = await db.execute(
            select(User.name).where(User.id == plan.created_by)
        )
        data = PlanListResponse.model_validate(plan)
        data.session_count = count_result.scalar_one()
        data.coach_name = coach_result.scalar_one_or_none()
        response.append(data)

    return response


@router.get("/enrollments/mine", response_model=list[PlanEnrollmentResponse])
async def my_enrollments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's active plan enrollments."""
    result = await db.execute(
        select(PlanEnrollment)
        .options(selectinload(PlanEnrollment.plan))
        .where(
            PlanEnrollment.athlete_id == current_user.id,
            PlanEnrollment.status == PlanEnrollmentStatus.ACTIVE,
        )
        .order_by(PlanEnrollment.enrolled_at.desc())
    )
    enrollments = result.scalars().all()

    response = []
    for enrollment in enrollments:
        enrollment_data = PlanEnrollmentResponse.model_validate(enrollment)
        if enrollment.plan:
            count_result = await db.execute(
                select(func.count(PlanSession.id)).where(
                    PlanSession.plan_id == enrollment.plan.id
                )
            )
            enrollment_data.plan.session_count = count_result.scalar_one()  # type: ignore[union-attr]
            coach_result = await db.execute(
                select(User.name).where(User.id == enrollment.plan.created_by)
            )
            enrollment_data.plan.coach_name = coach_result.scalar_one_or_none()  # type: ignore[union-attr]
        response.append(enrollment_data)

    return response


@router.delete("/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_enrollment(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a plan enrollment."""
    result = await db.execute(
        select(PlanEnrollment).where(
            PlanEnrollment.id == enrollment_id,
            PlanEnrollment.athlete_id == current_user.id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    enrollment.status = PlanEnrollmentStatus.CANCELLED
    await db.flush()


# ══════════════════════════════════════════════════════
#  Get plan session detail (for starting a workout)
# ══════════════════════════════════════════════════════


@router.get(
    "/sessions/{plan_session_id}",
    response_model=PlanSessionResponse,
)
async def get_plan_session(
    plan_session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a plan session with all blocks and exercises.

    Accessible if the user is the plan creator or is subscribed.
    """
    result = await db.execute(
        select(PlanSession)
        .options(
            selectinload(PlanSession.blocks)
            .selectinload(SessionBlock.exercises)
            .selectinload(BlockExercise.exercise)
        )
        .where(PlanSession.id == plan_session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión de plan no encontrada")

    # Check access
    plan_result = await db.execute(
        select(Plan).where(Plan.id == session.plan_id)
    )
    plan = plan_result.scalar_one()

    if plan.created_by != current_user.id and not plan.is_public:
        sub = await db.execute(
            select(PlanEnrollment).where(
                PlanEnrollment.plan_id == plan.id,
                PlanEnrollment.athlete_id == current_user.id,
                PlanEnrollment.status == PlanEnrollmentStatus.ACTIVE,
            )
        )
        if not sub.scalar_one_or_none():
            raise HTTPException(
                status_code=403,
                detail="No tienes acceso a esta sesión de plan",
            )

    return session


# ── Helpers ───────────────────────────────────────────


async def _get_own_plan(db: AsyncSession, plan_id: int, user_id: int) -> Plan:
    """Get a plan owned by user_id, or raise 404/403."""
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if plan.created_by != user_id:
        raise HTTPException(status_code=403, detail="No puedes modificar este plan")
    return plan
