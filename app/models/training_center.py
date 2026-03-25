import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CenterSubscriptionStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ClassStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ClassBookingStatus(str, enum.Enum):
    RESERVED = "reserved"
    ATTENDED = "attended"
    CANCELLED = "cancelled"


class CenterMemberRole(str, enum.Enum):
    MEMBER = "member"
    COACH = "coach"
    ADMIN = "admin"


class CenterMemberStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TrainingCenter(Base):
    __tablename__ = "training_centers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    monthly_xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship(  # noqa: F821
        foreign_keys=[owner_id]
    )
    memberships: Mapped[list["CenterMembership"]] = relationship(
        back_populates="center", cascade="all, delete-orphan"
    )
    published_plans: Mapped[list["CenterPlan"]] = relationship(
        back_populates="center", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["CenterSubscription"]] = relationship(
        back_populates="center", cascade="all, delete-orphan"
    )
    classes: Mapped[list["CenterClass"]] = relationship(
        back_populates="center", cascade="all, delete-orphan"
    )
    events: Mapped[list["Event"]] = relationship(  # noqa: F821
        back_populates="center"
    )

    def __repr__(self) -> str:
        return f"<TrainingCenter {self.name}>"


class CenterMembership(Base):
    __tablename__ = "center_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    center_id: Mapped[int] = mapped_column(
        ForeignKey("training_centers.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[CenterMemberRole] = mapped_column(
        Enum(CenterMemberRole, values_callable=lambda x: [e.value for e in x]),
        default=CenterMemberRole.MEMBER,
    )
    status: Mapped[CenterMemberStatus] = mapped_column(
        Enum(CenterMemberStatus, values_callable=lambda x: [e.value for e in x]),
        default=CenterMemberStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    center: Mapped["TrainingCenter"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<CenterMembership center={self.center_id} "
            f"user={self.user_id} role={self.role}>"
        )


class CenterPlan(Base):
    """Links a coach's plan to a training center so it appears in the center's catalog."""
    __tablename__ = "center_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    center_id: Mapped[int] = mapped_column(
        ForeignKey("training_centers.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), index=True
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    center: Mapped["TrainingCenter"] = relationship(back_populates="published_plans")
    plan: Mapped["Plan"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<CenterPlan center={self.center_id} plan={self.plan_id}>"


# ── CenterSubscription ─────────────────────────────────────────


class CenterSubscription(Base):
    """Monthly athlete subscription to a training center."""
    __tablename__ = "center_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    center_id: Mapped[int] = mapped_column(
        ForeignKey("training_centers.id", ondelete="CASCADE"), index=True
    )
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[CenterSubscriptionStatus] = mapped_column(
        Enum(CenterSubscriptionStatus, values_callable=lambda x: [e.value for e in x]),
        default=CenterSubscriptionStatus.PENDING,
    )
    xp_per_month: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    center: Mapped["TrainingCenter"] = relationship(back_populates="subscriptions")
    athlete: Mapped["User"] = relationship(foreign_keys=[athlete_id])  # noqa: F821

    def __repr__(self) -> str:
        return f"<CenterSubscription center={self.center_id} athlete={self.athlete_id}>"


# ── CenterClass ─────────────────────────────────────────────


class CenterClass(Base):
    """A scheduled group class at a training center."""
    __tablename__ = "center_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    center_id: Mapped[int] = mapped_column(
        ForeignKey("training_centers.id", ondelete="CASCADE"), index=True
    )
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_templates.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ClassStatus] = mapped_column(
        Enum(ClassStatus, values_callable=lambda x: [e.value for e in x]),
        default=ClassStatus.SCHEDULED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    center: Mapped["TrainingCenter"] = relationship(back_populates="classes")
    coach: Mapped["User"] = relationship(foreign_keys=[coach_id])  # noqa: F821
    bookings: Mapped[list["ClassBooking"]] = relationship(
        back_populates="center_class", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CenterClass {self.name} at={self.scheduled_at}>"


# ── ClassBooking ────────────────────────────────────────────


class ClassBooking(Base):
    """An athlete's booking for a center class."""
    __tablename__ = "class_bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(
        ForeignKey("center_classes.id", ondelete="CASCADE"), index=True
    )
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[ClassBookingStatus] = mapped_column(
        Enum(ClassBookingStatus, values_callable=lambda x: [e.value for e in x]),
        default=ClassBookingStatus.RESERVED,
    )
    booked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    center_class: Mapped["CenterClass"] = relationship(back_populates="bookings")
    athlete: Mapped["User"] = relationship(foreign_keys=[athlete_id])  # noqa: F821

    def __repr__(self) -> str:
        return f"<ClassBooking class={self.class_id} athlete={self.athlete_id}>"
