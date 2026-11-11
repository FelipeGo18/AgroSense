#!/usr/bin/env bash
# HU-022: Lint, pruebas y build del repo.
#
# Se ejecuta dentro de la caja de pruebas (Dockerfile.test) a través del servicio `test` de docker-compose.yml.
#   docker compose run --rm test
# El workflow .github/workflows/ci.yml corre ese mismo comando, así que local y CI no pueden divergir.

# Sin `-e` a propósito: si un paso falla, los demás siguen corriendo y se ven todos los fallos de una vez.
# `-u`: error si se usa una variable sin definir. `pipefail`: un fallo dentro de una tubería cuenta como fallo.
set -uo pipefail

# Lista de nombres de los pasos que fallaron. Se imprime al final si no está vacía. Si está vacía, todo está en orden.
fallos=()

# paso "Nombre" comando...: imprime un título para ubicarse en el log, corre el comando y,
# si termina con error, anota el nombre en `fallos`.
paso() {
  local nombre="$1"; shift
  echo "=== $nombre ==="
  "$@" || fallos+=("$nombre")
}

paso "Ruff"   uv run ruff check . # linter de Python: revisa el código sin ejecutarlo
paso "Pytest" uv run pytest       # backend, contrato y cuentas; usa la base `db` de Compose
# `npm ci` instala exactamente lo del package-lock.json. Si las pruebas de Vitest fallan, el build no corre
# (van con &&), pero el paso "Web" completo queda marcado como fallido.
paso "Web"    sh -c "cd web && npm ci && npm test && npm run build"

# El código de salida es lo que lee GitHub: 0 = check verde, distinto de 0 = X roja.
if [ ${#fallos[@]} -gt 0 ]; then
  echo "=== Fallaron los siguientes pasos ==="
  printf '%s\n' "${fallos[@]}"
  exit 1
fi
echo "==== Todo en orden ===="