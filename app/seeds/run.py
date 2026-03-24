"""
Seed runner: populates the database with initial data.
Usage: python -m app.seeds.run
"""

import asyncio

from sqlalchemy import select

from app.core.database import async_session, engine, Base
from app.models import Exercise
from app.models.coach_athlete import CoachAthlete, CoachAthleteStatus
from app.models.event import (
    Event,
    EventCollaborator,
    EventRegistration,
    EventStatus,
    RegistrationStatus,
)
from app.models.partner_company import PartnerCompany, Product
from app.models.training_center import (
    CenterMemberRole,
    CenterMemberStatus,
    CenterMembership,
    TrainingCenter,
)
from app.models.user import User
from app.seeds.community import (
    _PWD,
    CENTER_MEMBERSHIPS,
    COACH_ATHLETE_PAIRS,
    EVENT_COLLABORATORS,
    EVENT_REGISTRATIONS,
    EVENTS,
    PARTNER_COMPANIES,
    PRODUCTS,
    TRAINING_CENTERS,
    USERS,
)
from app.seeds.exercises import EXERCISES


async def seed_exercises() -> None:
    async with async_session() as session:
        # Get existing exercise names to avoid duplicates
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


async def seed_community() -> None:
    """Seed users, coaches, centers, companies, events and all relationships."""
    async with async_session() as session:
        # ── 1. Users ─────────────────────────────────────────────────────
        result = await session.execute(select(User.email))
        existing_emails: set[str] = {row[0] for row in result.all()}

        email_to_id: dict[str, int] = {}

        # Load IDs of already-existing users
        if existing_emails:
            rows = await session.execute(
                select(User.id, User.email).where(User.email.in_(existing_emails))
            )
            for uid, uemail in rows.all():
                email_to_id[uemail] = uid

        new_users = [u for u in USERS if u["email"] not in existing_emails]

        if new_users:
            print(f"🌱 Creando {len(new_users)} usuarios...")
            for u_data in new_users:
                user = User(
                    email=u_data["email"],
                    password_hash=_PWD,
                    name=u_data["name"],
                    role=u_data["role"],
                    sex=u_data.get("sex"),
                    birth_date=u_data.get("birth_date"),
                    height_cm=u_data.get("height_cm"),
                    weight_kg=u_data.get("weight_kg"),
                    units_preference=u_data.get("units_preference"),
                )
                session.add(user)
            await session.flush()

            # Refetch all IDs
            rows = await session.execute(
                select(User.id, User.email).where(
                    User.email.in_([u["email"] for u in USERS])
                )
            )
            for uid, uemail in rows.all():
                email_to_id[uemail] = uid

            print(f"✅ {len(new_users)} usuarios creados.")
        else:
            print("ℹ️  Todos los usuarios demo ya existen.")

        # ── 2. Coach-Athlete ─────────────────────────────────────────────
        result = await session.execute(
            select(CoachAthlete.coach_id, CoachAthlete.athlete_id)
        )
        existing_ca: set[tuple[int, int]] = {(r[0], r[1]) for r in result.all()}

        new_ca = 0
        for coach_email, athlete_email in COACH_ATHLETE_PAIRS:
            cid = email_to_id.get(coach_email)
            aid = email_to_id.get(athlete_email)
            if cid and aid and (cid, aid) not in existing_ca:
                session.add(
                    CoachAthlete(
                        coach_id=cid,
                        athlete_id=aid,
                        status=CoachAthleteStatus.ACTIVE,
                    )
                )
                new_ca += 1

        if new_ca:
            await session.flush()
            print(f"✅ {new_ca} relaciones coach-atleta creadas.")
        else:
            print("ℹ️  Relaciones coach-atleta ya existen.")

        # ── 3. Training Centers ──────────────────────────────────────────
        result = await session.execute(select(TrainingCenter.name))
        existing_center_names: set[str] = {row[0] for row in result.all()}

        name_to_center_id: dict[str, int] = {}

        if existing_center_names:
            rows = await session.execute(
                select(TrainingCenter.id, TrainingCenter.name).where(
                    TrainingCenter.name.in_(existing_center_names)
                )
            )
            for cid, cname in rows.all():
                name_to_center_id[cname] = cid

        new_centers = [c for c in TRAINING_CENTERS if c["name"] not in existing_center_names]

        if new_centers:
            print(f"🌱 Creando {len(new_centers)} centros de entrenamiento...")
            for c_data in new_centers:
                center = TrainingCenter(
                    name=c_data["name"],
                    description=c_data.get("description"),
                    address=c_data.get("address"),
                    city=c_data.get("city"),
                    phone=c_data.get("phone"),
                    email=c_data.get("email"),
                    website=c_data.get("website"),
                    owner_id=email_to_id[c_data["owner_email"]],
                )
                session.add(center)
            await session.flush()

            rows = await session.execute(
                select(TrainingCenter.id, TrainingCenter.name).where(
                    TrainingCenter.name.in_([c["name"] for c in TRAINING_CENTERS])
                )
            )
            for cid, cname in rows.all():
                name_to_center_id[cname] = cid

            print(f"✅ {len(new_centers)} centros creados.")
        else:
            print("ℹ️  Centros de entrenamiento ya existen.")

        # ── 4. Center Memberships ────────────────────────────────────────
        result = await session.execute(
            select(CenterMembership.center_id, CenterMembership.user_id)
        )
        existing_cm: set[tuple[int, int]] = {(r[0], r[1]) for r in result.all()}

        new_cm = 0
        for center_name, user_email, role, status in CENTER_MEMBERSHIPS:
            cid = name_to_center_id.get(center_name)
            uid = email_to_id.get(user_email)
            if cid and uid and (cid, uid) not in existing_cm:
                session.add(
                    CenterMembership(
                        center_id=cid,
                        user_id=uid,
                        role=CenterMemberRole(role),
                        status=CenterMemberStatus(status),
                    )
                )
                new_cm += 1

        if new_cm:
            await session.flush()
            print(f"✅ {new_cm} membresías de centro creadas.")
        else:
            print("ℹ️  Membresías de centro ya existen.")

        # ── 5. Partner Companies ─────────────────────────────────────────
        result = await session.execute(select(PartnerCompany.name))
        existing_company_names: set[str] = {row[0] for row in result.all()}

        name_to_company_id: dict[str, int] = {}

        if existing_company_names:
            rows = await session.execute(
                select(PartnerCompany.id, PartnerCompany.name).where(
                    PartnerCompany.name.in_(existing_company_names)
                )
            )
            for pid, pname in rows.all():
                name_to_company_id[pname] = pid

        new_companies = [c for c in PARTNER_COMPANIES if c["name"] not in existing_company_names]

        if new_companies:
            print(f"🌱 Creando {len(new_companies)} empresas colaboradoras...")
            for c_data in new_companies:
                company = PartnerCompany(
                    name=c_data["name"],
                    description=c_data.get("description"),
                    website=c_data.get("website"),
                    contact_email=c_data.get("contact_email"),
                )
                session.add(company)
            await session.flush()

            rows = await session.execute(
                select(PartnerCompany.id, PartnerCompany.name).where(
                    PartnerCompany.name.in_([c["name"] for c in PARTNER_COMPANIES])
                )
            )
            for pid, pname in rows.all():
                name_to_company_id[pname] = pid

            print(f"✅ {len(new_companies)} empresas creadas.")
        else:
            print("ℹ️  Empresas colaboradoras ya existen.")

        # ── 6. Products ──────────────────────────────────────────────────
        result = await session.execute(select(Product.name))
        existing_product_names: set[str] = {row[0] for row in result.all()}

        new_products = [p for p in PRODUCTS if p["name"] not in existing_product_names]

        if new_products:
            print(f"🌱 Creando {len(new_products)} productos...")
            for p_data in new_products:
                product = Product(
                    company_id=name_to_company_id[p_data["company_name"]],
                    name=p_data["name"],
                    description=p_data.get("description"),
                    item_type=p_data.get("item_type", "product"),
                    xp_cost=p_data.get("xp_cost"),
                    discount_pct=p_data.get("discount_pct"),
                    price=p_data.get("price"),
                    currency=p_data.get("currency", "EUR"),
                    external_url=p_data.get("external_url"),
                )
                session.add(product)
            await session.flush()
            print(f"✅ {len(new_products)} productos creados.")
        else:
            print("ℹ️  Productos ya existen.")

        # ── 7. Events ────────────────────────────────────────────────────
        result = await session.execute(select(Event.name))
        existing_event_names: set[str] = {row[0] for row in result.all()}

        name_to_event_id: dict[str, int] = {}

        if existing_event_names:
            rows = await session.execute(
                select(Event.id, Event.name).where(Event.name.in_(existing_event_names))
            )
            for eid, ename in rows.all():
                name_to_event_id[ename] = eid

        new_events = [e for e in EVENTS if e["name"] not in existing_event_names]

        if new_events:
            print(f"🌱 Creando {len(new_events)} eventos...")
            for e_data in new_events:
                event = Event(
                    name=e_data["name"],
                    description=e_data.get("description"),
                    event_date=e_data["event_date"],
                    end_date=e_data.get("end_date"),
                    location=e_data.get("location"),
                    capacity=e_data.get("capacity"),
                    status=EventStatus(e_data["status"]),
                    is_public=e_data.get("is_public", True),
                    event_type=e_data.get("event_type", "other"),
                    center_id=(
                        name_to_center_id.get(e_data["center_name"])
                        if e_data.get("center_name")
                        else None
                    ),
                    company_id=(
                        name_to_company_id.get(e_data["company_name"])
                        if e_data.get("company_name")
                        else None
                    ),
                )
                session.add(event)
            await session.flush()

            rows = await session.execute(
                select(Event.id, Event.name).where(
                    Event.name.in_([e["name"] for e in EVENTS])
                )
            )
            for eid, ename in rows.all():
                name_to_event_id[ename] = eid

            print(f"✅ {len(new_events)} eventos creados.")
        else:
            print("ℹ️  Eventos ya existen.")

        # Update event_type for any events that still have the default "other"
        event_type_map = {e["name"]: e.get("event_type", "other") for e in EVENTS}
        for ename, eid in name_to_event_id.items():
            desired_type = event_type_map.get(ename, "other")
            if desired_type != "other":
                await session.execute(
                    select(Event).where(Event.id == eid)
                )
                ev_obj = (await session.execute(
                    select(Event).where(Event.id == eid)
                )).scalar_one_or_none()
                if ev_obj and ev_obj.event_type != desired_type:
                    ev_obj.event_type = desired_type

        # ── 8. Event Collaborators ───────────────────────────────────────
        result = await session.execute(
            select(
                EventCollaborator.event_id,
                EventCollaborator.company_id,
                EventCollaborator.center_id,
            )
        )
        existing_ec: set[tuple[int, int | None, int | None]] = {
            (r[0], r[1], r[2]) for r in result.all()
        }

        new_ec = 0
        for event_name, company_name, center_name in EVENT_COLLABORATORS:
            eid = name_to_event_id.get(event_name)
            comp_id = name_to_company_id.get(company_name) if company_name else None
            cent_id = name_to_center_id.get(center_name) if center_name else None
            if eid and (eid, comp_id, cent_id) not in existing_ec:
                session.add(
                    EventCollaborator(
                        event_id=eid,
                        company_id=comp_id,
                        center_id=cent_id,
                    )
                )
                new_ec += 1

        if new_ec:
            await session.flush()
            print(f"✅ {new_ec} colaboradores de evento creados.")
        else:
            print("ℹ️  Colaboradores de evento ya existen.")

        # ── 9. Event Registrations ───────────────────────────────────────
        result = await session.execute(
            select(EventRegistration.event_id, EventRegistration.user_id)
        )
        existing_er: set[tuple[int, int]] = {(r[0], r[1]) for r in result.all()}

        new_er = 0
        for event_name, user_email in EVENT_REGISTRATIONS:
            eid = name_to_event_id.get(event_name)
            uid = email_to_id.get(user_email)
            if eid and uid and (eid, uid) not in existing_er:
                # Past completed events → mark as attended
                event_data = next(
                    (e for e in EVENTS if e["name"] == event_name), None
                )
                reg_status = RegistrationStatus.REGISTERED
                if event_data and event_data.get("status") == "completed":
                    reg_status = RegistrationStatus.ATTENDED

                session.add(
                    EventRegistration(
                        event_id=eid,
                        user_id=uid,
                        status=reg_status,
                    )
                )
                new_er += 1

        if new_er:
            await session.flush()
            print(f"✅ {new_er} inscripciones de evento creadas.")
        else:
            print("ℹ️  Inscripciones de evento ya existen.")

        # ── Commit everything ────────────────────────────────────────────
        await session.commit()
        print("🎉 Seed de comunidad completado.")


async def main() -> None:
    # Create tables if they don't exist (for development convenience)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_exercises()
    await seed_community()


if __name__ == "__main__":
    asyncio.run(main())
