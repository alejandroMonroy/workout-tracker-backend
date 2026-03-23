from fastapi import APIRouter

from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.coach import router as coach_router
from app.api.endpoints.exercises import router as exercises_router
from app.api.endpoints.plans import router as plans_router
from app.api.endpoints.sessions import router as sessions_router
from app.api.endpoints.stats import router as stats_router
from app.api.endpoints.templates import router as templates_router
from app.api.endpoints.xp import router as xp_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(exercises_router)
api_router.include_router(templates_router)
api_router.include_router(plans_router)
api_router.include_router(sessions_router)
api_router.include_router(stats_router)
api_router.include_router(coach_router)
api_router.include_router(xp_router)
