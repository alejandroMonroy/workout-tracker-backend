from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.xp import XPTransaction, xp_for_level
from app.schemas.xp import LeaderboardEntry, XPSummaryResponse, XPTransactionResponse

router = APIRouter(prefix="/xp", tags=["XP"])


@router.get("/summary", response_model=XPSummaryResponse)
async def get_xp_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's XP summary with level progress."""
    total_xp = current_user.total_xp or 0
    level = current_user.level or 1

    current_level_xp = xp_for_level(level)
    next_level_xp = xp_for_level(level + 1)
    xp_progress = total_xp - current_level_xp
    xp_needed = next_level_xp - current_level_xp

    progress_pct = (xp_progress / xp_needed * 100) if xp_needed > 0 else 100.0

    # Rank among all users
    rank_result = await db.execute(
        select(func.count(User.id) + 1).where(User.total_xp > total_xp)
    )
    rank = rank_result.scalar_one()

    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar_one()

    return XPSummaryResponse(
        total_xp=total_xp,
        level=level,
        xp_for_current_level=current_level_xp,
        xp_for_next_level=next_level_xp,
        xp_progress=xp_progress,
        xp_needed=xp_needed,
        progress_pct=round(min(progress_pct, 100), 1),
        rank=rank,
        total_users=total_users,
    )


@router.get("/history", response_model=list[XPTransactionResponse])
async def get_xp_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get XP transaction history for current user."""
    result = await db.execute(
        select(XPTransaction)
        .where(XPTransaction.user_id == current_user.id)
        .order_by(XPTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get top users by XP."""
    result = await db.execute(
        select(User)
        .where(User.total_xp > 0)
        .order_by(User.total_xp.desc())
        .limit(limit)
    )
    users = result.scalars().all()

    return [
        LeaderboardEntry(
            user_id=u.id,
            name=u.name,
            total_xp=u.total_xp or 0,
            level=u.level or 1,
            rank=i + 1,
            avatar_url=u.avatar_url,
        )
        for i, u in enumerate(users)
    ]
