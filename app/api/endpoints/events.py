from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.xp import XPReason
from app.services.xp import deduct_xp
from app.models.event import (
    Event,
    EventCollaborator,
    EventRegistration,
    EventStatus,
    RegistrationStatus,
)
from app.models.partner_company import PartnerCompany
from app.models.training_center import CenterMemberStatus, CenterMembership, TrainingCenter
from app.models.user import User
from app.schemas.event import (
    AddCollaboratorRequest,
    EventCollaboratorResponse,
    EventCreate,
    EventListItem,
    EventRegistrationResponse,
    EventResponse,
    EventUpdate,
)

router = APIRouter(prefix="/events", tags=["Events"])


# ── helpers ──────────────────────────────────────────────────────────────────


async def _enrich_event(db: AsyncSession, event: Event, user_id: int) -> dict:
    """Build response dict with center/company names, counts, registration."""
    center_name = None
    if event.center_id:
        r = await db.execute(
            select(TrainingCenter.name).where(TrainingCenter.id == event.center_id)
        )
        center_name = r.scalar_one_or_none()

    company_name = None
    if event.company_id:
        r = await db.execute(
            select(PartnerCompany.name).where(PartnerCompany.id == event.company_id)
        )
        company_name = r.scalar_one_or_none()

    reg_count_res = await db.execute(
        select(func.count(EventRegistration.id)).where(
            EventRegistration.event_id == event.id,
            EventRegistration.status != RegistrationStatus.CANCELLED,
        )
    )
    registered_count = reg_count_res.scalar_one()

    is_registered_res = await db.execute(
        select(EventRegistration.id).where(
            EventRegistration.event_id == event.id,
            EventRegistration.user_id == user_id,
            EventRegistration.status != RegistrationStatus.CANCELLED,
        )
    )
    is_registered = is_registered_res.scalar_one_or_none() is not None

    return {
        **{c.name: getattr(event, c.name) for c in event.__table__.columns},
        "center_name": center_name,
        "company_name": company_name,
        "registered_count": registered_count,
        "is_registered": is_registered,
        "xp_cost": event.xp_cost,
    }


# ── CRUD events ──────────────────────────────────────────────────────────────


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if not data.center_id and not data.company_id:
        raise HTTPException(400, "Un evento debe tener un centro o empresa organizadora")

    event = Event(**data.model_dump())
    db.add(event)
    await db.flush()

    enriched = await _enrich_event(db, event, current_user.id)
    return EventResponse(**enriched)


@router.get("", response_model=list[EventListItem])
async def list_events(
    center_id: int | None = Query(None),
    company_id: int | None = Query(None),
    status_filter: EventStatus | None = Query(None, alias="status"),
    event_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Event).order_by(Event.event_date.desc()).limit(limit).offset(offset)

    if center_id:
        query = query.where(Event.center_id == center_id)
    if company_id:
        query = query.where(Event.company_id == company_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
    if date_from:
        query = query.where(Event.event_date >= date_from)
    if date_to:
        query = query.where(Event.event_date <= date_to)
    if status_filter:
        query = query.where(Event.status == status_filter)
    else:
        query = query.where(Event.status != EventStatus.DRAFT)

    result = await db.execute(query)
    events = result.scalars().all()

    items = []
    for ev in events:
        enriched = await _enrich_event(db, ev, current_user.id)
        items.append(
            EventListItem(
                id=ev.id,
                name=ev.name,
                description=ev.description,
                event_date=ev.event_date,
                end_date=ev.end_date,
                location=ev.location,
                capacity=ev.capacity,
                image_url=ev.image_url,
                status=ev.status,
                event_type=ev.event_type,
                center_name=enriched["center_name"],
                company_name=enriched["company_name"],
                registered_count=enriched["registered_count"],
                is_registered=enriched["is_registered"],
            )
        )
    return items


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Evento no encontrado")

    enriched = await _enrich_event(db, event, current_user.id)
    return EventResponse(**enriched)


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    data: EventUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Evento no encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    await db.flush()

    enriched = await _enrich_event(db, event, current_user.id)
    return EventResponse(**enriched)


# ── Registration ─────────────────────────────────────────────────────────────


@router.post("/{event_id}/register", response_model=EventRegistrationResponse, status_code=201)
async def register_for_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Evento no encontrado")
    if event.status not in (EventStatus.PUBLISHED,):
        raise HTTPException(400, "No se pueden inscribir en este evento")

    # Check capacity
    if event.capacity:
        cnt_res = await db.execute(
            select(func.count(EventRegistration.id)).where(
                EventRegistration.event_id == event_id,
                EventRegistration.status != RegistrationStatus.CANCELLED,
            )
        )
        if cnt_res.scalar_one() >= event.capacity:
            raise HTTPException(400, "Evento completo")

    # Check not already registered
    existing = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == current_user.id,
            EventRegistration.status != RegistrationStatus.CANCELLED,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Ya estás inscrito en este evento")

    # If center event, check membership
    if event.center_id and not event.is_public:
        mem_res = await db.execute(
            select(CenterMembership).where(
                CenterMembership.center_id == event.center_id,
                CenterMembership.user_id == current_user.id,
                CenterMembership.status == CenterMemberStatus.ACTIVE,
            )
        )
        if not mem_res.scalar_one_or_none():
            raise HTTPException(403, "Debes ser miembro del centro para inscribirte")

    # Charge XP if event has a cost
    if event.xp_cost:
        try:
            await deduct_xp(
                db, current_user.id, event.xp_cost,
                XPReason.EVENT_REGISTRATION,
                f"Inscripción: {event.name}",
            )
        except ValueError as e:
            raise HTTPException(402, str(e))

    reg = EventRegistration(
        event_id=event_id,
        user_id=current_user.id,
    )
    db.add(reg)
    await db.flush()

    return EventRegistrationResponse(
        id=reg.id,
        event_id=event_id,
        user_id=current_user.id,
        user_name=current_user.name,
        status=reg.status,
        registered_at=reg.registered_at,
    )


@router.delete("/{event_id}/register", status_code=204)
async def cancel_registration(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == current_user.id,
            EventRegistration.status == RegistrationStatus.REGISTERED,
        )
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(404, "No estás inscrito en este evento")

    reg.status = RegistrationStatus.CANCELLED
    await db.flush()


@router.get("/{event_id}/registrations", response_model=list[EventRegistrationResponse])
async def list_registrations(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EventRegistration, User.name.label("uname"))
        .join(User, EventRegistration.user_id == User.id)
        .where(EventRegistration.event_id == event_id)
        .order_by(EventRegistration.registered_at)
    )
    rows = result.all()
    return [
        EventRegistrationResponse(
            id=r.id,
            event_id=r.event_id,
            user_id=r.user_id,
            user_name=uname,
            status=r.status,
            registered_at=r.registered_at,
        )
        for r, uname in rows
    ]


# ── Collaborators ────────────────────────────────────────────────────────────


@router.post("/{event_id}/collaborators", response_model=EventCollaboratorResponse, status_code=201)
async def add_collaborator(
    event_id: int,
    data: AddCollaboratorRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if not data.company_id and not data.center_id:
        raise HTTPException(400, "Debes especificar una empresa o centro colaborador")

    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Evento no encontrado")

    collab = EventCollaborator(
        event_id=event_id,
        company_id=data.company_id,
        center_id=data.center_id,
    )
    db.add(collab)
    await db.flush()

    company_name = None
    if collab.company_id:
        r = await db.execute(select(PartnerCompany.name).where(PartnerCompany.id == collab.company_id))
        company_name = r.scalar_one_or_none()
    center_name = None
    if collab.center_id:
        r = await db.execute(select(TrainingCenter.name).where(TrainingCenter.id == collab.center_id))
        center_name = r.scalar_one_or_none()

    return EventCollaboratorResponse(
        id=collab.id,
        event_id=event_id,
        company_id=collab.company_id,
        company_name=company_name,
        center_id=collab.center_id,
        center_name=center_name,
        created_at=collab.created_at,
    )


@router.get("/{event_id}/collaborators", response_model=list[EventCollaboratorResponse])
async def list_collaborators(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EventCollaborator).where(EventCollaborator.event_id == event_id)
    )
    collabs = result.scalars().all()

    items = []
    for c in collabs:
        company_name = None
        if c.company_id:
            r = await db.execute(select(PartnerCompany.name).where(PartnerCompany.id == c.company_id))
            company_name = r.scalar_one_or_none()
        center_name = None
        if c.center_id:
            r = await db.execute(select(TrainingCenter.name).where(TrainingCenter.id == c.center_id))
            center_name = r.scalar_one_or_none()

        items.append(
            EventCollaboratorResponse(
                id=c.id,
                event_id=c.event_id,
                company_id=c.company_id,
                company_name=company_name,
                center_id=c.center_id,
                center_name=center_name,
                created_at=c.created_at,
            )
        )
    return items


# ── My Calendar (user's registered events) ──────────────────────────────────


@router.get("/my/calendar", response_model=list[EventListItem])
async def my_calendar(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return events the current user is registered for, optionally filtered by date range."""
    query = (
        select(Event)
        .join(
            EventRegistration,
            (EventRegistration.event_id == Event.id)
            & (EventRegistration.user_id == current_user.id)
            & (EventRegistration.status != RegistrationStatus.CANCELLED),
        )
        .where(Event.status != EventStatus.DRAFT)
        .order_by(Event.event_date)
    )
    if date_from:
        query = query.where(Event.event_date >= date_from)
    if date_to:
        query = query.where(Event.event_date <= date_to)

    result = await db.execute(query)
    events = result.scalars().all()

    items = []
    for ev in events:
        enriched = await _enrich_event(db, ev, current_user.id)
        items.append(
            EventListItem(
                id=ev.id,
                name=ev.name,
                description=ev.description,
                event_date=ev.event_date,
                end_date=ev.end_date,
                location=ev.location,
                capacity=ev.capacity,
                image_url=ev.image_url,
                status=ev.status,
                event_type=ev.event_type,
                center_name=enriched["center_name"],
                company_name=enriched["company_name"],
                registered_count=enriched["registered_count"],
                is_registered=enriched["is_registered"],
            )
        )
    return items
