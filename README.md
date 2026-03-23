# Workout Tracker — Backend

API REST para el registro y seguimiento de entrenamientos, construida con **FastAPI**, **SQLAlchemy 2** (async) y **PostgreSQL**.

## Requisitos

- Python 3.12+
- PostgreSQL 17+
- Docker y Docker Compose (opcional)

## Inicio rápido

### Con Docker Compose

```bash
# Copia el archivo de variables de entorno
cp .env.example .env

# Levanta la base de datos y el backend
docker compose up -d

# Ejecuta las migraciones
docker compose exec backend alembic upgrade head

# Ejecuta el seed de ejercicios (opcional)
docker compose exec backend python -m app.seeds.run
```

La API estará disponible en `http://localhost:8000`.

### Sin Docker (desarrollo local)

```bash
# Crea un entorno virtual
python -m venv .venv
source .venv/bin/activate

# Instala dependencias
pip install -r requirements.txt

# Copia y configura las variables de entorno
cp .env.example .env

# Ejecuta las migraciones
alembic upgrade head

# Ejecuta el seed de ejercicios (opcional)
python -m app.seeds.run

# Inicia el servidor
uvicorn app.main:app --reload
```

## Estructura del proyecto

```
├── alembic/              # Migraciones de base de datos
├── app/
│   ├── api/              # Endpoints de la API
│   │   └── endpoints/
│   ├── core/             # Configuración, seguridad, DB
│   ├── models/           # Modelos SQLAlchemy
│   ├── schemas/          # Schemas Pydantic
│   ├── seeds/            # Datos iniciales
│   └── services/         # Lógica de negocio
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── alembic.ini
```

## API Docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Variables de entorno

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `DATABASE_URL` | URL de conexión a PostgreSQL | — |
| `SECRET_KEY` | Clave secreta para JWT | — |
| `ALGORITHM` | Algoritmo de firma JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración del access token (min) | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Expiración del refresh token (días) | `7` |
