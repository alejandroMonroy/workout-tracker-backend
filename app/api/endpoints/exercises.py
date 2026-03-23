from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.exercise import Exercise, ExerciseType
from app.models.user import User
from app.schemas.exercise import ExerciseCreate, ExerciseResponse, ExerciseUpdate

router = APIRouter(prefix="/exercises", tags=["Exercises"])


@router.get("", response_model=list[ExerciseResponse])
async def list_exercises(
    response: Response,
    search: str | None = Query(None, description="Buscar por nombre"),
    type: ExerciseType | None = Query(None, description="Filtrar por tipo"),
    muscle_group: str | None = Query(None, description="Filtrar por grupo muscular"),
    equipment: str | None = Query(None, description="Filtrar por equipamiento"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_filter = or_(Exercise.is_global.is_(True), Exercise.created_by == current_user.id)
    query = select(Exercise).where(base_filter)
    count_query = select(func.count(Exercise.id)).where(base_filter)

    if search:
        query = query.where(Exercise.name.ilike(f"%{search}%"))
        count_query = count_query.where(Exercise.name.ilike(f"%{search}%"))
    if type:
        query = query.where(Exercise.type == type)
        count_query = count_query.where(Exercise.type == type)
    if muscle_group:
        query = query.where(Exercise.muscle_groups.any(muscle_group))
        count_query = count_query.where(Exercise.muscle_groups.any(muscle_group))
    if equipment:
        query = query.where(Exercise.equipment.ilike(f"%{equipment}%"))
        count_query = count_query.where(Exercise.equipment.ilike(f"%{equipment}%"))

    total = (await db.execute(count_query)).scalar_one()
    response.headers["X-Total-Count"] = str(total)

    query = query.order_by(Exercise.name).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = result.scalar_one_or_none()
    if not exercise:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    if not exercise.is_global and exercise.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este ejercicio")
    return exercise


@router.post("", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
async def create_exercise(
    data: ExerciseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "athlete":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los atletas no pueden crear ejercicios",
        )
    exercise = Exercise(
        name=data.name,
        type=data.type,
        muscle_groups=data.muscle_groups,
        equipment=data.equipment,
        description=data.description,
        is_global=False,
        created_by=current_user.id,
    )
    db.add(exercise)
    await db.flush()
    await db.refresh(exercise)
    return exercise


@router.put("/{exercise_id}", response_model=ExerciseResponse)
async def update_exercise(
    exercise_id: int,
    data: ExerciseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = result.scalar_one_or_none()
    if not exercise:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    if exercise.is_global and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="No puedes editar ejercicios globales")
    if not exercise.is_global and exercise.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes editar este ejercicio")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(exercise, field, value)

    await db.flush()
    await db.refresh(exercise)
    return exercise


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = result.scalar_one_or_none()
    if not exercise:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    if exercise.is_global and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="No puedes eliminar ejercicios globales")
    if not exercise.is_global and exercise.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar este ejercicio")

    await db.delete(exercise)
