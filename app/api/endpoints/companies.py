from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.partner_company import PartnerCompany, Product
from app.models.user import User
from app.models.xp import XPReason
from app.services.xp import deduct_xp
from app.schemas.partner_company import (
    PartnerCompanyCreate,
    PartnerCompanyListItem,
    PartnerCompanyResponse,
    PartnerCompanyUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter(prefix="/companies", tags=["Partner Companies"])


# ── helpers ──────────────────────────────────────────────────────────────────


async def _product_count(db: AsyncSession, company_id: int) -> int:
    r = await db.execute(
        select(func.count(Product.id)).where(
            Product.company_id == company_id, Product.is_active == True  # noqa: E712
        )
    )
    return r.scalar_one()


# ── CRUD companies ───────────────────────────────────────────────────────────


@router.post("", response_model=PartnerCompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    data: PartnerCompanyCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new partner company (admin only)."""
    company = PartnerCompany(**data.model_dump())
    db.add(company)
    await db.flush()

    return PartnerCompanyResponse(
        **{c.name: getattr(company, c.name) for c in company.__table__.columns},
        product_count=0,
    )


@router.get("", response_model=list[PartnerCompanyListItem])
async def list_companies(
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            PartnerCompany,
            func.count(Product.id).label("product_count"),
        )
        .outerjoin(
            Product,
            (Product.company_id == PartnerCompany.id)
            & (Product.is_active == True),  # noqa: E712
        )
        .where(PartnerCompany.is_active == True)  # noqa: E712
        .group_by(PartnerCompany.id)
        .order_by(PartnerCompany.name)
        .limit(limit)
        .offset(offset)
    )
    if q:
        query = query.where(PartnerCompany.name.ilike(f"%{q}%"))

    result = await db.execute(query)
    rows = result.all()
    return [
        PartnerCompanyListItem(
            id=co.id,
            name=co.name,
            description=co.description,
            logo_url=co.logo_url,
            product_count=cnt,
            is_active=co.is_active,
        )
        for co, cnt in rows
    ]


@router.get("/{company_id}", response_model=PartnerCompanyResponse)
async def get_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PartnerCompany).where(PartnerCompany.id == company_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    cnt = await _product_count(db, company_id)
    return PartnerCompanyResponse(
        **{c.name: getattr(company, c.name) for c in company.__table__.columns},
        product_count=cnt,
    )


@router.put("/{company_id}", response_model=PartnerCompanyResponse)
async def update_company(
    company_id: int,
    data: PartnerCompanyUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PartnerCompany).where(PartnerCompany.id == company_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    await db.flush()

    cnt = await _product_count(db, company_id)
    return PartnerCompanyResponse(
        **{c.name: getattr(company, c.name) for c in company.__table__.columns},
        product_count=cnt,
    )


# ── Products ─────────────────────────────────────────────────────────────────


@router.post("/{company_id}/products", response_model=ProductResponse, status_code=201)
async def create_product(
    company_id: int,
    data: ProductCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Verify company
    co_res = await db.execute(
        select(PartnerCompany).where(PartnerCompany.id == company_id)
    )
    company = co_res.scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    product = Product(**data.model_dump(), company_id=company_id)
    db.add(product)
    await db.flush()

    return ProductResponse(
        **{c.name: getattr(product, c.name) for c in product.__table__.columns},
        company_name=company.name,
    )


@router.get("/{company_id}/products", response_model=list[ProductResponse])
async def list_products(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product, PartnerCompany.name.label("coname"))
        .join(PartnerCompany, Product.company_id == PartnerCompany.id)
        .where(Product.company_id == company_id, Product.is_active == True)  # noqa: E712
        .order_by(Product.name)
    )
    rows = result.all()
    return [
        ProductResponse(
            **{c.name: getattr(p, c.name) for c in p.__table__.columns},
            company_name=coname,
        )
        for p, coname in rows
    ]


@router.get("/products/all", response_model=list[ProductResponse])
async def list_all_products(
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Browse all active products across all companies (the 'shop')."""
    query = (
        select(Product, PartnerCompany.name.label("coname"))
        .join(PartnerCompany, Product.company_id == PartnerCompany.id)
        .where(Product.is_active == True, PartnerCompany.is_active == True)  # noqa: E712
        .order_by(Product.name)
        .limit(limit)
        .offset(offset)
    )
    if q:
        query = query.where(Product.name.ilike(f"%{q}%"))

    result = await db.execute(query)
    rows = result.all()
    return [
        ProductResponse(
            **{c.name: getattr(p, c.name) for c in p.__table__.columns},
            company_name=coname,
        )
        for p, coname in rows
    ]


@router.post("/products/{product_id}/redeem", status_code=status.HTTP_200_OK)
async def redeem_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Redeem a product or discount using XP."""
    result = await db.execute(
        select(Product, PartnerCompany.name.label("coname"))
        .join(PartnerCompany, Product.company_id == PartnerCompany.id)
        .where(Product.id == product_id, Product.is_active == True)  # noqa: E712
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(404, "Producto no encontrado")
    product, company_name = row

    if not product.xp_cost:
        raise HTTPException(400, "Este producto no tiene precio en XP")

    try:
        await deduct_xp(
            db, current_user.id, product.xp_cost,
            XPReason.PRODUCT_REDEMPTION,
            f"Canje: {product.name} ({company_name})",
        )
    except ValueError as e:
        raise HTTPException(402, str(e))

    return {
        "message": f"Has canjeado '{product.name}' por {product.xp_cost} XP",
        "product_id": product_id,
        "xp_spent": product.xp_cost,
        "external_url": product.external_url,
    }


@router.put("/{company_id}/products/{product_id}", response_model=ProductResponse)
async def update_product(
    company_id: int,
    product_id: int,
    data: ProductUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.company_id == company_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Producto no encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.flush()

    co_res = await db.execute(
        select(PartnerCompany.name).where(PartnerCompany.id == company_id)
    )
    return ProductResponse(
        **{c.name: getattr(product, c.name) for c in product.__table__.columns},
        company_name=co_res.scalar_one(),
    )
