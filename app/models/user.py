import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    ATHLETE = "athlete"
    COACH = "coach"
    ADMIN = "admin"


class UnitsPreference(str, enum.Enum):
    METRIC = "metric"
    IMPERIAL = "imperial"


class SexType(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.ATHLETE)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    units_preference: Mapped[UnitsPreference] = mapped_column(
        Enum(UnitsPreference), default=UnitsPreference.METRIC
    )
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    sex: Mapped[SexType | None] = mapped_column(
        Enum(SexType, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    total_xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    monthly_xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    level: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    current_division: Mapped[str | None] = mapped_column(
        String(20), nullable=True, server_default="bronce"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    sessions: Mapped[list["WorkoutSession"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    personal_records: Mapped[list["PersonalRecord"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    created_exercises: Mapped[list["Exercise"]] = relationship(  # noqa: F821
        back_populates="created_by_user"
    )
    created_templates: Mapped[list["WorkoutTemplate"]] = relationship(  # noqa: F821
        back_populates="created_by_user",
        foreign_keys="[WorkoutTemplate.created_by]",
    )
    created_plans: Mapped[list["Plan"]] = relationship(  # noqa: F821
        back_populates="creator",
        foreign_keys="[Plan.created_by]",
    )
    plan_enrollments: Mapped[list["PlanEnrollment"]] = relationship(  # noqa: F821
        back_populates="athlete",
        foreign_keys="[PlanEnrollment.athlete_id]",
    )
    coach_subscriptions_as_coach: Mapped[list["CoachSubscription"]] = relationship(  # noqa: F821
        foreign_keys="[CoachSubscription.coach_id]",
    )
    coach_subscriptions_as_athlete: Mapped[list["CoachSubscription"]] = relationship(  # noqa: F821
        foreign_keys="[CoachSubscription.athlete_id]",
    )
    center_subscriptions: Mapped[list["CenterSubscription"]] = relationship(  # noqa: F821
        foreign_keys="[CenterSubscription.athlete_id]",
    )
    class_bookings: Mapped[list["ClassBooking"]] = relationship(  # noqa: F821
        foreign_keys="[ClassBooking.athlete_id]",
    )
    xp_transactions: Mapped[list["XPTransaction"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
