import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompetitionResultStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"


# Junction table: which places a workout is held at
competition_workout_places = Table(
    "competition_workout_places",
    Base.metadata,
    Column(
        "competition_workout_id",
        Integer,
        ForeignKey("competition_workouts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "competition_place_id",
        Integer,
        ForeignKey("competition_places.id", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("competition_workout_id", "competition_place_id"),
)


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    location: Mapped[str] = mapped_column(String(300))
    init_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    inscription_xp_cost: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    creator: Mapped["User"] = relationship(foreign_keys=[created_by])  # noqa: F821
    places: Mapped[list["CompetitionPlace"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan", order_by="CompetitionPlace.name"
    )
    workouts: Mapped[list["CompetitionWorkout"]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
        order_by="CompetitionWorkout.order",
    )
    subscriptions: Mapped[list["CompetitionSubscription"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )


class CompetitionPlace(Base):
    __tablename__ = "competition_places"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))

    competition: Mapped["Competition"] = relationship(back_populates="places")


class CompetitionWorkout(Base):
    __tablename__ = "competition_workouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE")
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("workout_templates.id", ondelete="CASCADE")
    )
    init_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    order: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    competition: Mapped["Competition"] = relationship(back_populates="workouts")
    template: Mapped["WorkoutTemplate"] = relationship()  # noqa: F821
    places: Mapped[list["CompetitionPlace"]] = relationship(
        secondary=competition_workout_places
    )
    results: Mapped[list["CompetitionResult"]] = relationship(
        back_populates="competition_workout", cascade="all, delete-orphan"
    )


class CompetitionSubscription(Base):
    __tablename__ = "competition_subscriptions"
    __table_args__ = (UniqueConstraint("competition_id", "athlete_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE")
    )
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    competition: Mapped["Competition"] = relationship(back_populates="subscriptions")


class CompetitionResult(Base):
    __tablename__ = "competition_results"
    __table_args__ = (UniqueConstraint("competition_workout_id", "athlete_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_workout_id: Mapped[int] = mapped_column(
        ForeignKey("competition_workouts.id", ondelete="CASCADE")
    )
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id"))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[CompetitionResultStatus] = mapped_column(
        Enum(CompetitionResultStatus, values_callable=lambda x: [e.value for e in x]),
        default=CompetitionResultStatus.PENDING,
    )
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)

    competition_workout: Mapped["CompetitionWorkout"] = relationship(
        back_populates="results"
    )
    athlete: Mapped["User"] = relationship(foreign_keys=[athlete_id])  # noqa: F821
