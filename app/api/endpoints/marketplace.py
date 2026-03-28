from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.gym import Gym, GymMembership, MembershipStatus
from app.models.product import GymProduct, ProductRedemption
from app.models.xp import XPReason
from app.models.user import User
from app.schemas.product import (
    GymProductCreate,
    GymProductResponse,
    GymProductUpdate,
    ProductRedemptionResult,
)
from app.services.xp import deduct_xp

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


def _to_response(p: GymProduct) -> GymProductResponse:
    return GymProductResponse(
        id=p.id,
        gym_id=p.gym_id,
        gym_name=p.gym.name,
        name=p.name,
        description=p.description,
        item_type=p.item_type.value if hasattr(p.item_type, "value") else p.item_type,
        xp_cost=p.xp_cost,
        discount_pct=float(p.discount_pct) if p.discount_pct is not None else None,
        image_url=p.image_url,
        external_url=p.external_url,
        is_active=p.is_active,
        created_at=p.created_at,
    )


_PRODUCT_OPTIONS = [selectinload(GymProduct.gym)]


# ── Public marketplace (athletes browse) ────────────────────────────────────

@router.get("", response_model=list[GymProductResponse])
async def list_marketplace_products(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active products from gyms where the current user has an active/trial membership."""
    subscribed_gym_ids = select(GymMembership.gym_id).where(
        GymMembership.user_id == current_user.id,
        GymMembership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.TRIAL]),
    )
    result = await db.execute(
        select(GymProduct)
        .options(*_PRODUCT_OPTIONS)
        .where(
            GymProduct.is_active.is_(True),
            GymProduct.gym_id.in_(subscribed_gym_ids),
        )
        .order_by(GymProduct.created_at.desc())
    )
    products = result.scalars().all()
    return [_to_response(p) for p in products]


@router.post("/{product_id}/redeem", response_model=ProductRedemptionResult)
async def redeem_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Redeem a product using XP."""
    result = await db.execute(
        select(GymProduct).options(*_PRODUCT_OPTIONS).where(GymProduct.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product.xp_cost is None:
        raise HTTPException(status_code=400, detail="Este producto no tiene costo en XP")

    try:
        await deduct_xp(
            db,
            current_user.id,
            product.xp_cost,
            XPReason.PRODUCT_REDEMPTION,
            f"Canje: {product.name}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    redemption = ProductRedemption(
        product_id=product_id,
        athlete_id=current_user.id,
        xp_spent=product.xp_cost,
    )
    db.add(redemption)

    return ProductRedemptionResult(
        message=f"¡{product.name} canjeado con éxito!",
        product_id=product_id,
        xp_spent=product.xp_cost,
        external_url=product.external_url,
    )


# ── Gym owner product management ────────────────────────────────────────────

async def _get_owner_gym(gym_id: int, user_id: int, db: AsyncSession) -> Gym:
    result = await db.execute(select(Gym).where(Gym.id == gym_id))
    gym = result.scalar_one_or_none()
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")
    if gym.owner_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este gimnasio")
    return gym


@router.get("/gym/{gym_id}/products", response_model=list[GymProductResponse])
async def list_gym_products(
    gym_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all products for a gym (owner only)."""
    await _get_owner_gym(gym_id, current_user.id, db)
    result = await db.execute(
        select(GymProduct)
        .options(*_PRODUCT_OPTIONS)
        .where(GymProduct.gym_id == gym_id)
        .order_by(GymProduct.created_at.desc())
    )
    return [_to_response(p) for p in result.scalars().all()]


@router.post(
    "/gym/{gym_id}/products",
    response_model=GymProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gym_product(
    gym_id: int,
    data: GymProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new product for a gym."""
    gym = await _get_owner_gym(gym_id, current_user.id, db)
    product = GymProduct(
        gym_id=gym_id,
        name=data.name,
        description=data.description,
        item_type=data.item_type,
        xp_cost=data.xp_cost,
        discount_pct=data.discount_pct,
        image_url=data.image_url,
        external_url=data.external_url,
        is_active=data.is_active,
    )
    db.add(product)
    await db.flush()

    result = await db.execute(
        select(GymProduct)
        .options(*_PRODUCT_OPTIONS)
        .where(GymProduct.id == product.id)
        .execution_options(populate_existing=True)
    )
    return _to_response(result.scalar_one())


@router.put("/products/{product_id}", response_model=GymProductResponse)
async def update_gym_product(
    product_id: int,
    data: GymProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a gym product (gym owner only)."""
    result = await db.execute(
        select(GymProduct).options(*_PRODUCT_OPTIONS).where(GymProduct.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product.gym.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este producto")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.flush()
    result = await db.execute(
        select(GymProduct)
        .options(*_PRODUCT_OPTIONS)
        .where(GymProduct.id == product_id)
        .execution_options(populate_existing=True)
    )
    return _to_response(result.scalar_one())


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gym_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a gym product (gym owner only)."""
    result = await db.execute(
        select(GymProduct).options(*_PRODUCT_OPTIONS).where(GymProduct.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product.gym.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este producto")
    await db.delete(product)
