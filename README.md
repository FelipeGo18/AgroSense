# AgroSense · Siembra Segura

Herramienta web para agricultores (región piloto en Colombia, por confirmar con la sede y el enunciado del reto) que ayuda a explorar **estrategias de rotación** de hasta 3 ciclos: dice cómo cuida el suelo cada una, revisa cada ciclo con un diagnóstico de su ventana de siembra, estima el agua que necesitará y muestra qué cambió en el clima de la zona. Usa datos de la NASA (NASA POWER, NASADEM, GPM IMERG, MODIS NDVI, SMAP y las capas de GIBS), el suelo de SoilGrids, fichas de cultivo con fuente y reglas explicables; como valor agregado, la oferta de EVA/UPRA. Se puede usar sin cuenta; con cuenta, el agricultor dibuja sus lotes y guarda sus temporadas. Proyecto del **NASA Space Apps Challenge 2026**, reto «Field Shift: Adapting Farms with NASA Data» (equipo RealE4Life).

Flujo del MVP: lote (o municipio y área, sin cuenta) → estrategias de rotación → un ciclo con su diagnóstico → agua del plan → qué cambió. Es historia de la zona y comparación según reglas con fuente: no predice el clima, el rendimiento ni cuánto mejora el suelo.

> **Estado:** fase de especificación. Todavía no hay código del producto; las specs son la fuente de verdad. En la fase 0 se adelanta la identidad visual y un prototipo del frontend en `web/` (EP-15).

## Por dónde empezar

1. Lee `specs/00-vision.md` para entender el reto oficial, cómo lo cubre el MVP, la idea y el alcance.
2. Revisa `specs/BACKLOG.md` para ver todas las historias de usuario.
3. Para el orden de trabajo, mira `docs/orden-de-desarrollo.md`; para las horas y el recorte, `docs/plan-48h.md`.
4. Si no entiendes un término, `docs/glosario.md`.

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
└── web/               # prototipo del frontend de la fase 0 (EP-15)
```

## Trabajar con Claude Code

Abre el repositorio en Claude Code. `CLAUDE.md` se carga solo. Pide el trabajo por HU y, si quieres, nombra el agente:

```
usa el agente especificador para afinar los criterios de HU-074
usa el agente motor-api para implementar HU-074
```

Los comandos de arranque (`uv`, `pytest`, `npm`) se documentan aquí cuando exista el código (HU-021).

## Reglas esenciales

Diez reglas de diseño (R1–R10) en `specs/01-reglas.md`. Una HU que viole una regla no se acepta, aunque funcione.
