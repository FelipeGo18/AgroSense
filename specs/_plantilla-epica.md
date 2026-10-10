# Plantilla de épica

Copia esta plantilla a `specs/epicas/EP-XX-nombre-corto.md`. Una épica se define por **resultado**, no por componente.

```markdown
---
id: EP-XX
titulo: "Título orientado al resultado"
prioridad: P0
fase: [Evento]
rol: "Rol responsable, con roles de apoyo"
agentes: [nombre-del-agente]
subsistemas: [M1, W2]
depende_de: [EP-00, HU-011]
reglas: [R1, R5]
estado: pendiente
---

# EP-XX · Título

**Resultado esperado:** una frase que describe qué puede hacer el equipo o el usuario cuando la épica está completa.

Contexto opcional: condiciones, cómo arranca, qué se hace en cada fase.

## Historias de usuario

(Una sección por HU, según `specs/_plantilla-hu.md`.)
```

## Campos de la cabecera

La cabecera (frontmatter) es la única fuente de estos datos: no se repiten en el cuerpo. GitHub la muestra como tabla.

| Campo | Valores |
|---|---|
| `prioridad` | `P0` o `P1` |
| `fase` | Lista con `Fase 0` (antes del evento), `Hora 0` (arranque del evento) y `Evento` |
| `rol` | Rol responsable y, si hay, roles de apoyo |
| `agentes` | Agentes de `.claude/agents/`, el principal primero |
| `subsistemas` | Códigos de `specs/03-sistemas.md` |
| `depende_de` | Épicas, HUs o hitos externos; `[]` si no depende de nada |
| `reglas` | Reglas de `specs/01-reglas.md`; `[]` si ninguna aplica |
| `estado` | `pendiente`, `en curso`, `en revisión` o `hecha` |

Tamaños de HU: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona.

## Lista de verificación de una épica

- [ ] El resultado se puede demostrar, no solo «se hizo el trabajo».
- [ ] Las dependencias no son circulares.
- [ ] Cada HU cabe en una persona en menos de un día de evento.
- [ ] Declara qué reglas R1–R10 aplican.
- [ ] Está listada en `specs/BACKLOG.md` con todas sus HUs.
