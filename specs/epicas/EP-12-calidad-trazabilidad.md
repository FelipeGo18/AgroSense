---
id: EP-12
titulo: "Calidad y trazabilidad"
prioridad: P0
fase: [Hora 0, Evento]
rol: "Calidad, con Datos"
agentes: [calidad, datos]
subsistemas: [S3, D4]
depende_de: [HU-011]
reglas: [R4, R8]
estado: pendiente
---

# EP-12 · Calidad y trazabilidad

**Resultado esperado:** El equipo puede demostrar que cada resultado es correcto, reproducible y trazable a sus fuentes.

Empieza en la hora 0 con los casos de referencia y se cierra al final del evento.

## Historias de usuario

### HU-121 · Casos de referencia del motor

- **Historia:** Como equipo, quiero casos de referencia con resultado esperado escrito antes de programar, para saber si el motor acierta.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] De 5 a 8 combinaciones, incluidos verde, rojo y «no evaluable»
  - [ ] Automatizados en pytest y corriendo en Docker, en local y en CI

### HU-122 · Procedencia de cada dato

- **Historia:** Como jurado, quiero saber de dónde sale cada dato, para confiar en el resultado.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Manifiesto con versión, fuentes y cobertura
  - [ ] La web muestra fuentes y versión

### HU-123 · Reconstruir el dataset con un comando

- **Historia:** Como equipo, quiero reconstruir el dataset con un comando, para repetir la demo con los mismos datos.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Un comando regenera `data/published` desde la caché
  - [ ] El resultado coincide con el manifiesto
