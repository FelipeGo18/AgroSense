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
  - [x] Cada producto NASA que recomiende el enunciado y no esté en el MVP (POWER, NASADEM, IMERG, MODIS NDVI, SMAP, GIBS) queda listado con su HU nueva, que entra por su propio adaptador (decisión 12). **8 de noviembre de 2026 (decisión 14):** el enunciado sugiere SMAP, ECOSTRESS, GPM, Landsat, MODIS, NASA POWER, GRACE y GRACE-FO, y SRTM u otro modelo de elevación (y nombra GEDI como ejemplo). Faltaban GRACE-FO (HU-225) y ECOSTRESS (HU-226); Landsat sigue en HU-043 (HLS); GEDI no entra
  - [ ] Revisar la pestaña de recursos del reto el viernes 13 de noviembre, cuando se publica, y agregar lo que traiga
  - [ ] La sede del equipo queda confirmada. Si es Moquegua (Perú, según la imagen del reto local) u otra fuera de Colombia, se decide por escrito si la región piloto sigue en el altiplano colombiano o pasa a la región de la sede, y se registra en `docs/registro-de-decisiones.md` con la lista de adaptadores (oferta, límites, código territorial) que cambiarían
- **Notas:** El enunciado completo sale el 28 de octubre. Hasta entonces la región es un supuesto (decisión 11). El reto local de la sede de Moquegua dice: «Crea una herramienta que combine datos satelitales, suelo y cultivos para ayudar a los agricultores a tomar mejores decisiones» (`specs/00-vision.md`). Que esa sea la sede del equipo es un supuesto por confirmar. Criterios de los productos NASA y de la sede agregados el 11 de octubre de 2026.

### HU-003 · Verificar SIPSA y decidir si entra al P0

- **Historia:** Como equipo, quiero verificar SIPSA (productos, mercados, frecuencia y última fecha), para decidir si la señal de mercado entra al P0.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Decisión «entra» o «no entra» documentada
  - [ ] Si entra, mapeo de producto SIPSA a `crop_id`

### HU-004 · Confirmar qué se puede preparar antes del evento

- **Historia:** Como equipo, quiero confirmar en los términos de 2026 y con el evento local qué se puede preparar antes, para no arriesgar la entrega.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] Regla citada con enlace
  - [x] Respuesta escrita de la sede local sobre si se puede llevar código preparado (pipeline, motor, web) o solo diseños, guías y datos. **Sí se puede llevar código preparado:** confirmado por Felipe el 8 de noviembre de 2026
  - [x] Plan ajustado si cambia lo permitido (`docs/plan-48h.md`, los dos casos): aplica el escenario «Se puede llevar código y datos preparados»; el orden de recorte no se aplica desde el inicio
- **Notas:** **Urgente: se hace esta semana (antes del 17 de octubre de 2026).** Define todo el plan: si se puede llevar código, los datos NASA y las fichas llegan hechos al evento; si no, el P0 del evento supera de lejos las horas del equipo (`docs/plan-48h.md`). Marcada urgente el 11 de octubre de 2026.
