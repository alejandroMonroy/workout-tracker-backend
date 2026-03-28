import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlanType(str, enum.Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"
    TICKETS = "tickets"


class MembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    ATTENDED = "attended"
    NO_SHOW = "no_show"


class GymClassBlockType(str, enum.Enum):
    CRONOMETRO = "cronometro"
    AMRAP = "amrap"
    EMOM = "emom"
    FOR_TIME = "for_time"
    TABATA = "tabata"


class GymClassLiveStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    FINISHED = "finished"


class Gym(Base):
    __tablename__ = "gyms"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cancellation_hours: Mapped[int] = mapped_column(Integer, default=2)
    free_trial_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])  # noqa: F821
    locations: Mapped[list["GymLocation"]] = relationship(
        back_populates="gym", cascade="all, delete-orphan"
    )
    plans: Mapped[list["GymSubscriptionPlan"]] = relationship(
        back_populates="gym", cascade="all, delete-orphan"
    )
    class_templates: Mapped[list["GymClassTemplate"]] = relationship(
        back_populates="gym", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["GymMembership"]] = relationship(
        back_populates="gym", cascade="all, delete-orphan"
    )
    weekly_slots: Mapped[list["GymWeeklySlot"]] = relationship(
        back_populates="gym", cascade="all, delete-orphan"
    )
    class_workouts: Mapped[list["GymClassWorkout"]] = relationship(
        back_populates="gym", cascade="all, delete-orphan"
    )


class GymLocation(Base):
    __tablename__ = "gym_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150))
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=20)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    gym: Mapped["Gym"] = relationship(back_populates="locations")
    schedules: Mapped[list["GymClassSchedule"]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )


class GymSubscriptionPlan(Base):
    __tablename__ = "gym_subscription_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    plan_type: Mapped[PlanType] = mapped_column(
        Enum(PlanType, values_callable=lambda x: [e.value for e in x])
    )
    xp_price: Mapped[int] = mapped_column(Integer)
    sessions_included: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ticket_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    gym: Mapped["Gym"] = relationship(back_populates="plans")
    memberships: Mapped[list["GymMembership"]] = relationship(
        back_populates="plan"
    )


class GymMembership(Base):
    __tablename__ = "gym_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("gym_subscription_plans.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, values_callable=lambda x: [e.value for e in x]),
        default=MembershipStatus.ACTIVE,
    )
    tickets_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sessions_used_this_period: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    frozen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    frozen_days_used: Mapped[int] = mapped_column(Integer, default=0)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    gym: Mapped["Gym"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821
    plan: Mapped["GymSubscriptionPlan | None"] = relationship(back_populates="memberships")


class GymClassTemplate(Base):
    __tablename__ = "gym_class_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    max_capacity: Mapped[int] = mapped_column(Integer, default=20)
    tickets_cost: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    gym: Mapped["Gym"] = relationship(back_populates="class_templates")
    schedules: Mapped[list["GymClassSchedule"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class GymClassWorkout(Base):
    """Entrenamiento reutilizable de un gimnasio (bloques + ejercicios)."""

    __tablename__ = "gym_class_workouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    gym: Mapped["Gym"] = relationship(back_populates="class_workouts")
    blocks: Mapped[list["GymClassWorkoutBlock"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan", order_by="GymClassWorkoutBlock.order"
    )


class GymClassWorkoutBlock(Base):
    """Bloque dentro de un entrenamiento (e.g. calentamiento EMOM, WOD AMRAP)."""

    __tablename__ = "gym_class_workout_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("gym_class_workouts.id", ondelete="CASCADE"))
    order: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(150))
    block_type: Mapped[GymClassBlockType] = mapped_column(
        Enum(GymClassBlockType, values_callable=lambda x: [e.value for e in x], native_enum=False)
    )
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)

    workout: Mapped["GymClassWorkout"] = relationship(back_populates="blocks")
    exercises: Mapped[list["GymClassWorkoutExercise"]] = relationship(
        back_populates="block", cascade="all, delete-orphan", order_by="GymClassWorkoutExercise.order"
    )


class GymClassWorkoutExercise(Base):
    """Ejercicio dentro de un bloque con targets opcionales."""

    __tablename__ = "gym_class_workout_exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("gym_class_workout_blocks.id", ondelete="CASCADE"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    order: Mapped[int] = mapped_column(Integer, default=0)
    target_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    block: Mapped["GymClassWorkoutBlock"] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship()  # noqa: F821


class GymClassSchedule(Base):
    """A specific occurrence of a class at a location."""

    __tablename__ = "gym_class_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("gym_class_templates.id", ondelete="CASCADE")
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("gym_locations.id", ondelete="CASCADE")
    )
    workout_id: Mapped[int | None] = mapped_column(
        ForeignKey("gym_class_workouts.id", ondelete="SET NULL"), nullable=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    override_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    live_status: Mapped[GymClassLiveStatus] = mapped_column(
        Enum(GymClassLiveStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=GymClassLiveStatus.PENDING,
        server_default="pending",
    )
    live_block_index: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    live_timer_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    live_timer_paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    template: Mapped["GymClassTemplate"] = relationship(back_populates="schedules")
    location: Mapped["GymLocation"] = relationship(back_populates="schedules")
    workout: Mapped["GymClassWorkout | None"] = relationship(foreign_keys=[workout_id])
    bookings: Mapped[list["ClassBooking"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )
    waitlist: Mapped[list["ClassWaitlist"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )

    @property
    def effective_capacity(self) -> int:
        return self.override_capacity if self.override_capacity is not None else self.template.max_capacity


class ClassBooking(Base):
    __tablename__ = "class_bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("gym_class_schedules.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    membership_id: Mapped[int | None] = mapped_column(
        ForeignKey("gym_memberships.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, values_callable=lambda x: [e.value for e in x]),
        default=BookingStatus.CONFIRMED,
    )
    tickets_used: Mapped[int] = mapped_column(Integer, default=0)
    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    schedule: Mapped["GymClassSchedule"] = relationship(back_populates="bookings")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821
    membership: Mapped["GymMembership | None"] = relationship()


class ClassWaitlist(Base):
    __tablename__ = "class_waitlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("gym_class_schedules.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    schedule: Mapped["GymClassSchedule"] = relationship(back_populates="waitlist")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821


class GymTicketWallet(Base):
    """Tickets sueltos comprados por un atleta en un gimnasio. Independientes de la membresía."""

    __tablename__ = "gym_ticket_wallets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id", ondelete="CASCADE"))
    tickets_remaining: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    gym: Mapped["Gym"] = relationship(foreign_keys=[gym_id])
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821


class GymWeeklySlot(Base):
    __tablename__ = "gym_weekly_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id", ondelete="CASCADE"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Monday … 6=Sunday
    start_time: Mapped[str] = mapped_column(String(5))  # "HH:MM"
    end_time: Mapped[str] = mapped_column(String(5))    # "HH:MM"
    name: Mapped[str] = mapped_column(String(100))
    capacity: Mapped[int] = mapped_column(Integer)
    cost: Mapped[int] = mapped_column(Integer, default=1)

    gym: Mapped["Gym"] = relationship(back_populates="weekly_slots")
