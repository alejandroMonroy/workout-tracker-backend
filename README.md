# Workout Tracker — Backend

API REST para el registro y seguimiento de entrenamientos, construida con **FastAPI**, **SQLAlchemy 2** (async) y **PostgreSQL**.

## Requisitos

- Python 3.12+
- PostgreSQL 17+
- Docker y Docker Compose (opcional)

## Inicio rápido

### Con Docker Compose

```bash
# Copia el archivo de variables de entorno y configúralo
cp .env.example .env

# Construye y levanta todos los servicios (DB + backend)
# Las migraciones se ejecutan automáticamente al iniciar
docker compose up -d --build

# (Opcional) Ejecuta los seeds de ejercicios en el primer despliegue
docker compose run --rm -e RUN_SEEDS=true backend

# Ver logs del backend
docker compose logs -f backend
```

Para ejecutar los seeds automáticamente en cada inicio, agrega `RUN_SEEDS=true` a tu `.env`.

#### Comandos útiles

```bash
# Detener los servicios
docker compose down

# Detener y eliminar volúmenes (⚠️ borra datos de la DB)
docker compose down -v

# Reconstruir la imagen tras cambios en el código
docker compose up -d --build

# Ejecutar migraciones manualmente
docker compose exec backend alembic upgrade head

# Crear una nueva migración
docker compose exec backend alembic revision --autogenerate -m "descripción"
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
