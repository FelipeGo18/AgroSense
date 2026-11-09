# AgroSense · Siembra Segura

Herramienta web de apoyo a la decisión para agricultores (región piloto en Colombia, por confirmar con el enunciado del reto y la sede) que, con observaciones de la Tierra de la NASA, el suelo local, las características de los cultivos y las prioridades del agricultor, ayuda a explorar estrategias de rotación que cuiden el suelo y adapten la finca a condiciones que cambian. El flujo del MVP:

1. **Estrategias de rotación:** para un lote (o un municipio y un área, sin cuenta), planes de hasta 3 ciclos que cumplen las reglas agronómicas, comparados por agua, suelo, ingreso y riesgo según las prioridades del agricultor, con cinco criterios de salud del suelo por reglas con fuente (nitrógeno, carbono orgánico, cobertura, corte de plagas y erosión) y comparados contra la rotación que el agricultor ya hace. Es una comparación, no una predicción de cuánto mejora el suelo.
2. **Diagnóstico de cada ciclo:** ¿conviene sembrar este cultivo en esta fecha? (primero, si el cultivo se da en la zona; luego, un semáforo con seis señales: agua, heladas, calor, suelo, oferta y mercado; cada señal calificada de 0 a 100; si las prioridades del agricultor dan otra luz que las de AgroSense, se muestran las dos; y las ventanas de siembra del año ordenadas primero por el factor que más limita y después por las prioridades). También se puede consultar suelto.
3. **Agua del plan:** cuánta agua necesitará cada ciclo y en qué meses la lluvia no alcanza (estimación).
4. **Qué cambió:** cómo se movieron las heladas, la lluvia, el calor y las mejores ventanas entre dos periodos de la historia de la zona. Es historia comparada, nunca pronóstico.

La oferta es valor agregado, no protagonista: es una de las seis señales y entra a las estrategias solo por el criterio de ingreso.

Proyecto para el **NASA Space Apps Challenge 2026** (reto «Field Shift: Adapting Farms with NASA Data»; el texto oficial está en `specs/00-vision.md`). Equipo: RealE4Life. Hackatón: 14 y 15 de noviembre de 2026. Fase 0 (preparación): 10 de octubre al 13 de noviembre.

## Estado actual

Hay código de la web (`web/`: inicio, entrar, crear cuenta, Mi cuenta, Mi finca con el mapa de lotes y las siembras y cosechas), de las cuentas y los lotes (`backend/`: esquema, migraciones y la API de cuenta, sesión, lotes y temporadas), del catálogo agronómico (`catalog/crops.yaml`, con fuente por valor) y del pipeline (`pipeline/`: municipios y límites de DIVIPOLA, catálogo, `sources` y el manifiesto). El contrato está congelado (decisión 15): su esquema en código está en `pipeline/schema.py`, hay un dataset de ejemplo en `data/examples/` y los endpoints de cálculo ya tienen su forma y sus ejemplos, pero responden `501` hasta que exista su parte del motor (`backend/engine/` solo tiene las etapas por calendario). No inventes comandos, archivos ni módulos que no existan: si algo falta, créalo según la spec o pregunta.

**Excepción de la fase 0: el frontend y las cuentas.** Desde el 12 de octubre de 2026 también se adelanta el backend de las cuentas (`backend/`, PostgreSQL en Docker y migraciones de Alembic: `backend/README.md`). Identidad visual, animaciones, audio, assets 3D y un prototipo navegable se adelantan ahora en `web/` y en Figma (EP-15, `specs/05-frontend.md`). La app de la demo se construye en el evento en un repositorio nuevo. Todo lo de diseño y frontend (pantallas, HUs de web, estilo, stack de la web) se puede rediseñar. Un cambio que toque las reglas R1–R10 o el contrato de la API se registra en `docs/decisiones.md` y se refleja en `specs/01-reglas.md` y `specs/02-contratos.md`.

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
- **Calcular no es guardar:** hay cuentas con lotes y temporadas en PostgreSQL propio (en Docker), con autenticación propia, pero los endpoints de cálculo no guardan los datos de la finca ni quién consultó. En el P0 no escriben nada en la base de datos; desde HU-170 (P1) solo suman 1 a un contador anónimo de uso (día, tipo, municipio y cultivo) para las métricas. Sin cuenta, los datos de la finca se envían solo para calcular y no se guardan.
- **El agricultor pondera; el riesgo grave no se negocia:** cada señal se califica de 0 a 100 con una curva por cultivo (estilo EcoCrop de la FAO); el agricultor pone un peso de 0 a 5 por señal; agua, heladas o calor críticos cuentan siempre; si las luces difieren se muestran las dos. La decisión final es del agricultor.
- **Varias fuentes, ninguna única verdad:** las fuentes de un indicador se muestran juntas y nunca se mezclan; `sources.yaml` dice cuál calcula cada señal por región. La región es un supuesto hasta el enunciado del 28 de octubre.
- **La NASA en el núcleo y las estrategias en el centro (decisión 12):** cada producto de la NASA entra por su adaptador (POWER ampliado, NASADEM, IMERG, MODIS NDVI, SMAP y capas GIBS) y `sources.yaml` dice cuál calcula cada señal; POWER es un reanálisis y se rotula así. El producto gira sobre las estrategias de rotación.
- **El clima en vivo es ambiente (P1):** la escena refleja día, noche, lluvia y viento aproximados de ahora (Open-Meteo); nunca entra al motor ni cambia un resultado.

Detalle en `docs/decisiones.md`. Las decisiones puntuales (servicios, estilo, alcance) con su fecha están en `docs/registro-de-decisiones.md`.

## Stack

Python 3.12 con `uv` · Polars · GeoPandas/Shapely · FastAPI + Pydantic v2 · PostgreSQL con SQLAlchemy 2 + Alembic · autenticación propia (Argon2 y sesión en cookie) · pytest · Ruff. Pruebas siempre en Docker. Web: React + TypeScript + Vite, React Router, Tailwind + Radix con estilo propio, React Three Fiber + drei, GSAP + Lenis, Zustand, TanStack Query, MSW, `openapi-typescript`, gráficas en SVG propio, Howler.js (P1). Datos en Parquet con `manifest.json`. Docker Compose con la imagen de la app y PostgreSQL. Backlog en GitHub Projects. Detalle y alternativas descartadas en `specs/04-stack.md`.

## Estructura prevista del repositorio

```
AgroSense/
├── CLAUDE.md  AGENTS.md  README.md
├── .claude/agents/          # un agente por rol
├── specs/                   # fuente de verdad de qué construir
├── docs/                    # contexto, decisiones, plan, riesgos
├── pipeline/                # D1–D4: adaptadores, validación, indicadores, publicación
│   ├── sources/             # nasa_power, nasadem, imerg, modis_ndvi, smap, soilgrids, eva, sipsa, dane
│   └── build.py             # un comando reconstruye el dataset
├── catalog/                 # AG1–AG3: crops.yaml, rotation_rules.yaml, sources.yaml
├── backend/
│   ├── engine/              # M1–M5, M7, M10 y M11: Python puro, sin FastAPI
│   ├── api/                 # M6: rutas, modelos Pydantic, errores
│   ├── accounts/            # M8: usuarios, lotes, temporadas (PostgreSQL)
│   ├── conditions/          # M9: condiciones actuales con caché
│   └── config/              # thresholds.yaml, weights.yaml (versionados)
├── web/                     # W1–W10: React + Vite; src/api con tipos generados
├── data/
│   ├── raw/                 # caché de descargas (fuera de git)
│   └── published/           # Parquet + manifest.json de la versión de la demo
├── tests/                   # casos de referencia del motor, del contrato y de las cuentas
├── Dockerfile               # imagen de la app
└── docker-compose.yml       # app, db (PostgreSQL) y web (Node) para desarrollo y pruebas
```

Las carpetas de código se crean cuando se implemente su primera HU. No las crees vacías.

## Convenciones

- **Idioma:** textos de interfaz, documentación y mensajes de commit en español. Identificadores de código, columnas, endpoints y valores de contrato en inglés y `snake_case` (sin tildes), por ejemplo `municipality_id`, `frost_freq_pct`, `insufficient_data`.
- **Llave territorial:** el código oficial de la unidad territorial de la región; en la región piloto (Colombia), el DIVIPOLA de 5 dígitos (`municipality_id`). Nunca se une por nombre.
- **Ventanas de siembra:** la decisión se evalúa sobre una fecha de siembra más lo que dura el cultivo, no sobre semestres. El semestre (A es enero–junio y B es julio–diciembre, por confirmar en HU-001) solo existe en la oferta de EVA.
- **Datos de ejemplo:** se rotulan como ejemplo en los archivos y en la interfaz.
- **Fuentes:** cada fila de datos y cada regla agronómica apunta a una entrada de la tabla `sources`.
- **Tamaños de HU:** S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona.

## Comandos previstos

Los de las cuentas, la web y el pipeline ya existen (`backend/README.md`, `web/README.md` y `pipeline/README.md`). La convención acordada es:

```bash
# Desarrollo
docker compose up -d db                       # PostgreSQL local para las cuentas
uv sync                                       # entorno Python reproducible
uv run python -m pipeline.build               # reconstruye data/published desde la caché (--descargar baja las fuentes)
npm --prefix web run dev                      # web; con VITE_SIMULATION=true usa respuestas simuladas

# Pruebas y lint: siempre en Docker
docker compose run --rm app uv run pytest     # motor, contrato y cuentas, contra el PostgreSQL de Compose
docker compose run --rm app uv run ruff check .
docker compose run --rm web npm test          # Vitest
```

## Lo que nunca se hace

- Presentar un resultado como pronóstico de rendimiento, precio o clima; tampoco «Qué cambió», que es historia comparada.
- Presentar la salud del suelo de una estrategia como una predicción de cuánto mejora el suelo: es una comparación por reglas.
- Presentar NASA POWER como una observación directa de satélite: es un reanálisis.
- Usar el clima en vivo para calcular un resultado (decisión 7).
- Rellenar, promediar o sustituir en silencio una fuente que falta (R1).
- Promediar señales para decidir el semáforo, dejar que el promedio de una ventana compense una señal crítica, o que un peso 0 esconda un riesgo grave de clima (R2).
- Mezclar o promediar en silencio las fuentes de un mismo indicador.
- Importar FastAPI o leer archivos dentro del motor (R6).
- Guardar datos de la finca sin cuenta ni consentimiento, o desde un endpoint de cálculo (R9).
- Añadir una regla agronómica o un dato sin fuente (R8).
- Mostrar datos ficticios sin rotularlos como ejemplo (R5).
- Decir que el riego o el suelo son una medición del lote (R10).
- Dibujar un botón o control sin función.

## Web: reglas que valen para todo lo nuevo

Al crear o cambiar cualquier pantalla, vista o componente de `web/`, lea `web/CLAUDE.md` y aplíquelo sin que nadie lo pida:

- **Modo ligero (HU-158):** todo lo que se mueve (GSAP, scroll suave, animaciones, transiciones, la Tierra, la mascota) debe poder quedarse quieto con la misma información. Se pregunta `useAnimated()` o se usa la variante `animated:`; nunca se decide movimiento por cuenta propia.
- **Diseño adaptable (HU-096):** reglas globales desde 320 px (`container-page`, `grid-cols-1` en la base, anchos fijos con su versión angosta, `min-h-svh`, sin scroll horizontal, objetivos táctiles de 44 px).
- Una pantalla nueva no está hecha hasta que se ve completa en modo ligero y pasa `npm run test:responsive` con su ruta agregada.

## Qué se puede recortar y qué no

Orden de recorte si hay retraso en la hora 34 (detalle en `docs/plan-48h.md`): todo el P1 (con el NDVI por lote, que pasó a P1 en la decisión 15); la capa GIBS del mapa; SMAP (el reto lo nombra primero: decisión 14); el suelo por lote (queda el del municipio); el agua del plan solo con año normal; una sola razón por estrategia; pruebas de CI a mano; como último recurso, las cuentas (la demo queda en modo sin cuenta). **Nunca se recorta:** los estados «datos insuficientes», «no evaluable» y «no aplica», el suelo de la zona y las heladas en el diagnóstico y las estrategias, al menos un producto de observación satelital de la NASA en el núcleo (POWER, NASADEM e IMERG no se recortan), los casos de referencia del motor, el consentimiento y el borrado de la cuenta si hay cuentas, el despliegue y el video de respaldo, y las citas de fuentes en la entrega.

## Agentes

Hay un agente por rol en `.claude/agents/`. El catálogo y cuándo usar cada uno está en `AGENTS.md`.
