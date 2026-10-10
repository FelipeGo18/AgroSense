# AgroSense · Siembra Segura

Herramienta web para agricultores colombianos: diagnostica si un semestre es buena ventana de siembra, recomienda rotaciones de cultivos y estima el plan de agua de la finca, con datos abiertos (NASA POWER, EVA/UPRA, SIPSA) y reglas explicables. Proyecto del **NASA Space Apps Challenge 2026** (Kode Group).

> **Estado:** fase de especificación. Todavía no hay código; las specs son la fuente de verdad.

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
└── docs/              # glosario, decisiones, plan de 48 h, riesgos
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
