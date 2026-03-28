from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GymProductCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = None
    item_type: Literal["product", "discount"] = "product"
    xp_cost: int | None = Field(None, ge=1)
    discount_pct: float | None = Field(None, ge=0, le=100)
    image_url: str | None = None
    external_url: str | None = None
    is_active: bool = True


class GymProductUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    item_type: Literal["product", "discount"] | None = None
    xp_cost: int | None = Field(None, ge=1)
    discount_pct: float | None = Field(None, ge=0, le=100)
    image_url: str | None = None
    external_url: str | None = None
    is_active: bool | None = None


class GymProductResponse(BaseModel):
    id: int
    gym_id: int
    gym_name: str
    name: str
    description: str | None
    item_type: str
    xp_cost: int | None
    discount_pct: float | None
    image_url: str | None
    external_url: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductRedemptionResult(BaseModel):
    message: str
    product_id: int
    xp_spent: int
    external_url: str | None
