---
id: EP-05
titulo: "Señal de mercado con datos reales"
prioridad: P1
fase: [Evento]
rol: "Datos"
agentes: [datos]
subsistemas: [D1, D2, D3, D4]
depende_de: [HU-003]
reglas: [R1, R7, R8]
estado: pendiente
---

# EP-05 · Señal de mercado con datos reales

**Resultado esperado:** La tabla `market_month` con índice estacional de precio.

Condicionada a HU-003: solo entra si SIPSA cubre la región; si no, el P0 cubre la ausencia con HU-073.

## Historias de usuario

### HU-051 · Índice estacional de precio

- **Historia:** Como agricultor, quiero saber si el precio suele bajar cuando sale la cosecha de mi ventana, para evitar vender barato.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Precio mensual por producto y central
  - [ ] Índice estacional documentado
  - [ ] Mapeo de producto a cultivo revisado
