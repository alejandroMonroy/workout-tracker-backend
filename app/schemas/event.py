from datetime import datetime

from pydantic import BaseModel

from app.models.event import EventStatus, EventType, RegistrationStatus


# ── Event ────────────────────────────────────────────────────────────────────


class EventCreate(BaseModel):
    name: str
    description: str | None = None
    event_date: datetime
    end_date: datetime | None = None
    location: str | None = None
    capacity: int | None = None
    image_url: str | None = None
    event_type: str = "other"
    is_public: bool = False
    center_id: int | None = None
    company_id: int | None = None


class EventUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    event_date: datetime | None = None
    end_date: datetime | None = None
    location: str | None = None
    capacity: int | None = None
    image_url: str | None = None
    event_type: str | None = None
    status: EventStatus | None = None
    is_public: bool | None = None


class EventResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    event_date: datetime
    end_date: datetime | None = None
    location: str | None = None
    capacity: int | None = None
    image_url: str | None = None
    status: EventStatus
    event_type: str = "other"
    is_public: bool
    center_id: int | None = None
    center_name: str | None = None
    company_id: int | None = None
    company_name: str | None = None
    registered_count: int = 0
    is_registered: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class EventListItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    event_date: datetime
    end_date: datetime | None = None
    location: str | None = None
    capacity: int | None = None
    image_url: str | None = None
    status: EventStatus
    event_type: str = "other"
    center_name: str | None = None
    company_name: str | None = None
    registered_count: int = 0
    is_registered: bool = False

    model_config = {"from_attributes": True}


# ── Event Collaborator ───────────────────────────────────────────────────────


class AddCollaboratorRequest(BaseModel):
    company_id: int | None = None
    center_id: int | None = None


class EventCollaboratorResponse(BaseModel):
    id: int
    event_id: int
    company_id: int | None = None
    company_name: str | None = None
    center_id: int | None = None
    center_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Event Registration ───────────────────────────────────────────────────────


class EventRegistrationResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    user_name: str = ""
    status: RegistrationStatus
    registered_at: datetime

    model_config = {"from_attributes": True}
