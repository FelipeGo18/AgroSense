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

**SIPSA verificado el 20 de octubre de 2026 (insumo de HU-003):** el servicio web del DANE (SOAP 1.2, operación `promediosSipsaParcial`) responde sin cuenta y trae el precio mínimo, medio y máximo por kilo de cada producto, central y día desde el 1 de febrero de 2020 (unos 300 MB). Corabastos tiene 36 productos y Tunja 33, con datos hasta el día anterior. La decisión de si la señal `market` entra al P0 sigue siendo de HU-003.

SIPSA es de Colombia: es la fuente supuesta para la región piloto (decisión 11). Si la región cambia, `sources.yaml` dice qué fuente de precios calcula la señal `market` en la nueva región. Con varias fuentes de precios, se muestran juntas y nunca se mezclan.

## Historias de usuario

### HU-051 · Índice estacional de precio

- **Historia:** Como agricultor, quiero saber si el precio suele estar bajo en el mes en que saldría la cosecha de mi ventana de siembra, para evitar vender barato.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Precio mensual por producto y central
  - [ ] Índice estacional documentado
  - [ ] Mapeo de producto a cultivo revisado
  - [ ] Entrada de SIPSA en `sources` con `coverage` (mercados y país que cubre)

### HU-221 · Precios en la central de abastos

- **Historia:** Como agricultor de Boyacá, quiero ver a cuánto se paga hoy por kilo cada producto en Corabastos y en Tunja, cómo se movió en el último año y en qué meses suele estar más caro o más barato, para decidir qué sembrar y cuándo vender.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** hecha (falta aprobar el contrato y el diseño)
- **Notas:** Es lo que pasó en la central, nunca un pronóstico de precio (decisión 4): la pantalla lo dice. Los productos van con el nombre del DANE; el mapeo a `crop_id` es de HU-051, cuando exista el catálogo. Es la base de la que saldrá `market_month` (HU-051).
- **Criterios de aceptación:**
  - [x] Adaptador `pipeline/sources/sipsa.py`: baja la respuesta del servicio a `data/raw/sipsa/` y publica solo las centrales de `region.yaml` (Corabastos y Tunja)
  - [x] Tabla `market_price_day` (producto, central, día; mínimo, medio y máximo en pesos enteros por kilo). Un 0 o un vacío del DANE es nulo, nunca un precio (R1); un día sin precio medio no se publica
  - [x] Tabla `market_price_season`: índice estacional por producto, central y mes, que compara cada mes con el promedio de su mismo año (así no cuenta la inflación); solo con 3 o más años completos. Sin ellos no hay temporada (R1)
  - [x] Validaciones antes de publicar: llave sin repetir, precio medio presente y dentro del mínimo y el máximo (con un peso de tolerancia por el redondeo del DANE), fuente en `sources` (R8)
  - [x] `GET /api/v1/market/prices` y `GET /api/v1/market/prices/{product_id}`, sin base de datos ni guardar nada (R9)
  - [x] Pantalla `/precios`, sin cuenta: central, búsqueda, último precio con su cambio frente a hace una semana (con forma y texto) y, al abrir un producto, su último año y su temporada, con el rótulo «No es un pronóstico» y la fuente
  - [x] Modo ligero y diseño adaptable de 320 a 1920 px (`npm run test:responsive`)
  - [ ] Contrato aprobado por Haider o Felipe (`specs/02-contratos.md`)
  - [x] Generador `design/pantallas/precios.py` con sus SVG (escritorio, móvil y producto abierto en móvil), con cifras reales de SIPSA
  - [ ] Láminas enviadas a Figma y aprobadas (la pantalla se programó antes del diseño, por pedido del equipo)
  - [ ] Licencia de SIPSA verificada en los términos y condiciones del DANE
