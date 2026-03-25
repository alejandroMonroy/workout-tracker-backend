import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FriendshipStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    addressee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[FriendshipStatus] = mapped_column(
        Enum(FriendshipStatus, values_callable=lambda x: [e.value for e in x]),
        default=FriendshipStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    requester: Mapped["User"] = relationship(foreign_keys=[requester_id])  # noqa: F821
    addressee: Mapped["User"] = relationship(foreign_keys=[addressee_id])  # noqa: F821

    def __repr__(self) -> str:
        return f"<Friendship {self.requester_id}->{self.addressee_id} {self.status}>"
