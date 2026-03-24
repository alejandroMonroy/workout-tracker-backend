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
    # ── Admin ──
    {
        "email": "admin@wodtek.com",
        "name": "Admin WodTek",
        "role": UserRole.ADMIN,
        "sex": SexType.MALE,
        "birth_date": date(1980, 1, 1),
        "height_cm": 175.0,
        "weight_kg": 75.0,
        "units_preference": UnitsPreference.METRIC,
    },
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
    # ── New athletes ──
    {
        "email": "raul.herrera@demo.com",
        "name": "Raúl Herrera",
        "role": UserRole.ATHLETE,
        "sex": SexType.MALE,
        "birth_date": date(1989, 3, 8),
        "height_cm": 181.0,
        "weight_kg": 86.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "lucia.romero@demo.com",
        "name": "Lucía Romero",
        "role": UserRole.ATHLETE,
        "sex": SexType.FEMALE,
        "birth_date": date(1999, 7, 19),
        "height_cm": 167.0,
        "weight_kg": 59.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "marcos.gil@demo.com",
        "name": "Marcos Gil",
        "role": UserRole.ATHLETE,
        "sex": SexType.MALE,
        "birth_date": date(1995, 11, 25),
        "height_cm": 174.0,
        "weight_kg": 77.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "isabel.vega@demo.com",
        "name": "Isabel Vega",
        "role": UserRole.ATHLETE,
        "sex": SexType.FEMALE,
        "birth_date": date(2001, 4, 2),
        "height_cm": 162.0,
        "weight_kg": 54.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "adrian.ramos@demo.com",
        "name": "Adrián Ramos",
        "role": UserRole.ATHLETE,
        "sex": SexType.MALE,
        "birth_date": date(1990, 8, 14),
        "height_cm": 179.0,
        "weight_kg": 84.0,
        "units_preference": UnitsPreference.IMPERIAL,
    },
    {
        "email": "clara.mendez@demo.com",
        "name": "Clara Méndez",
        "role": UserRole.ATHLETE,
        "sex": SexType.FEMALE,
        "birth_date": date(1997, 1, 30),
        "height_cm": 169.0,
        "weight_kg": 61.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "fernando.ortiz@demo.com",
        "name": "Fernando Ortiz",
        "role": UserRole.ATHLETE,
        "sex": SexType.MALE,
        "birth_date": date(1993, 6, 11),
        "height_cm": 188.0,
        "weight_kg": 95.0,
        "units_preference": UnitsPreference.METRIC,
    },
    {
        "email": "natalia.blanco@demo.com",
        "name": "Natalia Blanco",
        "role": UserRole.ATHLETE,
        "sex": SexType.FEMALE,
        "birth_date": date(2000, 9, 22),
        "height_cm": 164.0,
        "weight_kg": 56.0,
        "units_preference": UnitsPreference.METRIC,
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Coach-Athlete relationships
# Each tuple: (coach_email, athlete_email)
# ──────────────────────────────────────────────────────────────────────────────

COACH_ATHLETE_PAIRS: list[tuple[str, str]] = [
    # Luis coaches 6 athletes
    ("coach.luis@demo.com", "ana.lopez@demo.com"),
    ("coach.luis@demo.com", "carlos.ruiz@demo.com"),
    ("coach.luis@demo.com", "sofia.torres@demo.com"),
    ("coach.luis@demo.com", "david.moreno@demo.com"),
    ("coach.luis@demo.com", "raul.herrera@demo.com"),
    ("coach.luis@demo.com", "fernando.ortiz@demo.com"),
    # Marta coaches 5 athletes
    ("coach.marta@demo.com", "laura.jimenez@demo.com"),
    ("coach.marta@demo.com", "pablo.sanchez@demo.com"),
    ("coach.marta@demo.com", "elena.navarro@demo.com"),
    ("coach.marta@demo.com", "lucia.romero@demo.com"),
    ("coach.marta@demo.com", "clara.mendez@demo.com"),
    # Pedro coaches 4 athletes
    ("coach.pedro@demo.com", "jorge.diaz@demo.com"),
    ("coach.pedro@demo.com", "maria.castro@demo.com"),
    ("coach.pedro@demo.com", "marcos.gil@demo.com"),
    ("coach.pedro@demo.com", "isabel.vega@demo.com"),
    ("coach.pedro@demo.com", "adrian.ramos@demo.com"),
    ("coach.pedro@demo.com", "natalia.blanco@demo.com"),
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
    ("CrossFit Volcán", "raul.herrera@demo.com", "member", "active"),
    ("CrossFit Volcán", "fernando.ortiz@demo.com", "member", "active"),
    ("CrossFit Volcán", "natalia.blanco@demo.com", "member", "pending"),

    # Olimpia Training Lab — Marta owns, Pedro also coaches
    ("Olimpia Training Lab", "coach.marta@demo.com", "admin", "active"),
    ("Olimpia Training Lab", "coach.pedro@demo.com", "coach", "active"),
    ("Olimpia Training Lab", "laura.jimenez@demo.com", "member", "active"),
    ("Olimpia Training Lab", "elena.navarro@demo.com", "member", "active"),
    ("Olimpia Training Lab", "jorge.diaz@demo.com", "member", "active"),
    ("Olimpia Training Lab", "ana.lopez@demo.com", "member", "active"),  # Ana in 2 centers
    ("Olimpia Training Lab", "lucia.romero@demo.com", "member", "active"),
    ("Olimpia Training Lab", "clara.mendez@demo.com", "member", "active"),
    ("Olimpia Training Lab", "marcos.gil@demo.com", "member", "pending"),

    # The Garage Fitness — Pedro owns
    ("The Garage Fitness", "coach.pedro@demo.com", "admin", "active"),
    ("The Garage Fitness", "jorge.diaz@demo.com", "member", "active"),
    ("The Garage Fitness", "maria.castro@demo.com", "member", "active"),
    ("The Garage Fitness", "david.moreno@demo.com", "member", "pending"),
    ("The Garage Fitness", "isabel.vega@demo.com", "member", "active"),
    ("The Garage Fitness", "adrian.ramos@demo.com", "member", "active"),
    ("The Garage Fitness", "marcos.gil@demo.com", "member", "active"),
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
    # ── NutriForce — Productos canjeables con XP ──
    {
        "company_name": "NutriForce",
        "name": "Whey Protein Isolate 2 kg",
        "description": "Proteína de suero aislada, 90 % pureza, sabor chocolate. Canjea tus XP por una unidad gratis.",
        "item_type": "product",
        "xp_cost": 1500,
        "external_url": "https://nutriforce.es/whey-isolate",
    },
    {
        "company_name": "NutriForce",
        "name": "Creatina Monohidrato 500 g",
        "description": "Creatina micronizada, 100 servicios. Consíguela gratis con tus puntos de entrenamiento.",
        "item_type": "product",
        "xp_cost": 800,
        "external_url": "https://nutriforce.es/creatina",
    },
    {
        "company_name": "NutriForce",
        "name": "Multivitamínico Atleta 90 caps",
        "description": "Fórmula completa con vitaminas y minerales para deportistas.",
        "item_type": "product",
        "xp_cost": 600,
        "external_url": "https://nutriforce.es/multi",
    },
    {
        "company_name": "NutriForce",
        "name": "Pre-Workout Volcano 300 g",
        "description": "Pre-entreno con cafeína, beta-alanina y citrulina. Sabor sandía.",
        "item_type": "product",
        "xp_cost": 1000,
        "external_url": "https://nutriforce.es/preworkout",
    },
    # ── NutriForce — Descuentos ──
    {
        "company_name": "NutriForce",
        "name": "10 % dto. en tu próximo pedido NutriForce",
        "description": "Canjea tus XP por un cupón de descuento del 10 % aplicable a cualquier pedido en nutriforce.es.",
        "item_type": "discount",
        "xp_cost": 300,
        "discount_pct": 10.0,
        "external_url": "https://nutriforce.es",
    },
    {
        "company_name": "NutriForce",
        "name": "20 % dto. en suplementación NutriForce",
        "description": "Descuento exclusivo del 20 % para atletas con alto nivel de XP.",
        "item_type": "discount",
        "xp_cost": 700,
        "discount_pct": 20.0,
        "external_url": "https://nutriforce.es",
    },
    # ── Titan Gear — Productos canjeables con XP ──
    {
        "company_name": "Titan Gear",
        "name": "Rodilleras 7 mm Neopreno (par)",
        "description": "Rodilleras de competición, soporte máximo para sentadilla y cleans.",
        "item_type": "product",
        "xp_cost": 1200,
        "external_url": "https://titangear.com/rodilleras",
    },
    {
        "company_name": "Titan Gear",
        "name": "Calleras Grips Pro",
        "description": "Calleras de fibra de carbono para pull-ups y muscle-ups.",
        "item_type": "product",
        "xp_cost": 900,
        "external_url": "https://titangear.com/grips",
    },
    {
        "company_name": "Titan Gear",
        "name": "Muñequeras WOD Wrap",
        "description": "Muñequeras de 45 cm con velcro reforzado.",
        "item_type": "product",
        "xp_cost": 500,
        "external_url": "https://titangear.com/wrist-wraps",
    },
    # ── Titan Gear — Descuentos ──
    {
        "company_name": "Titan Gear",
        "name": "15 % dto. en Cinturón Lever 10 mm",
        "description": "Consigue un 15 % de descuento en el cinturón de halterofilia con cierre lever, cuero genuino.",
        "item_type": "discount",
        "xp_cost": 500,
        "discount_pct": 15.0,
        "external_url": "https://titangear.com/cinturon",
    },
    {
        "company_name": "Titan Gear",
        "name": "10 % dto. en toda la colección Titan Gear",
        "description": "Descuento del 10 % aplicable a cualquier producto de la tienda titangear.com.",
        "item_type": "discount",
        "xp_cost": 400,
        "discount_pct": 10.0,
        "external_url": "https://titangear.com",
    },
    # ── WOD Snacks — Productos canjeables con XP ──
    {
        "company_name": "WOD Snacks",
        "name": "Barrita Energética Cacao & Avena (12 uds)",
        "description": "Barritas naturales con avena, cacao y miel. Sin aditivos.",
        "item_type": "product",
        "xp_cost": 700,
        "external_url": "https://wodsnacks.es/barrita-cacao",
    },
    {
        "company_name": "WOD Snacks",
        "name": "Mix Frutos Secos Athlete 500 g",
        "description": "Mezcla de almendras, nueces, anacardos y arándanos.",
        "item_type": "product",
        "xp_cost": 400,
        "external_url": "https://wodsnacks.es/mix-frutos",
    },
    # ── WOD Snacks — Descuentos ──
    {
        "company_name": "WOD Snacks",
        "name": "Pack WOD Snacks gratis con 25 % dto.",
        "description": "Canjea 600 XP por un 25 % de descuento en cualquier pack de WOD Snacks.",
        "item_type": "discount",
        "xp_cost": 600,
        "discount_pct": 25.0,
        "external_url": "https://wodsnacks.es",
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
        "event_type": "competition",
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
        "event_type": "workshop",
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
        "event_type": "open_day",
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
        "event_type": "seminar",
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
        "event_type": "competition",
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
        "event_type": "competition",
        "center_name": "The Garage Fitness",
        "company_name": None,
    },
    # ── New events for richer calendar ──
    {
        "name": "Exhibición de Halterofilia Barcelona",
        "description": "Demostración abierta de levantamientos olímpicos con atletas invitados.",
        "event_date": _NOW + timedelta(days=5),
        "end_date": _NOW + timedelta(days=5, hours=4),
        "location": "Olimpia Training Lab, Av. Olímpica 15, Barcelona",
        "capacity": 50,
        "status": "published",
        "is_public": True,
        "event_type": "exhibition",
        "center_name": "Olimpia Training Lab",
        "company_name": None,
    },
    {
        "name": "Afterwork Social — Volcán",
        "description": "Entreno informal + cervezas post-WOD. Abierto a amigos y familia.",
        "event_date": _NOW + timedelta(days=3),
        "end_date": _NOW + timedelta(days=3, hours=3),
        "location": "CrossFit Volcán, Calle de la Energía 42, Madrid",
        "capacity": 30,
        "status": "published",
        "is_public": True,
        "event_type": "social",
        "center_name": "CrossFit Volcán",
        "company_name": None,
    },
    {
        "name": "Seminario Nutrición para Atletas",
        "description": "Charla sobre periodización nutricional, hidratación y suplementación.",
        "event_date": _NOW + timedelta(days=10),
        "end_date": _NOW + timedelta(days=10, hours=2),
        "location": "Online (Zoom)",
        "capacity": 200,
        "status": "published",
        "is_public": True,
        "event_type": "seminar",
        "center_name": None,
        "company_name": "NutriForce",
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
    ("WOD Solidario CrossFit Volcán", "raul.herrera@demo.com"),
    ("WOD Solidario CrossFit Volcán", "fernando.ortiz@demo.com"),
    # Clínica de Snatch (only center members)
    ("Clínica de Snatch — Nivel Intermedio", "laura.jimenez@demo.com"),
    ("Clínica de Snatch — Nivel Intermedio", "elena.navarro@demo.com"),
    ("Clínica de Snatch — Nivel Intermedio", "jorge.diaz@demo.com"),
    ("Clínica de Snatch — Nivel Intermedio", "ana.lopez@demo.com"),
    ("Clínica de Snatch — Nivel Intermedio", "lucia.romero@demo.com"),
    ("Clínica de Snatch — Nivel Intermedio", "clara.mendez@demo.com"),
    # Open Day
    ("Open Day — The Garage Fitness", "jorge.diaz@demo.com"),
    ("Open Day — The Garage Fitness", "maria.castro@demo.com"),
    ("Open Day — The Garage Fitness", "pablo.sanchez@demo.com"),
    ("Open Day — The Garage Fitness", "isabel.vega@demo.com"),
    ("Open Day — The Garage Fitness", "adrian.ramos@demo.com"),
    ("Open Day — The Garage Fitness", "marcos.gil@demo.com"),
    # NutriForce Summit
    ("NutriForce Athlete Summit 2026", "coach.marta@demo.com"),
    ("NutriForce Athlete Summit 2026", "coach.luis@demo.com"),
    ("NutriForce Athlete Summit 2026", "ana.lopez@demo.com"),
    ("NutriForce Athlete Summit 2026", "carlos.ruiz@demo.com"),
    ("NutriForce Athlete Summit 2026", "elena.navarro@demo.com"),
    ("NutriForce Athlete Summit 2026", "raul.herrera@demo.com"),
    ("NutriForce Athlete Summit 2026", "natalia.blanco@demo.com"),
    # Throwdown (past — attended)
    ("Throwdown Interbox Madrid 2026", "ana.lopez@demo.com"),
    ("Throwdown Interbox Madrid 2026", "carlos.ruiz@demo.com"),
    ("Throwdown Interbox Madrid 2026", "sofia.torres@demo.com"),
    ("Throwdown Interbox Madrid 2026", "david.moreno@demo.com"),
    ("Throwdown Interbox Madrid 2026", "jorge.diaz@demo.com"),
    ("Throwdown Interbox Madrid 2026", "maria.castro@demo.com"),
    ("Throwdown Interbox Madrid 2026", "coach.pedro@demo.com"),
    ("Throwdown Interbox Madrid 2026", "coach.luis@demo.com"),
    ("Throwdown Interbox Madrid 2026", "fernando.ortiz@demo.com"),
    ("Throwdown Interbox Madrid 2026", "adrian.ramos@demo.com"),
    ("Throwdown Interbox Madrid 2026", "marcos.gil@demo.com"),
    ("Throwdown Interbox Madrid 2026", "isabel.vega@demo.com"),
    # Exhibición Halterofilia
    ("Exhibición de Halterofilia Barcelona", "ana.lopez@demo.com"),
    ("Exhibición de Halterofilia Barcelona", "laura.jimenez@demo.com"),
    ("Exhibición de Halterofilia Barcelona", "elena.navarro@demo.com"),
    ("Exhibición de Halterofilia Barcelona", "coach.marta@demo.com"),
    # Afterwork Social
    ("Afterwork Social — Volcán", "ana.lopez@demo.com"),
    ("Afterwork Social — Volcán", "carlos.ruiz@demo.com"),
    ("Afterwork Social — Volcán", "sofia.torres@demo.com"),
    ("Afterwork Social — Volcán", "coach.luis@demo.com"),
    ("Afterwork Social — Volcán", "raul.herrera@demo.com"),
    # Seminario Nutrición
    ("Seminario Nutrición para Atletas", "ana.lopez@demo.com"),
    ("Seminario Nutrición para Atletas", "carlos.ruiz@demo.com"),
    ("Seminario Nutrición para Atletas", "david.moreno@demo.com"),
    ("Seminario Nutrición para Atletas", "laura.jimenez@demo.com"),
    ("Seminario Nutrición para Atletas", "elena.navarro@demo.com"),
]
