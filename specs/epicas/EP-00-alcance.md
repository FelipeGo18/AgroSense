---
id: EP-00
titulo: "Alcance piloto decidido con datos reales"
prioridad: P0
fase: [Fase 0]
rol: "Producto y agro, con Datos"
agentes: [producto-agro, datos]
subsistemas: [D1, AG1]
depende_de: [Enunciado del 28 de octubre]
reglas: [R7, R8]
estado: pendiente
---

# EP-00 · Alcance piloto decidido con datos reales

**Resultado esperado:** Región, cultivos, periodos y fuentes elegidos con base en la cobertura real comprobada.

**La región es un supuesto (decisión 11).** El reto aún no dice qué datos ni qué región. Colombia, y dentro de ella el altiplano de Cundinamarca o Boyacá, es la región piloto supuesta. El P0 sigue con ella hasta que el enunciado del 28 de octubre (HU-002) la confirme o la cambie. Mientras tanto, lo propio de Colombia (EVA, DIVIPOLA, SIPSA, IDEAM, UPRA, IGAC, Ley 1581) vive en los adaptadores de cada fuente y en `sources.yaml`, no en el modelo (R7).

## Historias de usuario

### HU-001 · Comparar la cobertura de EVA y elegir región

- **Historia:** Como equipo, quiero comparar la cobertura de EVA para papa y cultivos de rotación por municipio, para elegir una región con datos completos.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Tabla de cobertura por municipio y semestre desde 2019
  - [ ] Región elegida con justificación escrita
  - [ ] Lista de municipios habilitados

### HU-002 · Confirmar los datasets NASA del enunciado

- **Historia:** Como equipo, quiero confirmar los datasets NASA que propone el enunciado, para no construir sobre datos que no aplican.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Variables, resolución, periodo y forma de acceso documentados
  - [ ] Descarga de prueba para un municipio
  - [ ] Dice si el enunciado fija una región o unos datos. Si no es compatible con la región piloto supuesta, se registra en `docs/registro-de-decisiones.md` y se lista qué adaptadores y entradas de `sources.yaml` hay que cambiar
- **Notas:** El enunciado completo sale el 28 de octubre. Hasta entonces la región es un supuesto (decisión 11).

### HU-003 · Verificar SIPSA y decidir si entra al P0

- **Historia:** Como equipo, quiero verificar SIPSA (productos, mercados, frecuencia y última fecha), para decidir si la señal de mercado entra al P0.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Decisión «entra» o «no entra» documentada
  - [ ] Si entra, mapeo de producto SIPSA a `crop_id`

### HU-004 · Confirmar qué se puede preparar antes del evento

- **Historia:** Como equipo, quiero confirmar en los términos de 2026 y con el evento local qué se puede preparar antes, para no arriesgar la entrega.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Regla citada con enlace
  - [ ] Plan ajustado si cambia lo permitido
