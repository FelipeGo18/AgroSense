# Imagen de la app: la API con sus dependencias. Sirve para desarrollo, para las pruebas y, más adelante, para la demo.
#
#   docker compose run --rm app uv run pytest         # pruebas, contra el PostgreSQL de Compose
#   docker compose up app                             # aplica las migraciones y deja la API en http://localhost:8000
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/

# `pg_dump`: antes de cada migración se hace una copia de seguridad de la base de datos. `tzdata`: los crons de precios
# corren en la hora de Bogotá (TZ=America/Bogota). `curl`: para bajar supercronic, aquí abajo.
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client tzdata curl && rm -rf /var/lib/apt/lists/*

# Supercronic, el cron para contenedores: corre las actualizaciones de precios del servicio `market` (HU-222). Versión y
# suma SHA-1 fijas, las que publica su página de versiones (https://github.com/aptible/supercronic/releases/tag/v0.2.51).
ARG TARGETARCH=amd64
ARG SUPERCRONIC_VERSION=v0.2.51
# La descarga se reintenta: GitHub a veces corta la conexión a mitad.
RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) sha1=1692066e350a88ff4d7d6474fe3c7a6c41ec5e89 ;; \
      arm64) sha1=9d4c2000493215a1898502b2fc2dada3e8ea8c7a ;; \
      *) echo "No hay supercronic para $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL --retry 5 --retry-all-errors --retry-delay 3 -o /usr/local/bin/supercronic \
      "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH}"; \
    echo "$sha1  /usr/local/bin/supercronic" | sha1sum -c -; \
    chmod +x /usr/local/bin/supercronic

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
COPY common ./common
COPY backend ./backend
COPY pipeline ./pipeline
# El catálogo agronómico con fuentes (EP-06): el pipeline lo valida y lo publica.
COPY catalog ./catalog
# El dataset publicado por el pipeline: la API solo lo lee (AGROSENSE_DATA_DIR).
COPY data/published ./data/published
# Los datos de ejemplo del contrato (HU-011): los usan las pruebas y el desarrollo del motor.
COPY data/examples ./data/examples
# El contrato: las pruebas comparan el esquema en código con él (HU-011).
COPY specs/02-contratos.md ./specs/02-contratos.md
# El revisor de los nombres de ramas y commits (HU-022): las pruebas lo cargan.
COPY scripts ./scripts
COPY tests ./tests

# Sin privilegios dentro del contenedor.
# data/market: las versiones de precios que dejan los crons del servicio `market` (HU-222); el volumen de Compose
# hereda este dueño.
RUN useradd --create-home agrosense && mkdir -p /app/backups /app/data/market && chown -R agrosense /app
USER agrosense

EXPOSE 8000
# Al arrancar se intenta copiar la base de datos y aplicar las migraciones pendientes; después sube la API, siempre.
# Si la base no responde, o la copia o una migración fallan, queda escrito en el log y las cuentas se apagan (503);
# lo que no usa la base de datos sigue funcionando.
CMD ["sh", "-c", "python -m backend.db.migrate --al-arrancar; exec uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
