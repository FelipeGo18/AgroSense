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

**SIPSA verificado el 20 de octubre de 2026 (insumo de HU-003):** el servicio web del DANE (SOAP 1.2, operación `promediosSipsaParcial`) responde sin cuenta y trae el precio mínimo, medio y máximo por kilo de cada producto, central y día desde el 1 de febrero de 2020 (unos 300 MB). Corabastos tiene 36 productos y Tunja 33, con datos hasta el día anterior. El 7 de noviembre se cruzó con los 7 cultivos del MVP: cubre papa, arveja, cebolla de bulbo y zanahoria, y no publica haba ni maíz en grano (`pipeline/sipsa_crops.yaml`). La decisión de si la señal `market` entra al P0 sigue siendo de HU-003, que tiene la propuesta de Datos.

SIPSA es de Colombia y cubre las centrales de referencia de la región confirmada para la sede de Duitama (**Boyacá y Cundinamarca**, decisión 11, HU-002). Si se configura otra región, `sources.yaml` dice qué fuente de precios calcula la señal `market` en ella. Con varias fuentes de precios, se muestran juntas y nunca se mezclan.

## Historias de usuario

### HU-051 · Índice estacional de precio

- **Historia:** Como agricultor, quiero saber si el precio suele estar bajo en el mes en que saldría la cosecha de mi ventana de siembra, para evitar vender barato.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** en curso (falta `market_month`)
- **Criterios de aceptación:**
  - [ ] Precio mensual por producto y central
  - [x] Índice estacional documentado (`market_price_season` en `specs/02-contratos.md`, hecho en HU-221)
  - [ ] Mapeo de producto a cultivo revisado (propuesta de Datos en `pipeline/sipsa_crops.yaml`, HU-003; falta la revisión de Producto y agro)
  - [x] Entrada de SIPSA en `sources` con `coverage` (mercados y país que cubre), hecha en HU-221
- **Notas:** `market_month` se arma por `crop_id` con el producto que dice `pipeline/sipsa_crops.yaml`. Un cultivo sin producto no tiene filas (R1). `promediosSipsaParcial` no trae volumen: `volume_t` pide otra parte de SIPSA (el abastecimiento) o queda nulo (R1). Se decide con Haider o Felipe, porque toca el contrato.

### HU-221 · Precios en la central de abastos

- **Historia:** Como agricultor de Boyacá, quiero ver a cuánto se paga hoy por kilo cada producto en Corabastos y en Tunja, cómo se movió en el último año y en qué meses suele estar más caro o más barato, para decidir qué sembrar y cuándo vender.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** hecha (falta aprobar el contrato y el diseño)
- **Notas:** Es lo que pasó en la central, nunca un pronóstico de precio (decisión 4): la pantalla lo dice. Los productos van con el nombre del DANE; el mapeo a `crop_id` está en `pipeline/sipsa_crops.yaml` (HU-003). Es la base de la que saldrá `market_month` (HU-051).
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

### HU-222 · Precios al día

- **Historia:** Como agricultor, quiero que los precios de la central sean los del último día que publicó el DANE, sin que nadie tenga que volver a publicar el dataset, para decidir con el precio de hoy.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** hecha (falta aprobar el contrato)
- **Notas:** Es la excepción a «datos precalculados» que registra `docs/registro-de-decisiones.md` (20 de octubre de 2026): solo para los precios, que cambian cada día. Sigue siendo historia de precios, no pronóstico.
- **Criterios de aceptación:**
  - [x] Con `AGROSENSE_MARKET_REFRESH=true`, la API baja SIPSA al arrancar si lo que tiene es anterior a la última publicación y después cada día a las 3:00 p. m. de Bogotá (el DANE publica a las 2:00)
  - [x] Usa el mismo adaptador y las mismas validaciones del pipeline; cada descarga buena es una versión nueva e inmutable (`sipsa-AAAAMMDDTHHMM`) en `AGROSENSE_MARKET_DIR`, y se guardan las dos últimas
  - [x] Si la descarga o la validación fallan, se sigue sirviendo la última versión buena, el log dice por qué y se reintenta en una hora (R1)
  - [x] Una versión bajada solo se sirve si es igual o más nueva que lo publicado en `data/published`
  - [x] Las respuestas de `/market/*` dicen su `version` y su `updated_at` (R4); la pantalla dice cuándo se actualizaron
  - [x] La API sigue atendiendo mientras baja (otro hilo); las pruebas no usan la red
  - [ ] Contrato aprobado por Haider o Felipe
