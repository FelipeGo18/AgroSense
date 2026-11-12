#!/usr/bin/env bash
# HU-022: Lint, pruebas y build del repo.
#
# Se ejecuta dentro de la caja de pruebas (Dockerfile.test) a través del servicio `test` de docker-compose.yml:
#   docker compose run --rm test                         # todo
#   docker compose run --rm test bash scripts/test.sh python   # solo Python: Ruff, formato y pytest
#   docker compose run --rm test bash scripts/test.sh web      # solo la web: typecheck, lint, formato, Vitest y build
# El CI (.github/workflows/ci.yml) corre las dos partes en paralelo con este mismo script: los pasos son los mismos que
# en local.

# Sin `-e` a propósito: si un paso falla, los demás siguen corriendo y se ven todos los fallos de una vez.
# `-u`: error si se usa una variable sin definir. `pipefail`: un fallo dentro de una tubería cuenta como fallo.
set -uo pipefail

parte="${1:-todo}"
case "$parte" in
  todo | python | web) ;;
  *)
    echo "Uso: bash scripts/test.sh [todo|python|web]"
    exit 2
    ;;
esac

# Lista de nombres de los pasos que fallaron. Se imprime al final si no está vacía. Si está vacía, todo está en orden.
fallos=()

# paso "Nombre" comando...: imprime un título para ubicarse en el log, corre el comando y,
# si termina con error, anota el nombre en `fallos`.
paso() {
  local nombre="$1"; shift
  echo "=== $nombre ==="
  "$@" || fallos+=("$nombre")
}

if [ "$parte" != web ]; then
  paso "Ruff"         uv run ruff check .          # linter de Python: revisa el código sin ejecutarlo
  paso "Ruff formato" uv run ruff format --check .
  paso "Pytest"       uv run pytest                # backend, contrato y cuentas; usa la base `db` de Compose
fi
if [ "$parte" != python ]; then
  # `npm ci` instala exactamente lo del package-lock.json. Si las pruebas de Vitest fallan, el build no corre
  # (van con &&), pero el paso "Web" completo queda marcado como fallido.
  paso "Web" sh -c "cd web && npm ci && npm run typecheck && npm run lint && npm run format:check && npm test && npm run build"
fi

# El código de salida es lo que lee GitHub: 0 = check verde, distinto de 0 = X roja.
if [ ${#fallos[@]} -gt 0 ]; then
  echo "=== Fallaron los siguientes pasos ==="
  printf '%s\n' "${fallos[@]}"
  exit 1
fi
echo "==== Todo en orden ($parte) ===="
