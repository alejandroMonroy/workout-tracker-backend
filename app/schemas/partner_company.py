from datetime import datetime

from pydantic import BaseModel


# ── Partner Company ──────────────────────────────────────────────────────────


class PartnerCompanyCreate(BaseModel):
    name: str
    description: str | None = None
    logo_url: str | None = None
    website: str | None = None
    contact_email: str | None = None


class PartnerCompanyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    logo_url: str | None = None
    website: str | None = None
    contact_email: str | None = None


class PartnerCompanyResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    logo_url: str | None = None
    website: str | None = None
    contact_email: str | None = None
    is_active: bool
    product_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PartnerCompanyListItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    logo_url: str | None = None
    product_count: int = 0
    is_active: bool

    model_config = {"from_attributes": True}


# ── Product ──────────────────────────────────────────────────────────────────


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: float | None = None
    currency: str = "EUR"
    image_url: str | None = None
    external_url: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    currency: str | None = None
    image_url: str | None = None
    external_url: str | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: int
    company_id: int
    company_name: str = ""
    name: str
    description: str | None = None
    price: float | None = None
    currency: str
    image_url: str | None = None
    external_url: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
