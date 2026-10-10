---
id: EP-12
titulo: "Calidad y trazabilidad"
prioridad: "P0"
fase: "En paralelo desde la hora 0"
rol: "Producto y agro (con Datos)"
agente: calidad
subsistemas: "S3, D4"
depende_de: "HU-011"
reglas: "R4, R8"
estado: pendiente
---

# EP-12 · Calidad y trazabilidad

**Resultado esperado:** El equipo puede demostrar que cada resultado es correcto, reproducible y trazable a sus fuentes.

| Campo | Valor |
|---|---|
| Prioridad | P0 |
| Fase | En paralelo desde la hora 0 |
| Rol responsable | Producto y agro (con Datos) |
| Agente sugerido | `calidad` (ver `.claude/agents/`) |
| Subsistemas | S3, D4 (ver `specs/03-sistemas.md`) |
| Depende de | HU-011 |
| Reglas de diseño que aplican | R4, R8 (ver `specs/01-reglas.md`) |

Tamaños: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. Estados: `pendiente`, `en curso`, `en revisión`, `hecha`.

## Historias de usuario

### HU-121 · Casos de referencia del motor

- **Historia:** Como equipo, quiero casos de referencia con resultado esperado escrito antes de programar, para saber si el motor acierta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] De 5 a 8 combinaciones, incluidos verde, rojo y «no evaluable»
  - [ ] Automatizados en pytest y corriendo en CI
- **Notas:** —

### HU-122 · Procedencia de cada dato

- **Historia:** Como jurado, quiero saber de dónde sale cada dato, para confiar en el resultado.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Manifiesto con versión, fuentes y cobertura
  - [ ] La web muestra fuentes y versión
- **Notas:** —

### HU-123 · Reconstruir el dataset con un comando

- **Historia:** Como equipo, quiero reconstruir el dataset con un comando, para repetir la demo con los mismos datos.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Un comando regenera `data/published` desde la caché
  - [ ] El resultado coincide con el manifiesto
- **Notas:** —
