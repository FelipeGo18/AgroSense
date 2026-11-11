---
id: EP-10
titulo: "Estrategias de rotación como entrada de la web"
prioridad: P0
fase: [Evento]
rol: "Web"
agentes: [web]
subsistemas: [W2, W3, W4]
depende_de: [EP-09, EP-08, HU-146, HU-212]
reglas: [R1, R2, R3, R5, R9, R10]
estado: en curso
---

# EP-10 · Estrategias de rotación como entrada de la web

**Resultado esperado:** El agricultor llega desde su lote (o desde su municipio y su área, sin cuenta) a las **estrategias de rotación de hasta 3 ciclos**, fija sus prioridades, entiende por qué cada estrategia queda en su lugar, cómo cuida el suelo y por qué otras se descartaron, y abre cualquier ciclo para ver su diagnóstico, el agua que necesitará y qué cambió en su zona.

**Es la entrada principal del MVP (decisión 12):** lote o municipio y área → estrategias → un ciclo con su diagnóstico → agua del plan → qué cambió. El diagnóstico suelto (EP-09) sigue disponible, y con «rotar» lleva aquí. Todo es informativo: decide el agricultor.

Arranca contra las respuestas simuladas y se integra con EP-08. Cada pantalla se diseña en Figma antes de programarla (`specs/05-frontend.md`, «Pantallas por diseñar del MVP»).

## Historias de usuario

### HU-214 · Entrada a las estrategias, con o sin cuenta

- **Historia:** Como agricultor, quiero llegar a las estrategias de rotación desde mi lote, o sin cuenta desde mi municipio y mi área, para planear mis próximos ciclos sin llenar más de lo necesario.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Sin cuenta, la pantalla pide: municipio (buscador), área en hectáreas (mayor que cero), qué había antes en el terreno (de 0 a 3 cultivos del catálogo, o «Nada: es la primera siembra aquí»), cuándo sembrar el primer ciclo (un mes de los próximos doce), «¿Tiene riego?» («Sí», «No», «No sé») y cuántos ciclos (2 o 3; por defecto 3)
  - [x] Con cuenta, se entra desde el lote: la web toma `lot_id`, el riego del lote y, en `previous_crop_ids`, los cultivos de las temporadas de las que viene el terreno (`follows_season_ids`); el área es la parte libre o la de la temporada cosechada que se va a sembrar
  - [x] **La rotación actual (HU-223):** sin cuenta, la pantalla pregunta «¿Qué viene sembrando en este terreno?» (de 2 a 3 cultivos en orden, opcional, con «No tengo una rotación fija»). Con cuenta, la web la arma con el historial del terreno, del más antiguo al más reciente, y deja corregirla antes de consultar
  - [x] Envía `POST /api/v1/rotations` con los campos del contrato, incluidas las prioridades de la rotación (HU-101) y las de las señales (`signal_priorities`, HU-202: las da `useSignalPriorities` de `web/src/features/diagnosis/priorities.ts`, las mismas de la consulta del diagnóstico)
  - [x] Sin cuenta, el área solo se usa en el navegador para el agua del plan (HU-215) y no se guarda en el servidor (R9)
  - [x] Validación inmediata en pantalla; un 422 de la API se explica en palabras sencillas
  - [x] Cada botón tiene una acción o una navegación definida; usable a 360 px
  - [x] Desde el diagnóstico («Ver estrategias de rotación», HU-203) llega con `?municipio=&siembra=&anterior=&riego=` o, con un lote, `?lote=&siembra=&anterior=` (`strategiesLink` de `web/src/features/diagnosis/lights.ts`): la pantalla los toma ya elegidos, con el cultivo consultado como lo que había antes en el terreno
- **Reglas que aplican:** R7, R9
- **Contrato que toca:** cuerpo de `POST /api/v1/rotations`
- **Notas:** Decisión 12. Reemplaza, para el MVP, a la finca temporal (HU-141 y HU-145, que pasaron a P1 el 11 de octubre de 2026): sin cuenta se consulta por municipio, área y cultivo anterior. Agregada el 11 de octubre de 2026.
- **Hecho (11 nov):** en `/consultar` (`web/src/pages/strategies/StrategiesPage.tsx`; la lógica en `web/src/features/strategies/entry.ts`). «Consultar» de la barra y «Ver estrategias de rotación» del lote y del diagnóstico llevan aquí. Sin cuenta, el área vive solo en la pestaña (`sessionStorage`): nunca va en la dirección ni a la API, y el campo lo dice («Solo se usa en este dispositivo»). Lo demás va en la dirección, así que la consulta se puede volver a abrir. Con sesión y lotes, «¿Para cuál terreno?» deja elegir un lote o seguir sin él. Con lote, el municipio y el riego salen del lote (con «Cambiarlo en el lote»); lo de antes, de las siembras cosechadas que dejaron el terreno libre (las mismas de «Registrar siembra», HU-165), y el área es la de esas siembras o, si no elige ninguna, la libre del lote. Al elegirlas, la rotación actual se arma con todo el historial del que vienen, del más antiguo al más reciente (las últimas tres), y se puede corregir. Si un lote de la dirección no es de la persona o no hay sesión, no se consulta y se ofrece entrar. Un 422 se traduce («Revise: priorities» → «Revise sus prioridades de la rotación»), y un 501 dice que el cálculo todavía no está listo. Mientras no exista HU-102, el resultado es un resumen: cuántas estrategias, las tres primeras con su puntaje, la rotación actual, cuántas se descartaron, las limitaciones y los rótulos «Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo» y «La decisión es suya». Pruebas en `web/src/pages/strategies/strategies.test.tsx` y `web/src/pages/farm/farm.test.tsx`; `/consultar` está en `e2e/responsive-check.mjs`, con y sin datos.

### HU-101 · Prioridades del agricultor

- **Historia:** Como agricultor, quiero indicar qué me importa más en la rotación, para que el ranking de estrategias refleje mis prioridades.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] Cuatro controles: agua, suelo, ingreso y riesgo, cada uno de 0 a 5 (`priorities` de `POST /api/v1/rotations`)
  - [x] El ranking se actualiza al cambiarlos
  - [x] La web envía `sowing_date`: la fecha en que se sembraría el primer ciclo, la que eligió en la entrada (HU-214); no se pide ningún otro periodo
  - [x] Con todas las prioridades en 0, la web no envía la petición y pide subir al menos una
- **Contrato que toca:** `POST /api/v1/rotations`
- **Notas:** Con cuenta, los cultivos anteriores salen del historial del terreno que se va a sembrar: los de todas las temporadas de las que viene (`follows_season_ids`, HU-165); sin cuenta, el usuario elige a mano el cultivo anterior. Estas cuatro prioridades son las de las rotaciones; las de las señales (una por señal, para el semáforo de cada ciclo) están en HU-202. Usan el mismo control visual.
- **Hecho (11 nov), con HU-214:** las cuatro prioridades empiezan en 3, iguales, hasta que la persona las mueva (`START_PRIORITIES`; `docs/registro-de-decisiones.md`). Van en un resumen plegado, «¿Qué busca en la rotación? · Ajustar», con el control de prioridad del kit. Al cambiar una se vuelve a pedir `POST /rotations` y el resumen se reordena; la lista completa es HU-102. No se recuerdan entre visitas (las de las señales sí, HU-202).

### HU-102 · Estrategias con ciclos, desglose y salud del suelo

- **Historia:** Como agricultor, quiero ver cada estrategia con sus ciclos, su desglose, cómo cuida mi suelo y por qué se descartaron otras, para decidir con confianza.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] Cada estrategia es una tarjeta con sus ciclos en orden: cultivo, fecha de siembra, cosecha estimada con su base y la luz del ciclo con forma y texto. El descanso se ve como «Descanso»
  - [x] Desglose por criterio (agua, suelo, ingreso y riesgo) con su puntaje y el total
  - [x] **La rotación actual va primero**, rotulada «Lo que usted siembra hoy», con sus mismos ciclos, criterios y salud del suelo, y sus problemas a la vista (`issues`: la regla que viola o el ciclo de alto riesgo). Cada estrategia sugerida dice en qué gana o pierde frente a ella (`vs_current`), con forma y texto. Sin rotación actual, la web lo dice y ofrece escribirla (HU-223)
  - [x] Bloque «Salud del suelo» con sus cinco criterios (nitrógeno, carbono orgánico, suelo cubierto, corte de plagas y erosión), cada uno con su nivel en forma y texto, su razón y su fuente; un criterio `insufficient_data` se ve «Sin datos suficientes», no como malo (R1)
  - [x] Rótulo visible: «Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo»
  - [x] El suelo usado lleva su rango y el rótulo de estimación (R10)
  - [x] Las estrategias excluidas y su motivo se ven a pedido: la regla que viola, «No se da en su zona» con el dato de la ficha y su fuente, o «Alto riesgo en el ciclo 2: heladas» con la razón
  - [x] Sin estrategias válidas, estado vacío con las exclusiones a la vista y un texto que propone cambiar la fecha o el número de ciclos
  - [ ] Tocar un ciclo abre su detalle (HU-215). Queda para HU-215: hasta que exista el detalle no se dibuja el botón, porque un control sin función está prohibido (decidido por Haider el 11 de noviembre de 2026)
  - [x] Rótulo visible: «Es información para decidir. La decisión es suya»
- **Reglas que aplican:** R1, R2, R3, R5, R10
- **Contrato que toca:** respuesta de `POST /api/v1/rotations` (`strategies`, `current_strategy`, `vs_current`, `cycles`, `scores`, `soil_health`, `excluded`)
- **Notas:** Cambiada el 11 de octubre de 2026 a estrategias de hasta 3 ciclos con salud del suelo (decisión 12); pasó de M a L. El resaltado de un cultivo alternativo del diagnóstico se fue con HU-197 a P1. **8 de noviembre de 2026 (decisión 14):** suma la rotación actual como referencia y la erosión; el diseño de «Estrategias de rotación» cambia en Figma antes de programarla.
- **Hecho (11 nov), salvo abrir el ciclo (HU-215):** en `/consultar`, al consultar, la entrada cambia por el resultado del diseño (`design/pantallas/estrategias.py`). El código está en `web/src/pages/strategies/StrategyResults.tsx` y `StrategyCard.tsx`, y la lectura de la respuesta en `web/src/features/strategies/strategies.ts`.
  - **Arriba:** el resumen de la consulta, con «Cambiar», que vuelve a la entrada con lo escrito y deja «Volver sin cambiar». Al lado, las prioridades de la rotación: al moverlas se vuelve a pedir y el orden anterior se sigue viendo con «Actualizando…».
  - **El suelo usado:** el del municipio, con su rango de pH y de carbono orgánico y el rótulo de estimación (R10). Con `soil_basis = lot` se dice que es el del lote, sin cifras, hasta que exista HU-182.
  - **Las tarjetas:** primero «Lo que usted siembra hoy», con «Lo que no cumple» (`issues`), y después las sugeridas en su orden. Cada una tiene:
    - su puesto y su total, y lo que gana o pierde frente a hoy, con triángulo y texto;
    - los ciclos: el abono verde con su rótulo y «Se incorpora»; el descanso «Sin semáforo: no se siembra»; la luz con forma y texto; la del criterio de AgroSense si difiere; y lo que limita;
    - la nota de la cosecha por calendario;
    - el desglose con su peso y su diferencia frente a hoy (un criterio sin datos no tiene barra);
    - sus razones, la salud del suelo con su fuente y sus limitaciones.
  - **Sin rotación actual:** lo dice y ofrece «Escribir lo que siembro».
  - **Las descartadas:** van plegadas, con su ciclo, su motivo y su fuente, y cuántas son por motivo cuando la API trae menos que el total.
  - **Sin estrategias:** «Ninguna estrategia cumple…», con las descartadas abiertas, «Cambiar la fecha» y «Probar con 2 ciclos».
  - **La fuente de cada regla:** para citarla, el contrato suma `source_ids` (decisión 15 de `docs/decisiones.md`, aprobado por Haider). Los ejemplos de la API suman una sugerida con descanso y los estados `sin_actual` y `sin_opciones`.
  - **Pruebas:** en `web/src/pages/strategies/strategies.test.tsx`. Revisado sin scroll horizontal ni objetivos de menos de 44 px a 320, 360, 768, 1024 y 1440 px, con y sin modo ligero.

### HU-215 · Ciclo de una estrategia

- **Historia:** Como agricultor, quiero abrir un ciclo de una estrategia y ver su diagnóstico, el agua que necesitará y cuándo suele estar verde el campo, para revisar ese ciclo antes de decidir.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Reutiliza los componentes del resultado del diagnóstico (HU-092, HU-194, HU-202 y HU-203) con el `diagnosis` del ciclo; no pide un diagnóstico aparte
  - [ ] Encabezado con la estrategia y el ciclo («Ciclo 2 de 3: arveja, siembra el …») y botones para ir al ciclo anterior y al siguiente
  - [ ] **Agua del plan:** pide `POST /api/v1/water-plans` con el cultivo del ciclo, su fecha de siembra y el área de la entrada (`area_pct` 100), y muestra el déficit mensual y el volumen en rangos, en año normal y año seco, con el rótulo de estimación (R10). Sin riego o sin definir, dice «En estos meses la lluvia no alcanza: el cultivo pasaría sed»
  - [ ] La humedad del suelo de la zona (POWER y, si existe, SMAP) se ve junto al agua como contraste, cada una en su unidad y con su fuente; nunca un valor combinado (decisión 11)
  - [ ] **Verdor:** la serie `ndvi` de `/trends` junto a la ventana del ciclo, con el rótulo «Cuándo suele estar verde el campo en su zona · MODIS, 250 m». Sin datos, estado vacío (R1)
  - [ ] Enlace a «Qué cambió en su zona» (HU-219) con el municipio y el cultivo del ciclo
  - [ ] Un ciclo de descanso muestra su duración y la regla que lo propone, sin semáforo
  - [ ] Con cuenta, el primer ciclo ofrece «Registrar esta siembra», que crea la temporada con el diagnóstico visto (HU-165)
  - [ ] Cada botón tiene una acción o una navegación definida; usable a 360 px
- **Reglas que aplican:** R1, R5, R8, R9, R10
- **Contrato que toca:** `strategies[].cycles[].diagnosis` de `POST /api/v1/rotations`; `POST /api/v1/water-plans`; serie `ndvi` de `GET /api/v1/trends`
- **Notas:** Decisión 12. Depende de HU-084, HU-146 y HU-078 (o de sus respuestas simuladas). Agregada el 11 de octubre de 2026.
