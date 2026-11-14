# AgroSense · Siembra Segura

Herramienta web para agricultores (región piloto en Boyacá y Cundinamarca, Colombia; sede Duitama) que ayuda a explorar **estrategias de rotación** de hasta 3 ciclos: dice cómo cuida el suelo cada una, revisa cada ciclo con un diagnóstico de su ventana de siembra, estima el agua que necesitará y muestra qué cambió en el clima de la zona. Usa datos de la NASA (NASA POWER, NASADEM, GPM IMERG, MODIS NDVI, SMAP y las capas de GIBS), el suelo de SoilGrids, fichas de cultivo con fuente y reglas explicables; como valor agregado, la oferta de EVA/UPRA. Se puede usar sin cuenta; con cuenta, el agricultor dibuja sus lotes y guarda sus temporadas. Proyecto del **NASA Space Apps Challenge 2026** (sede Duitama), reto «Field Shift: Adapting Farms with NASA Data» (equipo RealE4Life).

Flujo del MVP: lote (o municipio y área, sin cuenta) → estrategias de rotación → un ciclo con su diagnóstico → agua del plan → qué cambió. Es historia de la zona y comparación según reglas con fuente: no predice el clima, el rendimiento ni cuánto mejora el suelo.

> **Estado:** fase 0 (preparación). Las specs son la fuente de verdad. Ya hay código de la web (`web/`), de las cuentas y los lotes (`backend/`) y del comienzo del pipeline (`pipeline/`: municipios de DIVIPOLA); el catálogo agronómico y el motor de decisión siguen en especificación.

## Por dónde empezar

1. Lee `specs/00-vision.md` para entender el reto oficial, cómo lo cubre el MVP, la idea y el alcance.
2. Revisa `specs/BACKLOG.md` para ver todas las historias de usuario.
3. Para el orden de trabajo, mira `docs/orden-de-desarrollo.md`; para las horas y el recorte, `docs/plan-48h.md`.
4. Si no entiendes un término, `docs/glosario.md`.

## Cómo correr el proyecto

Hay dos piezas: la **API** (Python, con su base de datos PostgreSQL) y la **web** (React). Lo normal es correr la API y
la base de datos con Docker y la web con Node.

### 1. Lo que hay que tener instalado

| Qué | Para qué | Versión |
|---|---|---|
| [Git](https://git-scm.com/) | Clonar el repositorio | Cualquiera reciente |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | La base de datos y la API | Abierto antes de empezar |
| [Node.js](https://nodejs.org/) | La web | 22 o más nueva |
| [uv](https://docs.astral.sh/uv/) (`pip install uv`) | Solo para crear migraciones o correr la API sin Docker | 0.13 o más nueva |

### 2. Clonar

```bash
git clone https://github.com/FelipeGo18/AgroSense.git
cd AgroSense
```

### 3. Los archivos `.env`

Los `.env` **no están en el repositorio** (git los ignora): cada quien crea los suyos a partir de los ejemplos.

```bash
cp .env.example .env
cp web/.env.example web/.env
```

| Archivo | Qué lleva | De dónde salen los valores |
|---|---|---|
| `.env` | La base de datos local (`POSTGRES_*`), el puerto de la API y el nivel de los logs | Se inventan: son de su máquina. Cambie `POSTGRES_PASSWORD` por una clave cualquiera. No hay que pedirle nada a nadie |
| `web/.env` | Las redes del pie de página (`VITE_SOCIAL_*`) y, si quiere, la música (`VITE_MUSIC_URL`) | Las direcciones de las redes se le piden a Felipe o a Haider. Sin ellas la web funciona igual: esa red no se dibuja |

Nunca suba un `.env` ni pegue su contenido en un chat público. Si agrega una variable nueva, agréguela también al
`.env.example` correspondiente, sin su valor.

### 4. Levantar la base de datos y la API

Con Docker Desktop abierto, desde la raíz:

```bash
docker compose up --build app
```

Ese comando levanta PostgreSQL, espera a que esté listo, aplica las migraciones (con una copia de seguridad antes) y
deja la API en `http://127.0.0.1:8000`. La documentación de los endpoints queda en `http://127.0.0.1:8000/api/docs` (solo en desarrollo, con
`AGROSENSE_API_DOCS=true`, que Compose ya enciende).

Para comprobar que está arriba:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### 5. Levantar la web

En otra terminal:

```bash
npm --prefix web install      # solo la primera vez, o cuando cambie package.json
npm --prefix web run dev
```

Abra **`http://localhost:5173`**. Tiene que ser esa dirección: la API solo acepta cambios que vengan de ese origen.

### Comandos del día a día

| Comando | Qué hace |
|---|---|
| `docker compose up --build app` | Levanta la base y la API con el código actual. Use `--build` después de un `git pull` o de cambiar el backend: la imagen lleva el código copiado dentro |
| `docker compose up -d db` | Solo la base de datos, en segundo plano |
| `docker compose up --no-deps app` | Solo la API, sin base de datos (las cuentas responden 503; lo demás funciona) |
| `docker compose logs -f app` | Ver los logs de la API |
| `docker compose down` | Apaga todo y **conserva** los datos |
| `docker compose down -v` | Apaga todo y **borra** la base de datos local |
| `docker compose run --rm app uv run pytest` | Pruebas del backend |
| `docker compose run --rm app uv run ruff check .` | Lint del backend |
| `npm --prefix web test` | Pruebas de la web |
| `npm --prefix web run typecheck` · `lint` · `format:check` | Tipos, lint y formato de la web |
| `npm --prefix web run build` | Compila la web |

### Si cambia la base de datos

Crear la migración es a mano; aplicarla la hace Docker al arrancar (detalle y reglas en `backend/README.md`):

```bash
uv sync                                                  # una vez
uv run python -m backend.db.revision "lo que cambia"     # crea la migración con su número
docker compose up --build app                            # copia la base y la aplica
```

### Si un puerto está ocupado

| Puerto | Quién lo usa | Cómo cambiarlo |
|---|---|---|
| 5432 | PostgreSQL | `POSTGRES_PORT=5433` en `.env` |
| 8000 | La API | `API_PORT=8010` en `.env`, y la misma dirección en `proxy` de `web/vite.config.ts` |
| 5173 | La web | Cierre lo que lo esté usando: la API solo acepta ese origen (o agregue el otro a `WEB_ORIGINS` en `.env`) |

### Sin Docker

Se puede, pero hay que instalar y configurar PostgreSQL a mano.

1. **Instale PostgreSQL 17** y deje sus herramientas (`psql`, `pg_dump`) en el `PATH`. `pg_dump` hace la copia de
   seguridad antes de cada migración: sin él no se puede migrar.
2. **Cree el usuario y la base de datos** con los mismos nombres de su `.env`:
   ```bash
   psql -U postgres -c "create user agrosense with password 'la-clave-de-su-env' createdb"
   psql -U postgres -c "create database agrosense owner agrosense"
   ```
   `createdb` hace falta para que las pruebas creen su propia base (`agrosense_test`).
3. **Revise el `.env`**: `POSTGRES_HOST=127.0.0.1` y `POSTGRES_PORT` con el puerto de su PostgreSQL (5432 por defecto).
4. **Instale las dependencias de Python y prepare la base:**
   ```bash
   uv sync
   uv run python -m backend.db.migrate
   ```
5. **Levante la API:**
   ```bash
   uv run uvicorn backend.api.main:app --reload --port 8000 --no-access-log
   ```
6. **Levante la web** igual que con Docker (paso 5 de arriba).

Pruebas y lint sin Docker: `uv run pytest` y `uv run ruff check .`. Antes de abrir un PR córralas también en Docker,
que es el entorno que comparte todo el equipo.

Si su terminal no reconoce `uv`, use `python -m uv` en su lugar.

En el caso en el que la terminal activa no reconozca el servicio de PostgreSQL aunque esté levantada la base de datos local, es conveniente reiniciar la sesión de esa terminal. La salida al preparar la base de datos (paso 4) debe ser que está al día.

## Estructura

```
AgroSense/
├── CLAUDE.md          # reglas del proyecto para Claude Code
├── AGENTS.md          # catálogo de agentes y reglas de convivencia
├── .claude/agents/    # un agente por rol
├── specs/             # qué se construye y por qué
│   └── epicas/        # una épica por archivo, con sus HUs
├── docs/              # glosario, decisiones, plan de 48 h, riesgos
├── design/            # generadores de pantallas, kit, mascota y tokens (fuente del diseño)
├── web/               # la web: React + Vite (web/README.md)
├── backend/           # API, cuentas y migraciones de la base de datos (backend/README.md)
├── common/            # lo que comparten el backend y el pipeline sin importarse (la configuración de los logs)
├── tests/             # pruebas del backend (pytest, en Docker)
└── docker-compose.yml # PostgreSQL y la API para desarrollo y pruebas
```

## Trabajar con Claude Code

Abre el repositorio en Claude Code. `CLAUDE.md` se carga solo. Pide el trabajo por HU y, si quieres, nombra el agente:

```
usa el agente especificador para afinar los criterios de HU-074
usa el agente motor-api para implementar HU-074
```

## Licencias

El código es Apache 2.0 (`LICENSE`). La licencia de cada dato y librería de terceros está en `docs/licencias.md`.

## Reglas esenciales

Diez reglas de diseño (R1–R10) en `specs/01-reglas.md`. Una HU que viole una regla no se acepta, aunque funcione.
