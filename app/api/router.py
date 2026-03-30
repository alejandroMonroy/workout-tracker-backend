from fastapi import APIRouter

from app.api.endpoints.athletes import router as athletes_router
from app.api.endpoints.challenges import router as challenges_router
from app.api.endpoints.competitions import router as competitions_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.coaches import router as coaches_router
from app.api.endpoints.dashboard import router as dashboard_router
from app.api.endpoints.divisions import router as divisions_router
from app.api.endpoints.exercises import router as exercises_router
from app.api.endpoints.gyms import router as gyms_router
from app.api.endpoints.marketplace import router as marketplace_router
from app.api.endpoints.messages import router as messages_router
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
api_router.include_router(xp_router)
api_router.include_router(divisions_router)
api_router.include_router(dashboard_router)
api_router.include_router(athletes_router)
api_router.include_router(coaches_router)
api_router.include_router(gyms_router)
api_router.include_router(marketplace_router)
api_router.include_router(messages_router)
api_router.include_router(challenges_router)
api_router.include_router(competitions_router)
