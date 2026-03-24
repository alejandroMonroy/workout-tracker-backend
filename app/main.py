from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.database import async_session
from app.services.division import bulk_enroll_all_users, process_previous_season


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: process last week + enroll all users into current week
    async with async_session() as db:
        try:
            await process_previous_season(db)
            created = await bulk_enroll_all_users(db)
            await db.commit()
            if created:
                print(f"🏆 Liga: {created} usuarios inscritos en la semana actual")
        except Exception as e:
            await db.rollback()
            print(f"⚠️  Error al pre-inscribir liga: {e}")
    yield


app = FastAPI(
    title="Workout Tracker API",
    description="API para el registro y seguimiento de entrenamientos",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringir a los dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
