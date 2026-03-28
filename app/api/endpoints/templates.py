from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.exercise import Exercise
from app.models.template import TemplateBlock, WorkoutModality, WorkoutTemplate
from app.models.user import User
from app.schemas.template import TemplateCreate, TemplateResponse, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("", response_model=list[TemplateResponse])
async def list_templates(
    search: str | None = Query(None, description="Buscar por nombre"),
    modality: WorkoutModality | None = Query(None, description="Filtrar por modalidad"),
    mine_only: bool = Query(False, description="Solo mis plantillas"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(WorkoutTemplate).options(
        selectinload(WorkoutTemplate.blocks).selectinload(TemplateBlock.exercise)
    )

    if mine_only:
        query = query.where(WorkoutTemplate.created_by == current_user.id)
    else:
        query = query.where(
            or_(
                WorkoutTemplate.is_public.is_(True),
                WorkoutTemplate.created_by == current_user.id,
            )
        )

    if search:
        query = query.where(WorkoutTemplate.name.ilike(f"%{search}%"))
    if modality:
        query = query.where(WorkoutTemplate.modality == modality)

    query = query.order_by(WorkoutTemplate.id.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().unique().all()


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkoutTemplate)
        .options(
            selectinload(WorkoutTemplate.blocks).selectinload(TemplateBlock.exercise)
        )
        .where(WorkoutTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    if not template.is_public and template.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta plantilla")
    return template


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate all exercise IDs exist
    if data.blocks:
        exercise_ids = [b.exercise_id for b in data.blocks]
        result = await db.execute(
            select(Exercise.id).where(Exercise.id.in_(exercise_ids))
        )
        found_ids = set(result.scalars().all())
        missing = set(exercise_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Ejercicios no encontrados: {missing}",
            )

    template = WorkoutTemplate(
        name=data.name,
        description=data.description,
        modality=data.modality,
        rounds=data.rounds,
        time_cap_sec=data.time_cap_sec,
        is_public=data.is_public,
        created_by=current_user.id,
    )
    db.add(template)
    await db.flush()

    for block_data in data.blocks:
        block = TemplateBlock(
            template_id=template.id,
            exercise_id=block_data.exercise_id,
            order=block_data.order,
            target_sets=block_data.target_sets,
            target_reps=block_data.target_reps,
            target_weight_kg=block_data.target_weight_kg,
            target_distance_m=block_data.target_distance_m,
            target_duration_sec=block_data.target_duration_sec,
            rest_sec=block_data.rest_sec,
            notes=block_data.notes,
        )
        db.add(block)

    await db.flush()

    # Reload with relationships
    result = await db.execute(
        select(WorkoutTemplate)
        .options(
            selectinload(WorkoutTemplate.blocks).selectinload(TemplateBlock.exercise)
        )
        .where(WorkoutTemplate.id == template.id)
    )
    return result.scalar_one()


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkoutTemplate)
        .options(selectinload(WorkoutTemplate.blocks))
        .where(WorkoutTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    if template.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes editar esta plantilla")

    update_data = data.model_dump(exclude_unset=True, exclude={"blocks"})
    for field, value in update_data.items():
        setattr(template, field, value)

    # Replace blocks if provided
    if data.blocks is not None:
        # Validate exercise IDs
        exercise_ids = [b.exercise_id for b in data.blocks]
        if exercise_ids:
            res = await db.execute(
                select(Exercise.id).where(Exercise.id.in_(exercise_ids))
            )
            found_ids = set(res.scalars().all())
            missing = set(exercise_ids) - found_ids
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ejercicios no encontrados: {missing}",
                )

        # Delete old blocks
        for block in template.blocks:
            await db.delete(block)
        await db.flush()

        # Create new blocks
        for block_data in data.blocks:
            block = TemplateBlock(
                template_id=template.id,
                exercise_id=block_data.exercise_id,
                order=block_data.order,
                target_sets=block_data.target_sets,
                target_reps=block_data.target_reps,
                target_weight_kg=block_data.target_weight_kg,
                target_distance_m=block_data.target_distance_m,
                target_duration_sec=block_data.target_duration_sec,
                rest_sec=block_data.rest_sec,
                notes=block_data.notes,
            )
            db.add(block)

    await db.flush()

    # Reload with relationships — populate_existing forces a fresh load
    # from DB, bypassing any stale identity-map entries from deleted blocks.
    result = await db.execute(
        select(WorkoutTemplate)
        .options(
            selectinload(WorkoutTemplate.blocks).selectinload(TemplateBlock.exercise)
        )
        .where(WorkoutTemplate.id == template.id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkoutTemplate).where(WorkoutTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    if template.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar esta plantilla")
    await db.delete(template)
