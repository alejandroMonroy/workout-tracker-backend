"""
Seed data: users, coaches, training centers, partner companies, events,
and all relationships between them (memberships, coach-athlete, collaborators,
registrations, center plans).
"""

from datetime import date, datetime, timedelta, timezone

from app.core.security import hash_password
from app.models.user import UserRole, UnitsPreference, SexType

# ──────────────────────────────────────────────────────────────────────────────
# Users & Coaches
# ──────────────────────────────────────────────────────────────────────────────

_PWD = hash_password("Password1!")  # shared demo password

USERS: list[dict] = [
    # ── Coaches ──
    {
        "email": "coach.luis@demo.com",
        "name": "Luis García",
        "role": UserRole.COACH,
        "sex": SexType.MALE,
        "birth_date": date(1985, 4, 12),
        "height_cm": 180.0,
        "weight_kg": 85.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "coach.marta@demo.com",
        "name": "Marta Fernández",
        "role": UserRole.COACH,
        "sex": SexType.FEMALE,
        "birth_date": date(1990, 8, 25),
        "height_cm": 168.0,
        "weight_kg": 62.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "coach.pedro@demo.com",
        "name": "Pedro Martínez",
        "role": UserRole.COACH,
        "sex": SexType.MALE,
        "birth_date": date(1988, 1, 3),
        "height_cm": 175.0,
        "weight_kg": 78.0,
        "units_preference": UnitsPreference.METRIC,
    },
    # ── Athletes ──
    {
        "email": "ana.lopez@demo.com",
        "name": "Ana López",
        "role": UserRole.ATHLETE,
        "sex": SexType.FEMALE,
        "birth_date": date(1995, 11, 7),
        "height_cm": 165.0,
        "weight_kg": 58.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "carlos.ruiz@demo.com",
        "name": "Carlos Ruiz",
        "role": UserRole.ATHLETE,
        "sex": SexType.MALE,
        "birth_date": date(1992, 3, 20),
        "height_cm": 178.0,
        "weight_kg": 82.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "sofia.torres@demo.com",
        "name": "Sofía Torres",
        "role": UserRole.ATHLETE,
        "sex": SexType.FEMALE,
        "birth_date": date(1998, 6, 15),
        "height_cm": 170.0,
        "weight_kg": 63.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "david.moreno@demo.com",
        "name": "David Moreno",
        "role": UserRole.ATHLETE,
        "sex": SexType.MALE,
        "birth_date": date(1994, 9, 1),
        "height_cm": 183.0,
        "weight_kg": 90.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "laura.jimenez@demo.com",
        "name": "Laura Jiménez",
        "role": UserRole.ATHLETE,
        "sex": SexType.FEMALE,
        "birth_date": date(1997, 12, 30),
        "height_cm": 160.0,
        "weight_kg": 55.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "pablo.sanchez@demo.com",
        "name": "Pablo Sánchez",
        "role": UserRole.ATHLETE,
        "sex": SexType.MALE,
        "birth_date": date(1991, 5, 18),
        "height_cm": 176.0,
        "weight_kg": 80.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "elena.navarro@demo.com",
        "name": "Elena Navarro",
        "role": UserRole.ATHLETE,
        "sex": SexType.FEMALE,
        "birth_date": date(2000, 2, 14),
        "height_cm": 172.0,
        "weight_kg": 60.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "jorge.diaz@demo.com",
        "name": "Jorge Díaz",
        "role": UserRole.ATHLETE,
        "sex": SexType.MALE,
        "birth_date": date(1993, 7, 22),
        "height_cm": 185.0,
        "weight_kg": 92.0,
        "units_preference": UnitsPreference.IMPERIAL,
    },
    {
        "email": "maria.castro@demo.com",
        "name": "María Castro",
        "role": UserRole.ATHLETE,
        "sex": SexType.FEMALE,
        "birth_date": date(1996, 10, 5),
        "height_cm": 163.0,
        "weight_kg": 57.0,
        "units_preference": UnitsPreference.METRIC,
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Coach-Athlete relationships
# Each tuple: (coach_email, athlete_email)
# ──────────────────────────────────────────────────────────────────────────────

COACH_ATHLETE_PAIRS: list[tuple[str, str]] = [
    # Luis coaches 4 athletes
    ("coach.luis@demo.com", "ana.lopez@demo.com"),
    ("coach.luis@demo.com", "carlos.ruiz@demo.com"),
    ("coach.luis@demo.com", "sofia.torres@demo.com"),
    ("coach.luis@demo.com", "david.moreno@demo.com"),
    # Marta coaches 3 athletes
    ("coach.marta@demo.com", "laura.jimenez@demo.com"),
    ("coach.marta@demo.com", "pablo.sanchez@demo.com"),
    ("coach.marta@demo.com", "elena.navarro@demo.com"),
    # Pedro coaches 2 athletes
    ("coach.pedro@demo.com", "jorge.diaz@demo.com"),
    ("coach.pedro@demo.com", "maria.castro@demo.com"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Training Centers
# ──────────────────────────────────────────────────────────────────────────────

TRAINING_CENTERS: list[dict] = [
    {
        "name": "CrossFit Volcán",
        "description": "Box de CrossFit en el centro de Madrid con programación diaria y open gym.",
        "address": "Calle de la Energía 42",
        "city": "Madrid",
        "phone": "+34 910 123 456",
        "email": "info@crossfitvolcan.es",
        "website": "https://crossfitvolcan.es",
        "owner_email": "coach.luis@demo.com",
    },
    {
        "name": "Olimpia Training Lab",
        "description": "Centro especializado en halterofilia y preparación física. Equipamiento Eleiko.",
        "address": "Avenida Olímpica 15",
        "city": "Barcelona",
        "phone": "+34 933 456 789",
        "email": "hola@olimpialab.com",
        "website": "https://olimpialab.com",
        "owner_email": "coach.marta@demo.com",
    },
    {
        "name": "The Garage Fitness",
        "description": "Garage gym con ambiente familiar. Clases reducidas y atención personalizada.",
        "address": "Polígono Industrial 7, Nave 3",
        "city": "Valencia",
        "phone": "+34 961 234 567",
        "email": "contacto@garagefitness.es",
        "website": "https://garagefitness.es",
        "owner_email": "coach.pedro@demo.com",
    },
]


# Center membership assignments
# Each tuple: (center_name, user_email, role, status)
CENTER_MEMBERSHIPS: list[tuple[str, str, str, str]] = [
    # CrossFit Volcán — Luis is owner (auto), Marta coaches there too
    ("CrossFit Volcán", "coach.luis@demo.com", "admin", "active"),
    ("CrossFit Volcán", "coach.marta@demo.com", "coach", "active"),
    ("CrossFit Volcán", "ana.lopez@demo.com", "member", "active"),
    ("CrossFit Volcán", "carlos.ruiz@demo.com", "member", "active"),
    ("CrossFit Volcán", "sofia.torres@demo.com", "member", "active"),
    ("CrossFit Volcán", "david.moreno@demo.com", "member", "active"),
    ("CrossFit Volcán", "pablo.sanchez@demo.com", "member", "pending"),

    # Olimpia Training Lab — Marta owns, Pedro also coaches
    ("Olimpia Training Lab", "coach.marta@demo.com", "admin", "active"),
    ("Olimpia Training Lab", "coach.pedro@demo.com", "coach", "active"),
    ("Olimpia Training Lab", "laura.jimenez@demo.com", "member", "active"),
    ("Olimpia Training Lab", "elena.navarro@demo.com", "member", "active"),
    ("Olimpia Training Lab", "jorge.diaz@demo.com", "member", "active"),
    ("Olimpia Training Lab", "ana.lopez@demo.com", "member", "active"),  # Ana in 2 centers

    # The Garage Fitness — Pedro owns
    ("The Garage Fitness", "coach.pedro@demo.com", "admin", "active"),
    ("The Garage Fitness", "jorge.diaz@demo.com", "member", "active"),
    ("The Garage Fitness", "maria.castro@demo.com", "member", "active"),
    ("The Garage Fitness", "david.moreno@demo.com", "member", "pending"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Partner Companies
# ──────────────────────────────────────────────────────────────────────────────

PARTNER_COMPANIES: list[dict] = [
    {
        "name": "NutriForce",
        "description": "Suplementación deportiva premium: proteínas, creatina, vitaminas y más.",
        "website": "https://nutriforce.es",
        "contact_email": "partners@nutriforce.es",
    },
    {
        "name": "Titan Gear",
        "description": "Material de entrenamiento: rodilleras, muñequeras, cinturones y ropa técnica.",
        "website": "https://titangear.com",
        "contact_email": "info@titangear.com",
    },
    {
        "name": "WOD Snacks",
        "description": "Snacks y barritas energéticas diseñados para atletas funcionales.",
        "website": "https://wodsnacks.es",
        "contact_email": "collab@wodsnacks.es",
    },
]


PRODUCTS: list[dict] = [
    # NutriForce products
    {
        "company_name": "NutriForce",
        "name": "Whey Protein Isolate 2 kg",
        "description": "Proteína de suero aislada, 90 % pureza, sabor chocolate.",
        "price": 49.99,
        "currency": "EUR",
        "external_url": "https://nutriforce.es/whey-isolate",
    },
    {
        "company_name": "NutriForce",
        "name": "Creatina Monohidrato 500 g",
        "description": "Creatina micronizada, 100 servicios.",
        "price": 24.99,
        "currency": "EUR",
        "external_url": "https://nutriforce.es/creatina",
    },
    {
        "company_name": "NutriForce",
        "name": "Multivitamínico Atleta 90 caps",
        "description": "Fórmula completa con vitaminas y minerales para deportistas.",
        "price": 18.50,
        "currency": "EUR",
        "external_url": "https://nutriforce.es/multi",
    },
    {
        "company_name": "NutriForce",
        "name": "Pre-Workout Volcano 300 g",
        "description": "Pre-entreno con cafeína, beta-alanina y citrulina. Sabor sandía.",
        "price": 29.99,
        "currency": "EUR",
        "external_url": "https://nutriforce.es/preworkout",
    },
    # Titan Gear products
    {
        "company_name": "Titan Gear",
        "name": "Rodilleras 7 mm Neopreno (par)",
        "description": "Rodilleras de competición, soporte máximo para sentadilla y cleans.",
        "price": 39.99,
        "currency": "EUR",
        "external_url": "https://titangear.com/rodilleras",
    },
    {
        "company_name": "Titan Gear",
        "name": "Cinturón Lever 10 mm",
        "description": "Cinturón de halterofilia con cierre lever, cuero genuino.",
        "price": 89.99,
        "currency": "EUR",
        "external_url": "https://titangear.com/cinturon",
    },
    {
        "company_name": "Titan Gear",
        "name": "Muñequeras WOD Wrap",
        "description": "Muñequeras de 45 cm con velcro reforzado.",
        "price": 15.99,
        "currency": "EUR",
        "external_url": "https://titangear.com/wrist-wraps",
    },
    {
        "company_name": "Titan Gear",
        "name": "Calleras Grips Pro",
        "description": "Calleras de fibra de carbono para pull-ups y muscle-ups.",
        "price": 27.50,
        "currency": "EUR",
        "external_url": "https://titangear.com/grips",
    },
    # WOD Snacks products
    {
        "company_name": "WOD Snacks",
        "name": "Barrita Energética Cacao & Avena (12 uds)",
        "description": "Barritas naturales con avena, cacao y miel. Sin aditivos.",
        "price": 22.00,
        "currency": "EUR",
        "external_url": "https://wodsnacks.es/barrita-cacao",
    },
    {
        "company_name": "WOD Snacks",
        "name": "Mix Frutos Secos Athlete 500 g",
        "description": "Mezcla de almendras, nueces, anacardos y arándanos.",
        "price": 12.99,
        "currency": "EUR",
        "external_url": "https://wodsnacks.es/mix-frutos",
    },
    {
        "company_name": "WOD Snacks",
        "name": "Gel Energético Citrus (pack 10)",
        "description": "Geles energéticos de rápida absorción, sabor cítrico.",
        "price": 19.99,
        "currency": "EUR",
        "external_url": "https://wodsnacks.es/gel-citrus",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Events
# ──────────────────────────────────────────────────────────────────────────────

_NOW = datetime.now(timezone.utc)

EVENTS: list[dict] = [
    # ── Events organized by centers ──
    {
        "name": "WOD Solidario CrossFit Volcán",
        "description": "Evento benéfico: todos los fondos se destinan a la Fundación Deporte para Todos. "
                       "3 WODs en equipo, comida incluida y rifa de premios.",
        "event_date": _NOW + timedelta(days=14),
        "end_date": _NOW + timedelta(days=14, hours=6),
        "location": "CrossFit Volcán, Calle de la Energía 42, Madrid",
        "capacity": 60,
        "status": "published",
        "is_public": True,
        "center_name": "CrossFit Volcán",
        "company_name": None,
    },
    {
        "name": "Clínica de Snatch — Nivel Intermedio",
        "description": "Taller técnico de 3 horas con análisis de vídeo. "
                       "Impartido por la coach Marta Fernández.",
        "event_date": _NOW + timedelta(days=7),
        "end_date": _NOW + timedelta(days=7, hours=3),
        "location": "Olimpia Training Lab, Av. Olímpica 15, Barcelona",
        "capacity": 16,
        "status": "published",
        "is_public": False,
        "center_name": "Olimpia Training Lab",
        "company_name": None,
    },
    {
        "name": "Open Day — The Garage Fitness",
        "description": "Jornada de puertas abiertas: clases gratuitas, tour por las instalaciones "
                       "y descuentos exclusivos para nuevos socios.",
        "event_date": _NOW + timedelta(days=21),
        "end_date": _NOW + timedelta(days=21, hours=8),
        "location": "The Garage Fitness, Polígono Industrial 7, Valencia",
        "capacity": 40,
        "status": "published",
        "is_public": True,
        "center_name": "The Garage Fitness",
        "company_name": None,
    },
    # ── Event organized by a company ──
    {
        "name": "NutriForce Athlete Summit 2026",
        "description": "Cumbre de nutrición deportiva: charlas, degustaciones y descuentos de lanzamiento.",
        "event_date": _NOW + timedelta(days=30),
        "end_date": _NOW + timedelta(days=30, hours=5),
        "location": "Hotel Fitness Barcelona, Sala Olimpia",
        "capacity": 100,
        "status": "published",
        "is_public": True,
        "center_name": None,
        "company_name": "NutriForce",
    },
    # ── Past event (completed) ──
    {
        "name": "Throwdown Interbox Madrid 2026",
        "description": "Competición interbox de equipos de 4 personas. "
                       "Categorías RX y Scaled.",
        "event_date": _NOW - timedelta(days=10),
        "end_date": _NOW - timedelta(days=10) + timedelta(hours=8),
        "location": "Pabellón Municipal de Deportes, Madrid",
        "capacity": 80,
        "status": "completed",
        "is_public": True,
        "center_name": "CrossFit Volcán",
        "company_name": None,
    },
    # ── Draft event ──
    {
        "name": "Summer Throwdown Valencia",
        "description": "Competición de verano en la playa. Todavía en fase de planificación.",
        "event_date": _NOW + timedelta(days=90),
        "end_date": _NOW + timedelta(days=90, hours=10),
        "location": "Playa de la Malvarrosa, Valencia",
        "capacity": 120,
        "status": "draft",
        "is_public": True,
        "center_name": "The Garage Fitness",
        "company_name": None,
    },
]


# Event collaborators: (event_name, company_name | None, center_name | None)
EVENT_COLLABORATORS: list[tuple[str, str | None, str | None]] = [
    # WOD Solidario — sponsored by Titan Gear, WOD Snacks, and Olimpia Lab collaborates
    ("WOD Solidario CrossFit Volcán", "Titan Gear", None),
    ("WOD Solidario CrossFit Volcán", "WOD Snacks", None),
    ("WOD Solidario CrossFit Volcán", None, "Olimpia Training Lab"),
    # NutriForce Summit — CrossFit Volcán & Olimpia Lab collaborate
    ("NutriForce Athlete Summit 2026", None, "CrossFit Volcán"),
    ("NutriForce Athlete Summit 2026", None, "Olimpia Training Lab"),
    ("NutriForce Athlete Summit 2026", "Titan Gear", None),
    # Open Day — NutriForce sponsors
    ("Open Day — The Garage Fitness", "NutriForce", None),
    # Throwdown Madrid — all companies sponsor
    ("Throwdown Interbox Madrid 2026", "NutriForce", None),
    ("Throwdown Interbox Madrid 2026", "Titan Gear", None),
    ("Throwdown Interbox Madrid 2026", "WOD Snacks", None),
]


# Event registrations: (event_name, user_email)
EVENT_REGISTRATIONS: list[tuple[str, str]] = [
    # WOD Solidario
    ("WOD Solidario CrossFit Volcán", "ana.lopez@demo.com"),
    ("WOD Solidario CrossFit Volcán", "carlos.ruiz@demo.com"),
    ("WOD Solidario CrossFit Volcán", "sofia.torres@demo.com"),
    ("WOD Solidario CrossFit Volcán", "david.moreno@demo.com"),
    ("WOD Solidario CrossFit Volcán", "coach.luis@demo.com"),
    ("WOD Solidario CrossFit Volcán", "laura.jimenez@demo.com"),
    # Clínica de Snatch (only center members)
    ("Clínica de Snatch — Nivel Intermedio", "laura.jimenez@demo.com"),
    ("Clínica de Snatch — Nivel Intermedio", "elena.navarro@demo.com"),
    ("Clínica de Snatch — Nivel Intermedio", "jorge.diaz@demo.com"),
    ("Clínica de Snatch — Nivel Intermedio", "ana.lopez@demo.com"),
    # Open Day
    ("Open Day — The Garage Fitness", "jorge.diaz@demo.com"),
    ("Open Day — The Garage Fitness", "maria.castro@demo.com"),
    ("Open Day — The Garage Fitness", "pablo.sanchez@demo.com"),
    # NutriForce Summit
    ("NutriForce Athlete Summit 2026", "coach.marta@demo.com"),
    ("NutriForce Athlete Summit 2026", "coach.luis@demo.com"),
    ("NutriForce Athlete Summit 2026", "ana.lopez@demo.com"),
    ("NutriForce Athlete Summit 2026", "carlos.ruiz@demo.com"),
    ("NutriForce Athlete Summit 2026", "elena.navarro@demo.com"),
    # Throwdown (past — attended)
    ("Throwdown Interbox Madrid 2026", "ana.lopez@demo.com"),
    ("Throwdown Interbox Madrid 2026", "carlos.ruiz@demo.com"),
    ("Throwdown Interbox Madrid 2026", "sofia.torres@demo.com"),
    ("Throwdown Interbox Madrid 2026", "david.moreno@demo.com"),
    ("Throwdown Interbox Madrid 2026", "jorge.diaz@demo.com"),
    ("Throwdown Interbox Madrid 2026", "maria.castro@demo.com"),
    ("Throwdown Interbox Madrid 2026", "coach.pedro@demo.com"),
    ("Throwdown Interbox Madrid 2026", "coach.luis@demo.com"),
]
