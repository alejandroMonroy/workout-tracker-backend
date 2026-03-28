import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProductItemType(str, enum.Enum):
    PRODUCT = "product"
    DISCOUNT = "discount"


class GymProduct(Base):
    __tablename__ = "gym_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gyms.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_type: Mapped[ProductItemType] = mapped_column(
        Enum(ProductItemType, values_callable=lambda obj: [e.value for e in obj]),
        default=ProductItemType.PRODUCT,
    )
    xp_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    gym: Mapped["Gym"] = relationship("Gym")  # type: ignore[name-defined]


class ProductRedemption(Base):
    __tablename__ = "product_redemptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("gym_products.id", ondelete="CASCADE"), index=True
    )
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    xp_spent: Mapped[int] = mapped_column(Integer)
    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
