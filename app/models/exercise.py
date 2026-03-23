import enum

from sqlalchemy import ARRAY, Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ExerciseType(str, enum.Enum):
    STRENGTH = "strength"
    CARDIO = "cardio"
    GYMNASTICS = "gymnastics"
    OLYMPIC = "olympic"
    OTHER = "other"


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    type: Mapped[ExerciseType] = mapped_column(Enum(ExerciseType))
    muscle_groups: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    equipment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Relationships
    created_by_user: Mapped["User | None"] = relationship(  # noqa: F821
        back_populates="created_exercises"
    )

    def __repr__(self) -> str:
        return f"<Exercise {self.name}>"
