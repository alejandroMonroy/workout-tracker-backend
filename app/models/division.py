import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Division(str, enum.Enum):
    BRONCE = "bronce"
    PLATA = "plata"
    ORO = "oro"
    PLATINO = "platino"
    DIAMANTE = "diamante"
    ELITE = "elite"


DIVISION_ORDER: list[Division] = list(Division)

DIVISION_DISPLAY: dict[Division, str] = {
    Division.BRONCE: "Bronce",
    Division.PLATA: "Plata",
    Division.ORO: "Oro",
    Division.PLATINO: "Platino",
    Division.DIAMANTE: "Diamante",
    Division.ELITE: "Élite",
}

GROUP_SIZE = 20
PROMOTE_COUNT = 5
DEMOTE_COUNT = 5


def division_index(d: Division) -> int:
    return DIVISION_ORDER.index(d)


def promote_division(d: Division) -> Division:
    idx = division_index(d)
    if idx < len(DIVISION_ORDER) - 1:
        return DIVISION_ORDER[idx + 1]
    return d


def demote_division(d: Division) -> Division:
    idx = division_index(d)
    if idx > 0:
        return DIVISION_ORDER[idx - 1]
    return d


class LeagueSeason(Base):
    __tablename__ = "league_seasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, unique=True, index=True)
    week_end: Mapped[date] = mapped_column(Date)
    processed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    memberships: Mapped[list["LeagueMembership"]] = relationship(
        back_populates="season", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<LeagueSeason {self.week_start} – {self.week_end}>"


class LeagueMembership(Base):
    __tablename__ = "league_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("league_seasons.id"), index=True
    )
    division: Mapped[Division] = mapped_column(
        Enum(Division, values_callable=lambda x: [e.value for e in x])
    )
    group_number: Mapped[int] = mapped_column(Integer, default=1)
    weekly_xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    final_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    promoted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    demoted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # Relationships
    user: Mapped["User"] = relationship()  # noqa: F821
    season: Mapped["LeagueSeason"] = relationship(back_populates="memberships")

    def __repr__(self) -> str:
        return (
            f"<LeagueMembership user={self.user_id} "
            f"season={self.season_id} div={self.division}>"
        )
