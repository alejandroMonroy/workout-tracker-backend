"""
Seed runner: populates the database with initial data.
Usage: python -m app.seeds.run
"""

import asyncio

from sqlalchemy import select

from app.core.database import async_session, engine, Base
from app.models import Exercise
from app.seeds.exercises import EXERCISES


async def seed_exercises() -> None:
    async with async_session() as session:
        result = await session.execute(select(Exercise.name))
        existing_names: set[str] = {row[0] for row in result.all()}

        new_exercises = [ex for ex in EXERCISES if ex["name"] not in existing_names]

        if not new_exercises:
            print(f"ℹ️  Los {len(EXERCISES)} ejercicios del catálogo ya existen en la base de datos.")
            return

        print(f"🌱 Insertando {len(new_exercises)} ejercicios nuevos (ya existían {len(existing_names)})...")

        for ex_data in new_exercises:
            exercise = Exercise(
                name=ex_data["name"],
                type=ex_data["type"],
                muscle_groups=ex_data.get("muscle_groups"),
                equipment=ex_data.get("equipment"),
                description=ex_data.get("description"),
                is_global=True,
                created_by=None,
            )
            session.add(exercise)

        await session.commit()
        print(f"✅ {len(new_exercises)} ejercicios insertados correctamente.")


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_exercises()


if __name__ == "__main__":
    asyncio.run(main())
