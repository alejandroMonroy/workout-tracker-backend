from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_coach
from app.models.xp import XPReason
from app.services.xp import deduct_xp
from app.models.coach_subscription import CoachSubscription, CoachSubscriptionStatus
from app.models.exercise import Exercise
from app.models.plan import Plan, PlanEnrollment, PlanEnrollmentStatus, PlanSession
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
    CoachSubscriptionResponse,
    CoachProfileResponse,
    CoachRequestResponse,
    InviteAthleteRequest,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/coach", tags=["Coach"])


# --- Helper ---

async def _verify_active_subscription(
    db: AsyncSession, coach_id: int, athlete_id: int
) -> CoachSubscription:
    """Verify an active coach subscription exists."""
    result = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.coach_id == coach_id,
            CoachSubscription.athlete_id == athlete_id,
            CoachSubscription.status == CoachSubscriptionStatus.ACTIVE,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=403,
            detail="No tienes una suscripción activa con este atleta",
        )
    return sub


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
        athlete_count_result = await db.execute(
            select(func.count(CoachSubscription.id)).where(
                CoachSubscription.coach_id == coach.id,
                CoachSubscription.status == CoachSubscriptionStatus.ACTIVE,
            )
        )
        athlete_count = athlete_count_result.scalar_one()

        plan_count_result = await db.execute(
            select(func.count(Plan.id)).where(
                Plan.created_by == coach.id,
                Plan.is_public.is_(True),
            )
        )
        plan_count = plan_count_result.scalar_one()

        sub_result = await db.execute(
            select(CoachSubscription).where(
                CoachSubscription.coach_id == coach.id,
                CoachSubscription.athlete_id == current_user.id,
            )
        )
        sub = sub_result.scalar_one_or_none()

        response.append(
            CoachProfileResponse(
                id=coach.id,
                name=coach.name,
                email=coach.email,
                avatar_url=coach.avatar_url,
                athlete_count=athlete_count,
                plan_count=plan_count,
                xp_per_month=coach.monthly_xp,
                subscription_status=sub.status.value if sub else None,
                subscription_initiated_by=sub.initiated_by if sub else None,
            )
        )
    return response


@router.post("/request/{coach_id}", status_code=status.HTTP_201_CREATED)
async def request_coach(
    coach_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete sends a subscription request to a coach."""
    result = await db.execute(
        select(User).where(User.id == coach_id, User.role == UserRole.COACH)
    )
    coach = result.scalar_one_or_none()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach no encontrado")
    if coach.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes suscribirte a ti mismo")

    existing = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.coach_id == coach_id,
            CoachSubscription.athlete_id == current_user.id,
            CoachSubscription.status.in_([
                CoachSubscriptionStatus.PENDING,
                CoachSubscriptionStatus.ACTIVE,
            ]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya tienes una suscripción activa o pendiente con este coach")

    sub = CoachSubscription(
        coach_id=coach_id,
        athlete_id=current_user.id,
        status=CoachSubscriptionStatus.PENDING,
        initiated_by="athlete",
        xp_per_month=coach.monthly_xp,
    )
    db.add(sub)
    await db.flush()
    return {"message": f"Solicitud enviada a {coach.name}", "status": "pending"}


@router.get("/requests/pending", response_model=list[CoachRequestResponse])
async def get_pending_requests(
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Coach views pending athlete subscription requests."""
    result = await db.execute(
        select(CoachSubscription, User)
        .join(User, User.id == CoachSubscription.athlete_id)
        .where(
            CoachSubscription.coach_id == current_user.id,
            CoachSubscription.status == CoachSubscriptionStatus.PENDING,
            CoachSubscription.initiated_by == "athlete",
        )
        .order_by(CoachSubscription.created_at.desc())
    )
    rows = result.all()
    return [
        CoachRequestResponse(
            id=sub.id,
            athlete=UserResponse.model_validate(athlete),
            xp_per_month=sub.xp_per_month,
            created_at=sub.created_at,
        )
        for sub, athlete in rows
    ]


@router.post("/requests/{request_id}/accept")
async def accept_athlete_request(
    request_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Coach accepts an athlete's subscription request."""
    result = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.id == request_id,
            CoachSubscription.coach_id == current_user.id,
            CoachSubscription.status == CoachSubscriptionStatus.PENDING,
            CoachSubscription.initiated_by == "athlete",
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if sub.xp_per_month > 0:
        try:
            await deduct_xp(
                db, sub.athlete_id, sub.xp_per_month,
                XPReason.SUBSCRIPTION_PAYMENT,
                f"Suscripción mensual: coach {current_user.name}",
            )
        except ValueError as e:
            raise HTTPException(status_code=402, detail=str(e))

    now = datetime.now(timezone.utc)
    sub.status = CoachSubscriptionStatus.ACTIVE
    sub.started_at = now
    sub.expires_at = now + timedelta(days=30)
    await db.flush()
    return {"message": "Solicitud aceptada", "status": "active"}


@router.post("/requests/{request_id}/reject")
async def reject_athlete_request(
    request_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Coach rejects an athlete's subscription request."""
    result = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.id == request_id,
            CoachSubscription.coach_id == current_user.id,
            CoachSubscription.status == CoachSubscriptionStatus.PENDING,
            CoachSubscription.initiated_by == "athlete",
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    await db.delete(sub)
    await db.flush()
    return {"message": "Solicitud rechazada"}


@router.post("/invite", status_code=status.HTTP_201_CREATED)
async def invite_athlete(
    data: InviteAthleteRequest,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Coach invites an athlete by email."""
    result = await db.execute(select(User).where(User.email == data.athlete_email))
    athlete = result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if athlete.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes invitarte a ti mismo")

    existing = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.coach_id == current_user.id,
            CoachSubscription.athlete_id == athlete.id,
            CoachSubscription.status.in_([
                CoachSubscriptionStatus.PENDING,
                CoachSubscriptionStatus.ACTIVE,
            ]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe una suscripción activa o pendiente con este atleta")

    sub = CoachSubscription(
        coach_id=current_user.id,
        athlete_id=athlete.id,
        status=CoachSubscriptionStatus.PENDING,
        initiated_by="coach",
    )
    db.add(sub)
    await db.flush()
    return {"message": f"Invitación enviada a {data.athlete_email}", "status": "pending"}


@router.post("/invite/{invite_id}/accept")
async def accept_invite(
    invite_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athlete accepts a coach invitation."""
    result = await db.execute(
        select(CoachSubscription).where(
            CoachSubscription.id == invite_id,
            CoachSubscription.athlete_id == current_user.id,
            CoachSubscription.status == CoachSubscriptionStatus.PENDING,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")

    if sub.xp_per_month > 0:
        coach_res = await db.execute(select(User.name).where(User.id == sub.coach_id))
        coach_name = coach_res.scalar_one()
        try:
            await deduct_xp(
                db, current_user.id, sub.xp_per_month,
                XPReason.SUBSCRIPTION_PAYMENT,
                f"Suscripción mensual: coach {coach_name}",
            )
        except ValueError as e:
            raise HTTPException(status_code=402, detail=str(e))

    now = datetime.now(timezone.utc)
    sub.status = CoachSubscriptionStatus.ACTIVE
    sub.started_at = now
    sub.expires_at = now + timedelta(days=30)
    await db.flush()
    return {"message": "Invitación aceptada", "status": "active"}


@router.get("/invites/pending")
async def get_pending_invites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get pending coach invitations for the current user (as athlete)."""
    result = await db.execute(
        select(CoachSubscription, User)
        .join(User, User.id == CoachSubscription.coach_id)
        .where(
            CoachSubscription.athlete_id == current_user.id,
            CoachSubscription.status == CoachSubscriptionStatus.PENDING,
            CoachSubscription.initiated_by == "coach",
        )
    )
    rows = result.all()
    return [
        {
            "invite_id": sub.id,
            "coach": UserResponse.model_validate(coach),
            "xp_per_month": sub.xp_per_month,
            "created_at": sub.created_at,
        }
        for sub, coach in rows
    ]


@router.get("/athletes", response_model=list[CoachSubscriptionResponse])
async def list_athletes(
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """List all athletes with active/pending subscriptions to this coach."""
    result = await db.execute(
        select(CoachSubscription, User)
        .join(User, CoachSubscription.athlete_id == User.id)
        .where(CoachSubscription.coach_id == current_user.id)
        .order_by(User.name)
    )
    rows = result.all()
    return [
        CoachSubscriptionResponse(
            id=sub.id,
            athlete_id=sub.athlete_id,
            athlete=UserResponse.model_validate(athlete),
            status=sub.status.value,
            xp_per_month=sub.xp_per_month,
            started_at=sub.started_at,
            expires_at=sub.expires_at,
            created_at=sub.created_at,
        )
        for sub, athlete in rows
    ]


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
    await _verify_active_subscription(db, current_user.id, athlete_id)

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
    await _verify_active_subscription(db, current_user.id, athlete_id)

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

    sessions_count = (await db.execute(
        select(func.count(WorkoutSession.id)).where(
            WorkoutSession.user_id == athlete_id,
            WorkoutSession.finished_at.is_not(None),
            WorkoutSession.started_at >= since,
        )
    )).scalar_one()

    total_volume = (await db.execute(
        select(func.sum(func.coalesce(SessionSet.reps, 0) * func.coalesce(SessionSet.weight_kg, 0)))
        .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
        .where(
            WorkoutSession.user_id == athlete_id,
            WorkoutSession.finished_at.is_not(None),
            WorkoutSession.started_at >= since,
        )
    )).scalar_one() or 0

    total_time = (await db.execute(
        select(func.sum(WorkoutSession.total_duration_sec)).where(
            WorkoutSession.user_id == athlete_id,
            WorkoutSession.finished_at.is_not(None),
            WorkoutSession.started_at >= since,
        )
    )).scalar_one() or 0

    avg_rpe = (await db.execute(
        select(func.avg(WorkoutSession.rpe)).where(
            WorkoutSession.user_id == athlete_id,
            WorkoutSession.finished_at.is_not(None),
            WorkoutSession.rpe.is_not(None),
            WorkoutSession.started_at >= since,
        )
    )).scalar_one()

    total_sets = (await db.execute(
        select(func.count(SessionSet.id))
        .join(WorkoutSession, WorkoutSession.id == SessionSet.session_id)
        .where(
            WorkoutSession.user_id == athlete_id,
            WorkoutSession.finished_at.is_not(None),
            WorkoutSession.started_at >= since,
        )
    )).scalar_one()

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
    await _verify_active_subscription(db, current_user.id, athlete_id)

    result = await db.execute(
        select(PersonalRecord)
        .options(selectinload(PersonalRecord.exercise))
        .where(PersonalRecord.user_id == athlete_id)
        .order_by(PersonalRecord.achieved_at.desc())
    )
    return result.scalars().all()


@router.post("/assign-template", status_code=status.HTTP_201_CREATED)
async def assign_template(
    data: AssignTemplateRequest,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Assign a template to an athlete (creates a copy)."""
    await _verify_active_subscription(db, current_user.id, data.athlete_id)

    result = await db.execute(
        select(WorkoutTemplate)
        .options(selectinload(WorkoutTemplate.blocks))
        .where(
            WorkoutTemplate.id == data.template_id,
            WorkoutTemplate.created_by == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")

    new_template = WorkoutTemplate(
        name=template.name,
        description=template.description,
        modality=template.modality,
        rounds=template.rounds,
        time_cap_sec=template.time_cap_sec,
        is_public=False,
        created_by=data.athlete_id,
        assigned_by=current_user.id,
    )
    db.add(new_template)
    await db.flush()

    for block in template.blocks:
        db.add(TemplateBlock(
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
        ))

    await db.flush()

    result = await db.execute(
        select(WorkoutTemplate)
        .options(selectinload(WorkoutTemplate.blocks).selectinload(TemplateBlock.exercise))
        .where(WorkoutTemplate.id == new_template.id)
    )
    return TemplateResponse.model_validate(result.scalar_one())


@router.get("/athletes/{athlete_id}/assigned-templates")
async def get_athlete_assigned_templates(
    athlete_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Get templates assigned by this coach to an athlete."""
    await _verify_active_subscription(db, current_user.id, athlete_id)

    result = await db.execute(
        select(WorkoutTemplate)
        .options(selectinload(WorkoutTemplate.blocks).selectinload(TemplateBlock.exercise))
        .where(
            WorkoutTemplate.created_by == athlete_id,
            WorkoutTemplate.assigned_by == current_user.id,
        )
        .order_by(WorkoutTemplate.id.desc())
    )
    templates = result.scalars().unique().all()

    response = []
    for t in templates:
        session_count = (await db.execute(
            select(func.count(WorkoutSession.id)).where(
                WorkoutSession.user_id == athlete_id,
                WorkoutSession.template_id == t.id,
                WorkoutSession.finished_at.is_not(None),
            )
        )).scalar_one()

        last_session = (await db.execute(
            select(WorkoutSession.finished_at)
            .where(
                WorkoutSession.user_id == athlete_id,
                WorkoutSession.template_id == t.id,
                WorkoutSession.finished_at.is_not(None),
            )
            .order_by(WorkoutSession.finished_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        response.append({
            "template": TemplateResponse.model_validate(t),
            "sessions_completed": session_count,
            "last_session_at": last_session.isoformat() if last_session else None,
        })

    return response


@router.post("/assign-plan", status_code=status.HTTP_201_CREATED)
async def assign_plan(
    plan_id: int,
    athlete_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Assign (enroll) a plan to an athlete."""
    sub = await _verify_active_subscription(db, current_user.id, athlete_id)

    result = await db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.created_by == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    existing = await db.execute(
        select(PlanEnrollment).where(
            PlanEnrollment.plan_id == plan_id,
            PlanEnrollment.athlete_id == athlete_id,
            PlanEnrollment.status == PlanEnrollmentStatus.ACTIVE,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="El atleta ya está inscrito en este plan")

    enrollment = PlanEnrollment(
        plan_id=plan_id,
        athlete_id=athlete_id,
        coach_subscription_id=sub.id,
        assigned_by_coach=True,
        status=PlanEnrollmentStatus.ACTIVE,
    )
    db.add(enrollment)
    await db.flush()
    return {"message": "Plan asignado correctamente", "enrollment_id": enrollment.id}


@router.get("/athletes/{athlete_id}/plans", response_model=list[PlanListResponse])
async def get_athlete_plans(
    athlete_id: int,
    current_user: User = Depends(require_coach),
    db: AsyncSession = Depends(get_db),
):
    """Get plans enrolled by an athlete from this coach."""
    await _verify_active_subscription(db, current_user.id, athlete_id)

    result = await db.execute(
        select(Plan)
        .join(PlanEnrollment, PlanEnrollment.plan_id == Plan.id)
        .where(
            PlanEnrollment.athlete_id == athlete_id,
            PlanEnrollment.status == PlanEnrollmentStatus.ACTIVE,
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
        data = PlanListResponse.model_validate(plan)
        data.session_count = count_result.scalar_one()
        response.append(data)

    return response
