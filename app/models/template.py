import enum

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WorkoutModality(str, enum.Enum):
    AMRAP = "amrap"
    EMOM = "emom"
    FOR_TIME = "for_time"
    TABATA = "tabata"
    CUSTOM = "custom"


class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    modality: Mapped[WorkoutModality] = mapped_column(
        Enum(WorkoutModality), default=WorkoutModality.CUSTOM
    )
    rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_cap_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Relationships
    created_by_user: Mapped["User"] = relationship(  # noqa: F821
        foreign_keys=[created_by], back_populates="created_templates"
    )
    blocks: Mapped[list["TemplateBlock"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="TemplateBlock.order"
    )

    def __repr__(self) -> str:
        return f"<WorkoutTemplate {self.name}>"


class TemplateBlock(Base):
    __tablename__ = "template_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("workout_templates.id", ondelete="CASCADE"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    order: Mapped[int] = mapped_column(Integer, default=0)
    target_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    template: Mapped["WorkoutTemplate"] = relationship(back_populates="blocks")
    exercise: Mapped["Exercise"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<TemplateBlock template={self.template_id} order={self.order}>"
