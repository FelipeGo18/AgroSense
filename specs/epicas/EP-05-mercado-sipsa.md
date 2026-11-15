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
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Precio mensual por producto y central: `market_month` (`pipeline/sources/sipsa.py`, `monthly`), con el precio de cada mes del último año completo, publicada desde el dataset `2026.11.1`
  - [x] Índice estacional documentado (`market_price_season` y `market_month` en `specs/02-contratos.md`)
  - [x] Mapeo de producto a cultivo revisado (`pipeline/sipsa_crops.yaml`, HU-003): aprobado por Felipe el 10 de noviembre de 2026; el maíz queda sin producto (el chócolo es maíz tierno)
  - [x] Entrada de SIPSA en `sources` con `coverage` (mercados y país que cubre), hecha en HU-221
  - [x] Columnas de `market_month` aprobadas por Haider o Felipe (`specs/02-contratos.md`): aprobado por Felipe el 10 de noviembre de 2026
- **Notas:** `market_month` se arma por `crop_id` con el producto que dice `pipeline/sipsa_crops.yaml`: arveja, cebolla de bulbo y zanahoria en Corabastos y Tunja, y papa solo en Corabastos (84 filas). Un cultivo sin producto, o sin 3 años completos en una central, no tiene filas allí (R1). El precio de cada mes es el que se pagó en el último año completo (`price_year`), no un promedio entre años, que mezclaría la inflación. Al contrato se sumaron `product_id`, `price_year` y `years`, para saber de dónde y de qué año sale cada número (R4, R8). `promediosSipsaParcial` no trae volumen: `volume_t` va nulo (R1) hasta que se agregue el abastecimiento de SIPSA. Qué central usa la señal `market` de un municipio es de HU-073. Pruebas: `tests/pipeline/test_precio_mensual.py`.

### HU-221 · Precios en la central de abastos

- **Historia:** Como agricultor de Boyacá, quiero ver a cuánto se paga hoy por kilo cada producto en Corabastos y en Tunja, cómo se movió en el último año y en qué meses suele estar más caro o más barato, para decidir qué sembrar y cuándo vender.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** en curso (falta el diseño en Figma)
- **Notas:** Es lo que pasó en la central, nunca un pronóstico de precio (decisión 4): la pantalla lo dice. Los productos van con el nombre del DANE; el mapeo a `crop_id` está en `pipeline/sipsa_crops.yaml` (HU-003). Es la base de la que saldrá `market_month` (HU-051). **9 de noviembre de 2026 (segunda revisión de Felipe del PR #12):** las rutas `GET` solo traen datos. El último precio de cada producto, el de hace una semana, el cambio y el orden los calcula quien escribe los datos (el pipeline y cada actualización de precios) en la tabla `market_price_latest`; la ruta filtra y devuelve. La cita del DANE pasa a la columna `citation` de `sources`, para que la API no importe el pipeline.
- **Criterios de aceptación:**
  - [x] Adaptador `pipeline/sources/sipsa.py`: baja la respuesta del servicio a `data/raw/sipsa/` y publica solo las centrales de `region.yaml` (Corabastos y Tunja)
  - [x] Tabla `market_price_day` (producto, central, día; mínimo, medio y máximo en pesos enteros por kilo). Un 0 o un vacío del DANE es nulo, nunca un precio (R1); un día sin precio medio no se publica
  - [x] Tabla `market_price_season`: índice estacional por producto, central y mes, que compara cada mes con el promedio de su mismo año (así no cuenta la inflación); solo con 3 o más años completos. Sin ellos no hay temporada (R1)
  - [x] Validaciones antes de publicar: llave sin repetir, precio medio presente y dentro del mínimo y el máximo (con un peso de tolerancia por el redondeo del DANE), fuente en `sources` (R8)
  - [x] `GET /api/v1/market/prices` y `GET /api/v1/market/prices/{product_id}`, sin base de datos ni guardar nada (R9)
  - [x] Tabla `market_price_latest` (último precio por central y producto, con el de hace una semana, el cambio y el orden), escrita por el pipeline y por cada actualización de precios con la misma función (`sipsa.latest`). Las rutas `GET` solo filtran y devuelven; qué versión se sirve lo decide la dependencia `market_tables`
  - [x] La cita textual va en la columna `citation` de `sources` (nula si la fuente no pide una, R1) y la API la lee de ahí: `backend/api` no importa `pipeline` ni `pipeline` importa `backend` (`tests/test_dependencias.py`)
  - [x] Pantalla `/precios`, sin cuenta: central, búsqueda, último precio con su cambio frente a hace una semana (con forma y texto) y, al abrir un producto, su último año y su temporada, con el rótulo «No es un pronóstico» y la fuente
  - [x] Modo ligero y diseño adaptable de 320 a 1920 px (`npm run test:responsive`)
  - [x] Contrato aprobado por Haider o Felipe (`specs/02-contratos.md`): aprobado por Felipe el 10 de noviembre de 2026, con los errores `404` `unknown_market` y `unknown_product` y los campos de las respuestas tal como quedaron en el código
  - [x] Generador `design/pantallas/precios.py` con sus SVG (escritorio, móvil y producto abierto en móvil), con cifras reales de SIPSA
  - [ ] Láminas enviadas a Figma y aprobadas (la pantalla se programó antes del diseño, por pedido del equipo)
  - [x] Licencia de SIPSA verificada en los términos y condiciones del DANE (8 de noviembre de 2026): autorizan usar y transformar la información con la cita «Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co». La pantalla, las láminas y la fila de `sources` la llevan

### HU-222 · Precios al día

- **Historia:** Como agricultor, quiero que los precios de la central sean los del último día que publicó el DANE, sin que nadie tenga que volver a publicar el dataset, para decidir con el precio de hoy.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** hecha
- **Notas:** Es la excepción a «datos precalculados» que registra `docs/registro-de-decisiones.md`: solo para los precios, que cambian cada día. Sigue siendo historia de precios, no pronóstico. **9 de noviembre de 2026 (revisión de Felipe del PR #12):** la descarga sale de la API y pasa a dos crons del servicio `market`, después de revisar las 6 operaciones del servicio web de SIPSA (ninguna acepta filtros: todas devuelven la serie completa de todo el país). El precio del día sale del anexo del boletín diario del DANE (unos 340 KB), que es la misma serie del servicio sin el mínimo ni el máximo: el 6 de noviembre sus 63 precios de Corabastos y Tunja eran iguales a los del servicio. La serie completa (unos 300 MB) se baja una vez por semana, y la temporada solo cambia una vez al año, con el dataset.
- **Criterios de aceptación:**
  - [x] La API no baja nada: solo lee la última versión de `AGROSENSE_MARKET_DIR` (`current.json`), y la vuelve a mirar como mucho cada minuto, sin reiniciarse
  - [x] Servicio `market` en `docker-compose.yml` con el perfil `market` (no arranca con `docker compose up`): supercronic corre `python -m backend.market.updates diario` y `semanal` en los horarios del `.env` (`AGROSENSE_MARKET_DAILY_SCHEDULE`, `AGROSENSE_MARKET_WEEKLY_SCHEDULE`), en la hora de Bogotá
  - [x] Diario (de lunes a viernes, 3:00 p. m.): baja el anexo del boletín de cada día hábil que falte, hasta 10 días atrás. Un día sin boletín (festivo) no es un error. Sus filas citan `dane_sipsa_boletin`, con el mínimo y el máximo nulos (R1, R8)
  - [x] Semanal (domingos, 3:00 p. m.): baja la serie completa del servicio, que reemplaza los días del boletín; solo quedan los días del boletín posteriores al último día del servicio en cada central
  - [x] Cada actualización buena es una versión nueva e inmutable (`sipsa-AAAAMMDDTHHMMSS-boletin` o `-servicio`) con sus fuentes, y se guardan las dos últimas. Si algo falla, no se toca la versión que se sirve (R1), el log dice por qué y el comando termina con error
  - [x] Las descargas cortan por tiempo total y por tamaño (`AGROSENSE_MARKET_TIMEOUT_S`, `AGROSENSE_MARKET_MAX_MB`); la del servicio se reintenta 3 veces
  - [x] Cada versión trae también `market_price_latest`, calculada al escribirla: la API no calcula nada al responder
  - [x] El servicio `market` no usa la base de datos: lee su configuración de `pipeline/settings.py` y no recibe `POSTGRES_*`
  - [x] El candado no se borra al arrancar el servicio: uno que quedó de un proceso muerto se da por muerto a las 6 horas (`LOCK_STALE_S`)
  - [x] Una versión bajada solo se sirve si es igual o más nueva que lo publicado en `data/published`. La temporada sale siempre de lo publicado
  - [x] Las respuestas de `/market/*` dicen su `version`, su `updated_at`, la fuente del último día y la cita del DANE (R4, R8); la pantalla dice cuándo se actualizaron y muestra la cita tal cual
  - [x] Las pruebas no usan la red
  - [x] Contrato aprobado por Haider o Felipe: aprobado por Felipe el 10 de noviembre de 2026

### HU-238 · Historia de precios de SIPSA desde 2013

- **Historia:** Como motor, quiero la serie de precios mayoristas desde 2013 con su variabilidad entre años, para calificar el mercado con suficientes años y con un método publicado.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] El adaptador baja a la caché (`data/raw/sipsa_microdatos/`) los microdatos de SIPSA-P del DANE (catálogo 776, 2013–2024, de uso público y gratuito: 8 ZIP con un CSV cada uno, de 1,5 a 15,7 MB) con los límites de tiempo y tamaño de `pipeline/sources/fetch.py`, y revisa el tamaño de lo que descomprime. La carpeta entra a la caché compartida (`pipeline/raw_cache.py`, `FOLDERS`) con su licencia en `docs/licencias.md`. Sin red en las pruebas
  - [ ] Normaliza los formatos de cada año (revisados archivo por archivo el 15 nov 2026): separador `;`; codificación Latin-1 (2013–2023) o UTF-8 con BOM (2024); fecha `1/01/2019` (2013–2021) o `ene-22` (2022–2024); la central en `Fuente` (2013–2019) o `Mercado` (2020–2024); el precio en la columna que empieza por «Precio» (cambia de nombre casi cada año), entero hasta 2021 y con espacios y punto de miles desde 2022 (` 1.150 `); columnas vacías de sobra (2022 y 2023) y `CODIGO_CPC_AC` (2024); textos en NFC. Cada ZIP trae también `.dta` y `.sav`: solo se lee el CSV. Un precio que no se puede leer se cuenta y va al log
  - [ ] Valida y falla si no cuadra: precio mayor que 0, ninguna llave (año, mes, producto, central) repetida en los productos y centrales que se usan, y que cada nombre de producto y de central del mapeo exista en los microdatos
  - [ ] Arma la serie mensual: el microdato en sus meses y, después del último mes de los microdatos, el promedio de los precios diarios de `market_price_day`; si los dos tienen el mes, vale el microdato. Entran los productos de `market_price_day` y los de `pipeline/sipsa_crops.yaml`. Es interna: no se publica como tabla
  - [ ] Comprueba las dos fuentes en cada publicación: en los meses que tienen las dos, la mediana de \|microdato ÷ promedio de los diarios − 1\| de cada serie no pasa de 1 %, y si pasa, el build falla y dice cuál. Con los datos del 15 nov 2026: menos de 0,04 % en las 42 series que se cruzan; meses sueltos de hasta 7,9 % en 2020–2022, ninguno de más de 0,06 % desde 2023; la papa más parecida que no es la papa negra (superior) da 4,9 %
  - [ ] Mapeo con fuente (`pipeline/sipsa_crops.yaml`): el nombre de cada producto en los microdatos cuando no es el del diario (la papa es «Papa parda pastusa», la misma serie que «Papa negra»: 0,02 %); el haba es «Haba verde», que solo trae el microdato; el maíz sigue sin producto (decisión de HU-051). El build valida el mapeo contra la serie mensual, no solo contra `market_price_day`. Las centrales se emparejan por nombre (en los microdatos no viene el código `fuenId`), con un mapeo del adaptador que se valida contra `region.yaml`
  - [ ] `market_price_season` publica, por producto, central y mes, con la **media móvil centrada de 12 meses** (Texas A&M E-314; 2×12, solo con los 13 meses; un año cuenta con sus 12 cocientes): `seasonal_index` (normalizado para que los 12 promedien 1), `seasonal_sd` (desviación estándar muestral entre años, en la misma escala), `years_below` (años en que el cociente del mes quedó bajo 1), `years`, `first_year`, `last_year` y `source_id`; solo con 5 o más años completos (IFPA de la FAO). `market_month` lleva `seasonal_index`, `seasonal_sd` y `years_below` al cultivo, y su `price_cop_kg` sale de la serie mensual
  - [ ] Casos de referencia con los datos publicados: papa, arveja, cebolla y zanahoria tienen 12 años (2014–2025) en Corabastos y en Tunja; la papa en Tunja, 7 (2014–2020); el haba, 10 en Corabastos y 8 en Tunja (2014–2023)
  - [ ] La fuente `dane_sipsa_microdatos` en `sources` con URL, licencia (uso público y gratuito, con la cita textual del DANE), periodo y cobertura, y en `notes` que desde 2025 los meses son el promedio de los diarios de `dane_sipsa`, con la comprobación (R8). `pipeline/schema.py`, `pipeline/examples.py` y `data/examples/` con las columnas nuevas. Sube `dataset_version` (R4)
- **Reglas que aplican:** R1, R4, R7, R8
- **Contrato que toca:** `market_price_season` y `market_month` (`seasonal_sd`, `years_below`, la media móvil, el mínimo de 5 años y la fuente de la serie empalmada): pendiente de aprobar por Haider o Felipe
- **Notas:** Agregada el 15 de noviembre de 2026 para HU-073 (decisión 17; investigación en `docs/investigacion-decisiones.md`, 5f). Por qué: los precios publicados solo eran los del servicio web de SIPSA, desde febrero de 2020. Con eso hay 5 años completos (2021–2025), justo el mínimo del IFPA, y una desviación con 5 puntos no es confiable. Además SIPSA dejó de publicar papa negra en Tunja en julio de 2021, así que la papa de Boyacá (que vende en Tunja, `department_markets`) quedaba sin un año completo. Con los microdatos hay 12 años, y se recuperan la papa de Tunja (7 años) y el haba. El DANE no ha publicado los microdatos de 2025 (el catálogo llega a 2024, modificado el 1 de abril de 2025): por eso se empalma con los diarios. Reemplaza el método de HU-051 (el promedio del año como base y 3 años como mínimo). Para republicar hacen falta las cachés completas (IMERG, EVA y SoilGrids); hoy solo las tiene quien publicó el dataset 2026.11.21. Afecta a HU-221 (de Luisa): la web de `/precios` dice «que el promedio de su año», y con la media móvil la base es el promedio de los 12 meses alrededor (R5). Se descartaron el boletín de Corabastos (un PDF del día, sin archivo histórico ni metodología) y mezclarlo con SIPSA (dos métodos para un indicador, R1).

