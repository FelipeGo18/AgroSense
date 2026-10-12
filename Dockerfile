# Imagen de la app: la API con sus dependencias. Sirve para desarrollo, para las pruebas y, más adelante, para la demo.
#
#   docker compose run --rm app uv run pytest         # pruebas, contra el PostgreSQL de Compose
#   docker compose up app                             # aplica las migraciones y deja la API en http://localhost:8000
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/

# `pg_dump`: antes de cada migración se hace una copia de seguridad de la base de datos.
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# El entorno vive fuera de /app: en desarrollo el código se monta encima y no debe tapar las dependencias.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_NO_SYNC=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Primero solo las dependencias: esta capa se reutiliza mientras no cambie uv.lock.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY alembic.ini ./
COPY backend ./backend
COPY tests ./tests

# Sin privilegios dentro del contenedor.
RUN useradd --create-home agrosense && mkdir -p /app/backups && chown -R agrosense /app
USER agrosense

EXPOSE 8000
# Al arrancar se intenta copiar la base de datos y aplicar las migraciones pendientes; después sube la API, siempre.
# Si la base no responde, o la copia o una migración fallan, queda escrito en el log y las cuentas se apagan (503);
# lo que no usa la base de datos sigue funcionando.
CMD ["sh", "-c", "python -m backend.db.migrate --al-arrancar; exec uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
