import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class RegistrationStatus(str, enum.Enum):
    REGISTERED = "registered"
    CANCELLED = "cancelled"
    ATTENDED = "attended"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, values_callable=lambda x: [e.value for e in x]),
        default=EventStatus.DRAFT,
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # Organizer — either a center or a company (at least one)
    center_id: Mapped[int | None] = mapped_column(
        ForeignKey("training_centers.id"), nullable=True, index=True
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("partner_companies.id"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    center: Mapped["TrainingCenter | None"] = relationship(  # noqa: F821
        back_populates="events"
    )
    company: Mapped["PartnerCompany | None"] = relationship(  # noqa: F821
        back_populates="events"
    )
    collaborators: Mapped[list["EventCollaborator"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    registrations: Mapped[list["EventRegistration"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Event {self.name}>"


class EventCollaborator(Base):
    """Companies or centers that collaborate in an event they didn't organize."""
    __tablename__ = "event_collaborators"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("partner_companies.id"), nullable=True
    )
    center_id: Mapped[int | None] = mapped_column(
        ForeignKey("training_centers.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="collaborators")
    company: Mapped["PartnerCompany | None"] = relationship(  # noqa: F821
        back_populates="collaborations"
    )
    center: Mapped["TrainingCenter | None"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<EventCollaborator event={self.event_id}>"


class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus, values_callable=lambda x: [e.value for e in x]),
        default=RegistrationStatus.REGISTERED,
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="registrations")
    user: Mapped["User"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<EventRegistration event={self.event_id} user={self.user_id}>"
