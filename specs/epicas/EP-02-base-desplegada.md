---
id: EP-02
titulo: "Base del proyecto desplegada"
prioridad: P0
fase: [Hora 0]
rol: "Plataforma (Motor y API si el equipo es de 4)"
agentes: [plataforma]
subsistemas: [S1, S2]
depende_de: []
reglas: []
estado: pendiente
---

# EP-02 · Base del proyecto desplegada

**Resultado esperado:** Cualquier integrante arranca el proyecto en minutos, y la URL pública existe desde las primeras horas.

## Historias de usuario

### HU-021 · Clonar y ejecutar con pocos comandos

- **Historia:** Como integrante, quiero clonar y ejecutar todo con pocos comandos, para no perder tiempo configurando.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] README de arranque probado por otra persona
  - [ ] Estructura del repositorio acordada

### HU-022 · Lint y pruebas automáticas en cada cambio

- **Historia:** Como equipo, quiero lint y pruebas automáticas en cada cambio, para detectar roturas temprano.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] GitHub Actions corre Ruff, pytest, Vitest y el build web dentro de Docker Compose
  - [ ] Las mismas pruebas corren en local con un solo comando de Docker

### HU-023 · Esqueleto desplegado en URL pública

- **Historia:** Como equipo, quiero el esqueleto desplegado, para que el despliegue no sea un riesgo al final.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Un contenedor sirve API y web en una URL pública
  - [ ] `/api/v1/version` responde
  - [ ] Docker Compose levanta la app y PostgreSQL con volumen persistente; credenciales en variables de entorno, ningún secreto en el repositorio
