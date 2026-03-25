from fastapi import APIRouter

from app.api.endpoints.athletes import router as athletes_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.dashboard import router as dashboard_router
from app.api.endpoints.divisions import router as divisions_router
from app.api.endpoints.exercises import router as exercises_router
from app.api.endpoints.sessions import router as sessions_router
from app.api.endpoints.stats import router as stats_router
from app.api.endpoints.templates import router as templates_router
from app.api.endpoints.xp import router as xp_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(exercises_router)
api_router.include_router(templates_router)
api_router.include_router(sessions_router)
api_router.include_router(stats_router)
api_router.include_router(xp_router)
api_router.include_router(divisions_router)
api_router.include_router(dashboard_router)
api_router.include_router(athletes_router)
