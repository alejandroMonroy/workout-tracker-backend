import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


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
