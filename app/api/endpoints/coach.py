from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_coach
from app.models.coach_athlete import CoachAthlete, CoachAthleteStatus
from app.models.exercise import Exercise
from app.models.plan import Plan, PlanSession, Subscription, SubscriptionStatus
from app.models.record import PersonalRecord
from app.models.session import SessionSet, WorkoutSession
from app.models.template import TemplateBlock, WorkoutTemplate
from app.models.user import User, UserRole
from app.schemas.record import RecordResponse
from app.schemas.session import SessionListResponse
from app.schemas.template import TemplateResponse
from app.schemas.plan import PlanListResponse
from app.schemas.coach import (
    AssignTemplateRequest,
    CoachAthleteResponse,
    CoachProfileResponse,
    CoachRequestResponse,
    InviteAthleteRequest,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/coach", tags=["Coach"])


# --- Helper ---

async def _verify_coach_athlete(
    db: AsyncSession, coach_id: int, athlete_id: int
) -> CoachAthlete:
    """Verify the coach-athlete relationship exists and is active."""
    result = await db.execute(
        select(CoachAthlete).where(
            CoachAthlete.coach_id == coach_id,
            CoachAthlete.athlete_id == athlete_id,
            CoachAthlete.status == CoachAthleteStatus.ACTIVE,
        )
    )
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(
            status_code=403,
            detail="No tienes una relación activa con este atleta",
        )
    return rel


# --- Coach discovery ---


@router.get("/directory", response_model=list[CoachProfileResponse])
async def list_coaches(
    search: str | None = Query(None, description="Buscar por nombre"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all coaches with stats for athlete discovery."""
    query = select(User).where(User.role == UserRole.COACH)
    if search:
        query = query.where(User.name.ilike(f"%{search}%"))
    query = query.order_by(User.name).limit(limit).offset(offset)
    result = await db.execute(query)
    coaches = result.scalars().all()

    response = []
    for coach in coaches:
        # Athlete count (active)
        athlete_count_result = await db.execute(
            select(func.count(CoachAthlete.id)).where(
                CoachAthlete.coach_id == coach.id,
                CoachAthlete.status == CoachAthleteStatus.ACTIVE,
            )
        )
        athlete_count = athlete_count_result.scalar_one()

        # Plan count (public)
        plan_count_result = await db.execute(
            select(func.count(Plan.id)).where(
                Plan.created_by == coach.id,
                Plan.is_public.is_(True),
            )
        )
        plan_count = plan_count_result.scalar_one()

        # Existing relationship with current user
        rel_result = await db.execute(
            select(CoachAthlete).where(
                CoachAthlete.coach_id == coach.id,
                CoachAthlete.athlete_id == current_user.id,
            )
        )
        rel = rel_result.scalar_one_or_none()

        response.append(
            CoachProfileResponse(
                id=coach.id,
                name=coach.name,
                email=coach.email,
                avatar_url=coach.avatar_url,
                athlete_count=athlete_count,
                plan_count=plan_count,
                relationship_status=rel.status.value if rel else None,
                relationship_initiated_by=rel.initiated_by if rel else None,
            )
        )
    return response


@router.post("/request/{coach_id}", status_code=status.HTTP_201_CREATED)
async def request_coach(
    coach_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete sends a coaching request to a coach."""
    # Verify coach exists
    result = await db.execute(
        select(User).where(User.id == coach_id, User.role == UserRole.COACH)
    )
    coach = result.scalar_one_or_none()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach no encontrado")
    if coach.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes solicitar ser tu propio atleta")

    # Check existing relationship
    existing = await db.execute(
        select(CoachAthlete).where(
            CoachAthlete.coach_id == coach_id,
            CoachAthlete.athlete_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe una relación con este coach")

    rel = CoachAthlete(
        coach_id=coach_id,
        athlete_id=current_user.id,
        status=CoachAthleteStatus.PENDING,
        initiated_by="athlete",
    )
    db.add(rel)
    await db.flush()
    return {"message": f"Solicitud enviada a {coach.name}", "status": "pending"}


@router.get("/requests/pending", response_model=list[CoachRequestResponse])
async def get_pending_requests(
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Coach views pending athlete requests."""
    result = await db.execute(
        select(CoachAthlete, User)
        .join(User, User.id == CoachAthlete.athlete_id)
        .where(
            CoachAthlete.coach_id == current_user.id,
            CoachAthlete.status == CoachAthleteStatus.PENDING,
            CoachAthlete.initiated_by == "athlete",
        )
        .order_by(CoachAthlete.created_at.desc())
    )
    rows = result.all()
    return [
        CoachRequestResponse(
            id=rel.id,
            athlete=UserResponse.model_validate(athlete),
            created_at=rel.created_at,
        )
        for rel, athlete in rows
    ]


@router.post("/requests/{request_id}/accept")
async def accept_athlete_request(
    request_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Coach accepts an athlete's coaching request."""
    result = await db.execute(
        select(CoachAthlete).where(
            CoachAthlete.id == request_id,
            CoachAthlete.coach_id == current_user.id,
            CoachAthlete.status == CoachAthleteStatus.PENDING,
            CoachAthlete.initiated_by == "athlete",
        )
    )
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    rel.status = CoachAthleteStatus.ACTIVE
    await db.flush()
    return {"message": "Solicitud aceptada", "status": "active"}


@router.post("/requests/{request_id}/reject")
async def reject_athlete_request(
    request_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Coach rejects an athlete's coaching request."""
    result = await db.execute(
        select(CoachAthlete).where(
            CoachAthlete.id == request_id,
            CoachAthlete.coach_id == current_user.id,
            CoachAthlete.status == CoachAthleteStatus.PENDING,
            CoachAthlete.initiated_by == "athlete",
        )
    )
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    await db.delete(rel)
    await db.flush()
    return {"message": "Solicitud rechazada"}


# --- Invite / manage athletes ---


@router.post("/invite", status_code=status.HTTP_201_CREATED)
async def invite_athlete(
    data: InviteAthleteRequest,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Invite an athlete by email."""
    athlete_email = data.athlete_email
    result = await db.execute(select(User).where(User.email == athlete_email))
    athlete = result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if athlete.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes invitarte a ti mismo")

    # Check if relationship already exists
    existing = await db.execute(
        select(CoachAthlete).where(
            CoachAthlete.coach_id == current_user.id,
            CoachAthlete.athlete_id == athlete.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe una relación con este atleta")

    rel = CoachAthlete(
        coach_id=current_user.id,
        athlete_id=athlete.id,
        status=CoachAthleteStatus.PENDING,
        initiated_by="coach",
    )
    db.add(rel)
    await db.flush()
    return {"message": f"Invitación enviada a {athlete_email}", "status": "pending"}


@router.post("/invite/{invite_id}/accept")
async def accept_invite(
    invite_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete accepts a coach invitation."""
    result = await db.execute(
        select(CoachAthlete).where(
            CoachAthlete.id == invite_id,
            CoachAthlete.athlete_id == current_user.id,
            CoachAthlete.status == CoachAthleteStatus.PENDING,
        )
    )
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")

    rel.status = CoachAthleteStatus.ACTIVE
    await db.flush()
    return {"message": "Invitación aceptada", "status": "active"}


@router.get("/invites/pending")
async def get_pending_invites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get pending coach invitations for the current user (as athlete)."""
    result = await db.execute(
        select(CoachAthlete, User)
        .join(User, User.id == CoachAthlete.coach_id)
        .where(
            CoachAthlete.athlete_id == current_user.id,
            CoachAthlete.status == CoachAthleteStatus.PENDING,
            CoachAthlete.initiated_by == "coach",
        )
    )
    rows = result.all()
    return [
        {
            "invite_id": rel.id,
            "coach": UserResponse.model_validate(coach),
            "created_at": rel.created_at,
        }
        for rel, coach in rows
    ]


# --- List athletes ---


@router.get("/athletes", response_model=list[CoachAthleteResponse])
async def list_athletes(
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """List all athletes linked to this coach (active and pending)."""
    result = await db.execute(
        select(CoachAthlete, User)
        .join(User, CoachAthlete.athlete_id == User.id)
        .where(CoachAthlete.coach_id == current_user.id)
        .order_by(User.name)
    )
    rows = result.all()
    return [
        CoachAthleteResponse(
            id=rel.id,
            athlete_id=rel.athlete_id,
            athlete=UserResponse.model_validate(athlete),
            status=rel.status.value,
            created_at=rel.created_at,
        )
        for rel, athlete in rows
    ]


# --- View athlete data ---


@router.get("/athletes/{athlete_id}/sessions", response_model=list[SessionListResponse])
async def get_athlete_sessions(
    athlete_id: int,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """View an athlete's workout sessions."""
    await _verify_coach_athlete(db, current_user.id, athlete_id)

    query = select(WorkoutSession).where(
        WorkoutSession.user_id == athlete_id,
        WorkoutSession.finished_at.is_not(None),
    )
    if date_from:
        query = query.where(WorkoutSession.started_at >= date_from)
    if date_to:
        query = query.where(WorkoutSession.started_at <= date_to)

    query = query.order_by(WorkoutSession.started_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    sessions = result.scalars().all()

    response = []
    for session in sessions:
        sets_result = await db.execute(
            select(
                func.count(SessionSet.id),
                func.count(func.distinct(SessionSet.exercise_id)),
            ).where(SessionSet.session_id == session.id)
        )
        set_count, exercise_count = sets_result.one()
        session_data = SessionListResponse.model_validate(session)
        session_data.set_count = set_count
        session_data.exercise_count = exercise_count
        response.append(session_data)

    return response


@router.get("/athletes/{athlete_id}/stats")
async def get_athlete_stats(
    athlete_id: int,
    period: str = Query("month", description="week, month, year"),
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """View an athlete's training summary."""
    await _verify_coach_athlete(db, current_user.id, athlete_id)

    now = datetime.now(timezone.utc)
    match period:
        case "week":
            since = now - timedelta(weeks=1)
        case "month":
            since = now - timedelta(days=30)
        case "year":
            since = now - timedelta(days=365)
        case _:
            since = now - timedelta(days=30)

    sessions_count = (
        await db.execute(
            select(func.count(WorkoutSession.id)).where(
                WorkoutSession.user_id == athlete_id,
                WorkoutSession.finished_at.is_not(None),
                WorkoutSession.started_at >= since,
            )
        )
    ).scalar_one()

    total_volume = (
        await db.execute(
            select(
                func.sum(
                    func.coalesce(SessionSet.reps, 0)
                    * func.coalesce(SessionSet.weight_kg, 0)
                )
            )
            .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
            .where(
                WorkoutSession.user_id == athlete_id,
                WorkoutSession.finished_at.is_not(None),
                WorkoutSession.started_at >= since,
            )
        )
    ).scalar_one() or 0

    total_time = (
        await db.execute(
            select(func.sum(WorkoutSession.total_duration_sec)).where(
                WorkoutSession.user_id == athlete_id,
                WorkoutSession.finished_at.is_not(None),
                WorkoutSession.started_at >= since,
            )
        )
    ).scalar_one() or 0

    avg_rpe = (
        await db.execute(
            select(func.avg(WorkoutSession.rpe)).where(
                WorkoutSession.user_id == athlete_id,
                WorkoutSession.finished_at.is_not(None),
                WorkoutSession.rpe.is_not(None),
                WorkoutSession.started_at >= since,
            )
        )
    ).scalar_one()

    total_sets = (
        await db.execute(
            select(func.count(SessionSet.id))
            .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
            .where(
                WorkoutSession.user_id == athlete_id,
                WorkoutSession.finished_at.is_not(None),
                WorkoutSession.started_at >= since,
            )
        )
    ).scalar_one()

    return {
        "athlete_id": athlete_id,
        "period": period,
        "total_sessions": sessions_count,
        "total_volume_kg": round(total_volume, 2),
        "total_sets": total_sets,
        "total_time_sec": total_time,
        "avg_rpe": round(avg_rpe, 1) if avg_rpe else None,
    }


@router.get("/athletes/{athlete_id}/records", response_model=list[RecordResponse])
async def get_athlete_records(
    athlete_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """View an athlete's personal records."""
    await _verify_coach_athlete(db, current_user.id, athlete_id)

    result = await db.execute(
        select(PersonalRecord)
        .options(selectinload(PersonalRecord.exercise))
        .where(PersonalRecord.user_id == athlete_id)
        .order_by(PersonalRecord.achieved_at.desc())
    )
    return result.scalars().all()


# --- Assign templates ---


@router.post("/assign-template", status_code=status.HTTP_201_CREATED)
async def assign_template(
    data: AssignTemplateRequest,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Assign a template to an athlete (creates a copy for the athlete)."""
    template_id = data.template_id
    athlete_id = data.athlete_id
    await _verify_coach_athlete(db, current_user.id, athlete_id)

    # Load the template with blocks
    result = await db.execute(
        select(WorkoutTemplate)
        .options(selectinload(WorkoutTemplate.blocks))
        .where(
            WorkoutTemplate.id == template_id,
            WorkoutTemplate.created_by == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")

    # Create a copy for the athlete
    new_template = WorkoutTemplate(
        name=f"{template.name}",
        description=template.description,
        modality=template.modality,
        rounds=template.rounds,
        time_cap_sec=template.time_cap_sec,
        is_public=False,
        created_by=athlete_id,
        assigned_by=current_user.id,
    )
    db.add(new_template)
    await db.flush()

    for block in template.blocks:
        new_block = TemplateBlock(
            template_id=new_template.id,
            exercise_id=block.exercise_id,
            order=block.order,
            target_sets=block.target_sets,
            target_reps=block.target_reps,
            target_weight_kg=block.target_weight_kg,
            target_distance_m=block.target_distance_m,
            target_duration_sec=block.target_duration_sec,
            rest_sec=block.rest_sec,
            notes=block.notes,
        )
        db.add(new_block)

    await db.flush()

    # Reload with relationships
    result = await db.execute(
        select(WorkoutTemplate)
        .options(
            selectinload(WorkoutTemplate.blocks).selectinload(TemplateBlock.exercise)
        )
        .where(WorkoutTemplate.id == new_template.id)
    )
    return TemplateResponse.model_validate(result.scalar_one())


@router.get("/athletes/{athlete_id}/assigned-templates")
async def get_athlete_assigned_templates(
    athlete_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Get templates assigned by this coach to an athlete, with session counts."""
    await _verify_coach_athlete(db, current_user.id, athlete_id)

    result = await db.execute(
        select(WorkoutTemplate)
        .options(
            selectinload(WorkoutTemplate.blocks).selectinload(TemplateBlock.exercise)
        )
        .where(
            WorkoutTemplate.created_by == athlete_id,
            WorkoutTemplate.assigned_by == current_user.id,
        )
        .order_by(WorkoutTemplate.id.desc())
    )
    templates = result.scalars().unique().all()

    response = []
    for t in templates:
        # Count sessions using this template
        session_count_result = await db.execute(
            select(func.count(WorkoutSession.id)).where(
                WorkoutSession.user_id == athlete_id,
                WorkoutSession.template_id == t.id,
                WorkoutSession.finished_at.is_not(None),
            )
        )
        session_count = session_count_result.scalar_one()

        # Last session date
        last_session_result = await db.execute(
            select(WorkoutSession.finished_at)
            .where(
                WorkoutSession.user_id == athlete_id,
                WorkoutSession.template_id == t.id,
                WorkoutSession.finished_at.is_not(None),
            )
            .order_by(WorkoutSession.finished_at.desc())
            .limit(1)
        )
        last_session = last_session_result.scalar_one_or_none()

        response.append({
            "template": TemplateResponse.model_validate(t),
            "sessions_completed": session_count,
            "last_session_at": last_session.isoformat() if last_session else None,
        })

    return response


# --- Assign plan to athlete ---


@router.post("/assign-plan", status_code=status.HTTP_201_CREATED)
async def assign_plan(
    plan_id: int,
    athlete_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Assign (subscribe) a plan to an athlete."""
    await _verify_coach_athlete(db, current_user.id, athlete_id)

    # Verify plan belongs to coach
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.created_by == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    # Check existing subscription
    existing = await db.execute(
        select(Subscription).where(
            Subscription.plan_id == plan_id,
            Subscription.athlete_id == athlete_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="El atleta ya está suscrito a este plan")

    sub = Subscription(
        plan_id=plan_id,
        athlete_id=athlete_id,
        status=SubscriptionStatus.ACTIVE,
    )
    db.add(sub)
    await db.flush()
    return {"message": "Plan asignado correctamente", "subscription_id": sub.id}


@router.get("/athletes/{athlete_id}/plans", response_model=list[PlanListResponse])
async def get_athlete_plans(
    athlete_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Get plans assigned to an athlete by this coach."""
    await _verify_coach_athlete(db, current_user.id, athlete_id)

    result = await db.execute(
        select(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(
            Subscription.athlete_id == athlete_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Plan.created_by == current_user.id,
        )
        .order_by(Plan.id.desc())
    )
    plans = result.scalars().all()

    response = []
    for plan in plans:
        count_result = await db.execute(
            select(func.count(PlanSession.id)).where(PlanSession.plan_id == plan.id)
        )
        session_count = count_result.scalar_one()
        data = PlanListResponse.model_validate(plan)
        data.session_count = session_count
        response.append(data)

    return response
