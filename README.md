# AgroSense · Siembra Segura

Herramienta web para agricultores (región piloto en Colombia, por confirmar con el enunciado del reto): dice si un cultivo se da en la zona y cuándo conviene sembrarlo, recomienda rotaciones de cultivos y estima el plan de agua de la finca, con datos abiertos (NASA POWER, SoilGrids, EVA/UPRA, SIPSA) y reglas explicables. Se puede usar sin cuenta; con cuenta, el agricultor guarda sus lotes, su historial y su progreso. Proyecto del **NASA Space Apps Challenge 2026** (equipo RealE4Life).

> **Estado:** fase de especificación. Todavía no hay código del producto; las specs son la fuente de verdad. En la fase 0 se adelanta la identidad visual y un prototipo del frontend en `web/` (EP-15).

## Por dónde empezar

1. Lee `specs/00-vision.md` para entender el problema, la idea y el alcance.
2. Revisa `specs/BACKLOG.md` para ver todas las historias de usuario.
3. Para el orden de trabajo, mira `docs/orden-de-desarrollo.md`.
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
