#!/bin/bash
# La base de producción (HU-234): PostgreSQL 17 en la VM e2-micro. Corre en cada arranque y no cambia nada si ya está.
# La clave sale de Secret Manager (agrosense-db-password), nunca de los metadatos de la VM.
set -euo pipefail

SUBNET="10.10.0.0/24"
PG_VERSION=17

if ! command -v psql >/dev/null || [ ! -d "/etc/postgresql/${PG_VERSION}" ]; then
  apt-get update
  apt-get install -y --no-install-recommends postgresql-common ca-certificates curl gnupg
  # El repositorio oficial de PostgreSQL (Debian 12 trae la 15).
  /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
  apt-get install -y --no-install-recommends "postgresql-${PG_VERSION}"
fi

CONF="/etc/postgresql/${PG_VERSION}/main"
# Escucha en la red privada; solo con SSL y clave (scram) desde la subred de Cloud Run. Debian trae ssl = on con su
# certificado propio (snakeoil): la API pide sslmode=require.
sed -i "s/^#\?listen_addresses.*/listen_addresses = '*'/" "${CONF}/postgresql.conf"
grep -q "^ssl = on" "${CONF}/postgresql.conf" || echo "ssl = on" >> "${CONF}/postgresql.conf"
# Memoria de una e2-micro (1 GB).
grep -q "^shared_buffers = 128MB" "${CONF}/postgresql.conf" || echo "shared_buffers = 128MB" >> "${CONF}/postgresql.conf"
grep -q "^max_connections = 40" "${CONF}/postgresql.conf" || echo "max_connections = 40" >> "${CONF}/postgresql.conf"
RULE="hostssl agrosense agrosense ${SUBNET} scram-sha-256"
grep -qF "${RULE}" "${CONF}/pg_hba.conf" || echo "${RULE}" >> "${CONF}/pg_hba.conf"
systemctl restart postgresql

PASSWORD="$(gcloud secrets versions access latest --secret=agrosense-db-password)"
sudo -u postgres psql -v ON_ERROR_STOP=1 -v pw="${PASSWORD}" <<'SQL'
SELECT 'CREATE ROLE agrosense LOGIN' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'agrosense')\gexec
ALTER ROLE agrosense WITH LOGIN PASSWORD :'pw';
SELECT 'CREATE DATABASE agrosense OWNER agrosense' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agrosense')\gexec
SQL

# Copia diaria (HU-234), 7 días, en el disco de la VM.
mkdir -p /var/backups/agrosense
chown postgres /var/backups/agrosense
cat > /etc/cron.d/agrosense-backup <<'CRON'
30 3 * * * postgres pg_dump -Fc agrosense > /var/backups/agrosense/agrosense-$(date +\%F).dump && find /var/backups/agrosense -name '*.dump' -mtime +7 -delete
CRON
