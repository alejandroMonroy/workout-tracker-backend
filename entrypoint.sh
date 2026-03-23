#!/bin/sh
set -e

echo "⏳ Ejecutando migraciones de base de datos..."
alembic upgrade head

if [ "$RUN_SEEDS" = "true" ]; then
    echo "🌱 Ejecutando seeds..."
    python -m app.seeds.run
fi

echo "🚀 Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 ${UVICORN_EXTRA_ARGS:-}
