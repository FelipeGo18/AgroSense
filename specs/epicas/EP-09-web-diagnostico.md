---
id: EP-09
titulo: "Diagnóstico usable en la web"
prioridad: P0
fase: [Evento]
rol: "Web"
agentes: [web]
subsistemas: [W1, W2, W3, W6]
depende_de: [HU-012, HU-013, EP-07]
reglas: [R1, R5]
estado: pendiente
---

# EP-09 · Diagnóstico usable en la web

**Resultado esperado:** Un agricultor elige su contexto desde el celular y entiende el diagnóstico sin ayuda.

Arranca contra las respuestas simuladas (HU-013) y se integra con EP-07.

## Historias de usuario

### HU-091 · Elegir municipio, cultivo y semestre

- **Historia:** Como agricultor, quiero elegir municipio, cultivo y semestre entre opciones válidas, para no equivocarme.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Buscador de municipios con autocompletado
  - [ ] Solo opciones del catálogo
  - [ ] Validación inmediata en pantalla
- **Notas:** El municipio se busca en el nivel «satélite» del descenso (`specs/05-frontend.md`).

### HU-092 · Semáforo con señales, razones y limitaciones

- **Historia:** Como agricultor, quiero ver el semáforo con sus señales, razones y limitaciones, para entender el resultado.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] «Desfavorable» y «no evaluable» se distinguen con forma y texto, no solo con color
  - [ ] La acción sugerida es lo primero que se lee
  - [ ] Las cinco señales (lluvia, heladas, suelo, oferta y mercado); «No aplica» se ve distinto de «datos insuficientes»
  - [ ] El suelo lleva su rango y el rótulo de estimación (R10)

### HU-093 · Gráficas de lluvia y área sembrada

- **Historia:** Como agricultor, quiero ver la lluvia frente a lo normal y el área sembrada en el tiempo, para ver la tendencia con mis ojos.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Dos gráficas con unidades y periodo visibles
  - [ ] Se marca el semestre consultado

### HU-094 · Estados de carga, vacío y error

- **Historia:** Como usuario, quiero mensajes claros cuando algo carga, falla o no tiene datos, para saber qué hacer.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Estados de carga, vacío, sin cobertura y error
  - [ ] Los datos de ejemplo se rotulan

### HU-095 · Mapa regional por semáforo

- **Historia:** Como agricultor, quiero ver la región en un mapa coloreado por semáforo, para comparar mi zona con las vecinas.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] GeoJSON propio de la región, sin mapa base externo
  - [ ] Clic en un municipio lo selecciona
- **Notas:** Se dibuja en el nivel «región» de la escena 3D (`specs/05-frontend.md`). En modo ligero, una lista de municipios con su estado en forma y texto.

### HU-096 · Uso desde el celular

- **Historia:** Como agricultor, quiero usar la herramienta desde el celular, porque es lo que tengo en el campo.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Usable a 360 px de ancho sin desplazamiento horizontal
