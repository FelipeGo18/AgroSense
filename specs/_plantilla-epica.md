# Plantilla de épica

Copia esta plantilla a `specs/epicas/EP-XX-nombre-corto.md`. Una épica se define por **resultado**, no por componente.

```markdown
---
id: EP-XX
titulo: "Título orientado al resultado"
prioridad: "P0"
fase: "Fase 0 | Hora 0 | Evento"
rol: "Datos | Motor y API | Web | Producto y agro | Plataforma"
agente: nombre-del-agente
subsistemas: "D#, AG#, M#, W#, S#"
depende_de: "EP-## o HU-###"
reglas: "R#, R#"
estado: pendiente
---

# EP-XX · Título

**Resultado esperado:** una frase que describe qué puede hacer el equipo o el usuario cuando la épica está completa.

| Campo | Valor |
|---|---|
| Prioridad | |
| Fase | |
| Rol responsable | |
| Agente sugerido | |
| Subsistemas | |
| Depende de | |
| Reglas de diseño que aplican | |

## Historias de usuario

(Una sección por HU, según `specs/_plantilla-hu.md`.)
```

## Lista de verificación de una épica

- [ ] El resultado se puede demostrar, no solo «se hizo el trabajo».
- [ ] Las dependencias no son circulares.
- [ ] Cada HU cabe en una persona en menos de un día de evento.
- [ ] Declara qué reglas R1–R10 aplican.
- [ ] Está listada en `specs/BACKLOG.md` con todas sus HUs.
