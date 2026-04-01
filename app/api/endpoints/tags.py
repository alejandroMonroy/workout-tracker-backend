from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.plan import PlanTag
from app.models.user import User
from app.schemas.plan import TagCreate, TagResponse

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("", response_model=list[TagResponse])
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlanTag).where(PlanTag.created_by == current_user.id).order_by(PlanTag.name)
    )
    return result.scalars().all()


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tag = PlanTag(name=data.name.strip(), color=data.color, created_by=current_user.id)
    db.add(tag)
    await db.flush()
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PlanTag).where(PlanTag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    if tag.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar este tag")
    await db.delete(tag)
