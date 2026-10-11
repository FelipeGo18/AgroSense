# AgroSense · Siembra Segura

Herramienta web para agricultores colombianos que responde tres preguntas con datos abiertos y reglas explicables:

1. **Diagnóstico de ventana:** ¿es buen semestre para sembrar este cultivo en este municipio? (semáforo con cinco señales: lluvia, heladas, suelo, oferta y mercado).
2. **Rotaciones:** ¿qué sembrar después? (ranking de secuencias agronómicamente válidas, con el suelo de la zona o del lote y abonos verdes).
3. **Finca, calendario y plan de agua:** ¿en qué mes conviene sembrar, cuándo hay riesgo de helada, cuánta agua necesitará cada cultivo y en qué meses es probable regar? (estimación).

Proyecto para el **NASA Space Apps Challenge 2026** (reto «Cambio de rumbo: adaptando las granjas con datos de la NASA»). Equipo: Kode Group. Hackatón: 14 y 15 de noviembre de 2026. Fase 0 (preparación): 10 de octubre al 13 de noviembre.

## Estado actual

Solo hay especificaciones. **Todavía no hay código.** No inventes comandos, archivos ni módulos que no existan: si algo falta, créalo según la spec o pregunta.

**Excepción de la fase 0: el frontend.** Identidad visual, animaciones, audio, assets 3D y un prototipo navegable se adelantan ahora en `web/` y en Figma (EP-15, `specs/05-frontend.md`). La app de la demo se construye en el evento en un repositorio nuevo. Todo lo de diseño y frontend (pantallas, HUs de web, estilo, stack de la web) se puede rediseñar. Un cambio que toque las reglas R1–R10 o el contrato de la API se registra en `docs/decisiones.md` y se refleja en `specs/01-reglas.md` y `specs/02-contratos.md`.

## Cómo trabajamos: primero la spec

Todo cambio parte de una historia de usuario (HU) escrita en `specs/epicas/`.

1. Lee la HU, su épica y las reglas que aplican (`specs/01-reglas.md`).
2. Si la HU es ambigua o contradice una regla, **corrige la spec primero** y luego el código.
3. Un cambio de código corresponde a una HU. Menciona su código (por ejemplo `HU-074`) en el commit y en el PR.
4. Cuando termines, marca los criterios de aceptación en el archivo de la épica, actualiza el estado y refleja el cambio en `specs/BACKLOG.md`.
5. **Haider y Felipe son los responsables del contrato** (`specs/02-contratos.md`): lo cambia uno de los dos o aprueba cada cambio. Avísales antes, porque un cambio de contrato rompe el trabajo en paralelo.

Mapa de documentos:

| Qué buscas | Dónde |
|---|---|
| Problema, alcance P0/P1, impacto | `specs/00-vision.md` |
| Reglas de diseño R1–R10 y semáforo | `specs/01-reglas.md` |
| Tablas, endpoints, errores, JSON | `specs/02-contratos.md` |
| Sistemas y subsistemas (D, AG, M, W, S) | `specs/03-sistemas.md` |
| Stack y por qué | `specs/04-stack.md` |
| Visión, estilo y stack del frontend | `specs/05-frontend.md` |
| Épicas e historias de usuario | `specs/epicas/` y `specs/BACKLOG.md` |
| Plantillas para escribir HUs | `specs/_plantilla-epica.md`, `specs/_plantilla-hu.md` |
| Glosario, decisiones, registro de decisiones, plan de 48 h, riesgos | `docs/` |

@specs/01-reglas.md

## Decisiones de arquitectura (resumen)

- **Monolito modular:** un backend en Python. El motor de decisión es un módulo puro (sin FastAPI ni lectura de archivos); la API es una capa delgada encima.
- **Contratos primero:** el esquema de datos y el OpenAPI se congelan al inicio. La web trabaja contra respuestas simuladas hasta que exista el motor real.
- **Datos precalculados:** el pipeline corre antes de la demo y publica Parquet versionado. Para calcular, la API solo lee y aplica reglas.
- **Reglas, no predicción:** no hay modelo de aprendizaje automático. Se entrega riesgo histórico explicable, no rendimiento ni precio futuro.
- **Sin datos no hay señal:** si falta una fuente, la señal es `insufficient_data` con nivel nulo. Nunca se rellena ni se sustituye en silencio.
- **Calcular no es guardar:** hay cuentas con lotes y temporadas en PostgreSQL propio (en Docker), con autenticación propia, pero los endpoints de cálculo no guardan nada. Sin cuenta, nada sale del dispositivo.
- **El clima en vivo es ambiente:** la escena refleja día, noche, lluvia y viento aproximados de ahora (Open-Meteo); nunca entra al motor ni cambia un resultado.

Detalle en `docs/decisiones.md`. Las decisiones puntuales (servicios, estilo, alcance) con su fecha están en `docs/registro-de-decisiones.md`.

## Stack

Python 3.12 con `uv` · Polars · GeoPandas/Shapely · FastAPI + Pydantic v2 · PostgreSQL con SQLAlchemy 2 + Alembic · autenticación propia (Argon2 y sesión en cookie) · pytest · Ruff. Pruebas siempre en Docker. Web: React + TypeScript + Vite, Tailwind + Radix con estilo propio, React Three Fiber + drei, GSAP + Lenis, Zustand, TanStack Query, MSW, `openapi-typescript`, gráficas en SVG propio, Howler.js (P1). Datos en Parquet con `manifest.json`. Docker Compose con la imagen de la app y PostgreSQL. Backlog en GitHub Projects. Detalle y alternativas descartadas en `specs/04-stack.md`.

## Estructura prevista del repositorio

```
AgroSense/
├── CLAUDE.md  AGENTS.md  README.md
├── .claude/agents/          # un agente por rol
├── specs/                   # fuente de verdad de qué construir
├── docs/                    # contexto, decisiones, plan, riesgos
├── pipeline/                # D1–D4: adaptadores, validación, indicadores, publicación
│   ├── sources/             # nasa_power, eva, sipsa, dane
│   └── build.py             # un comando reconstruye el dataset
├── catalog/                 # AG1–AG3: crops.yaml, rotation_rules.yaml, sources.yaml
├── backend/
│   ├── engine/              # M1–M5: Python puro, sin FastAPI
│   ├── api/                 # M6: rutas, modelos Pydantic, errores
│   ├── accounts/            # M8: usuarios, lotes, temporadas (PostgreSQL)
│   ├── conditions/          # M9: condiciones actuales con caché
│   └── config/              # thresholds.yaml, weights.yaml (versionados)
├── web/                     # W1–W9: React + Vite; src/api con tipos generados
├── data/
│   ├── raw/                 # caché de descargas (fuera de git)
│   └── published/           # Parquet + manifest.json de la versión de la demo
├── tests/                   # casos de referencia del motor, del contrato y de las cuentas
├── Dockerfile               # imagen de la app
└── docker-compose.yml       # app, db (PostgreSQL) y web (Node) para desarrollo y pruebas
```

Las carpetas de código se crean cuando se implemente su primera HU. No las crees vacías.

## Convenciones

- **Idioma:** textos de interfaz, documentación y mensajes de commit en español. Identificadores de código, columnas, endpoints y valores de contrato en inglés y `snake_case` (sin tildes), por ejemplo `municipality_id`, `precip_anomaly_pct`, `insufficient_data`.
- **Llave territorial:** siempre el código DIVIPOLA de 5 dígitos (`municipality_id`). Nunca se une por nombre.
- **Semestres:** A es enero–junio y B es julio–diciembre (supuesto por confirmar en HU-001).
- **Datos de ejemplo:** se rotulan como ejemplo en los archivos y en la interfaz.
- **Fuentes:** cada fila de datos y cada regla agronómica apunta a una entrada de la tabla `sources`.
- **Tamaños de HU:** S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona.

## Comandos previstos

Aún no existen. Se definen en HU-021 y se documentan en el `README.md`. La convención acordada es:

```bash
# Desarrollo
docker compose up -d db                       # PostgreSQL local para las cuentas
uv sync                                       # entorno Python reproducible
uv run python -m pipeline.build               # reconstruye data/published desde la caché
npm --prefix web run dev                      # web; con VITE_SIMULATION=true usa respuestas simuladas

# Pruebas y lint: siempre en Docker
docker compose run --rm app uv run pytest     # motor, contrato y cuentas, contra el PostgreSQL de Compose
docker compose run --rm app uv run ruff check .
docker compose run --rm web npm test          # Vitest
```

## Lo que nunca se hace

- Presentar un resultado como pronóstico de rendimiento, precio o clima.
- Usar el clima en vivo para calcular un resultado (decisión 7).
- Rellenar, promediar o sustituir en silencio una fuente que falta (R1).
- Promediar señales para decidir el semáforo (R2).
- Importar FastAPI o leer archivos dentro del motor (R6).
- Guardar datos de la finca sin cuenta ni consentimiento, o desde un endpoint de cálculo (R9).
- Añadir una regla agronómica o un dato sin fuente (R8).
- Mostrar datos ficticios sin rotularlos como ejemplo (R5).
- Decir que el riego o el suelo son una medición del lote (R10).
- Dibujar un botón o control sin función.

## Qué se puede recortar y qué no

Orden de recorte si hay retraso en la hora 34 (detalle en `docs/plan-48h.md`): todo el P1; lluvia, nubes y viento en la escena (queda solo día y noche); progreso del lote; suelo por lote (queda el del municipio); vista del calendario (las heladas siguen en el diagnóstico); reducir HU-093 a una sola gráfica; plan de agua solo con año normal; explicaciones con una razón por opción; pruebas de CI a mano; como último recurso, las cuentas (la demo queda en modo sin cuenta). **Nunca se recorta:** los estados «datos insuficientes», «no evaluable» y «no aplica», el suelo de la zona y las heladas en el diagnóstico y las rotaciones, los casos de referencia del motor, el consentimiento y el borrado de la cuenta si hay cuentas, el despliegue y el video de respaldo, y las citas de fuentes en la entrega.

## Agentes

Hay un agente por rol en `.claude/agents/`. El catálogo y cuándo usar cada uno está en `AGENTS.md`.
