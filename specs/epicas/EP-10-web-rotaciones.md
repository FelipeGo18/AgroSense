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
estado: pendiente
---

# EP-10 · Estrategias de rotación como entrada de la web

**Resultado esperado:** El agricultor llega desde su lote (o desde su municipio y su área, sin cuenta) a las **estrategias de rotación de hasta 3 ciclos**, fija sus prioridades, entiende por qué cada estrategia queda en su lugar, cómo cuida el suelo y por qué otras se descartaron, y abre cualquier ciclo para ver su diagnóstico, el agua que necesitará y qué cambió en su zona.

**Es la entrada principal del MVP (decisión 12):** lote o municipio y área → estrategias → un ciclo con su diagnóstico → agua del plan → qué cambió. El diagnóstico suelto (EP-09) sigue disponible, y con «rotar» lleva aquí. Todo es informativo: decide el agricultor.

Arranca contra las respuestas simuladas y se integra con EP-08. Cada pantalla se diseña en Figma antes de programarla (`specs/05-frontend.md`, «Pantallas por diseñar del MVP»).

## Historias de usuario

### HU-214 · Entrada a las estrategias, con o sin cuenta

- **Historia:** Como agricultor, quiero llegar a las estrategias de rotación desde mi lote, o sin cuenta desde mi municipio y mi área, para planear mis próximos ciclos sin llenar más de lo necesario.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Sin cuenta, la pantalla pide: municipio (buscador), área en hectáreas (mayor que cero), qué había antes en el terreno (de 0 a 3 cultivos del catálogo, o «Nada: es la primera siembra aquí»), cuándo sembrar el primer ciclo (un mes de los próximos doce), «¿Tiene riego?» («Sí», «No», «No sé») y cuántos ciclos (2 o 3; por defecto 3)
  - [ ] Con cuenta, se entra desde el lote: la web toma `lot_id`, el riego del lote y, en `previous_crop_ids`, los cultivos de las temporadas de las que viene el terreno (`follows_season_ids`); el área es la parte libre o la de la temporada cosechada que se va a sembrar
  - [ ] **La rotación actual (HU-223):** sin cuenta, la pantalla pregunta «¿Qué viene sembrando en este terreno?» (de 2 a 3 cultivos en orden, opcional, con «No tengo una rotación fija»). Con cuenta, la web la arma con el historial del terreno, del más antiguo al más reciente, y deja corregirla antes de consultar
  - [ ] Envía `POST /api/v1/rotations` con los campos del contrato, incluidas las prioridades de la rotación (HU-101) y las de las señales (`signal_priorities`, HU-202)
  - [ ] Sin cuenta, el área solo se usa en el navegador para el agua del plan (HU-215) y no se guarda en el servidor (R9)
  - [ ] Validación inmediata en pantalla; un 422 de la API se explica en palabras sencillas
  - [ ] Cada botón tiene una acción o una navegación definida; usable a 360 px
- **Reglas que aplican:** R7, R9
- **Contrato que toca:** cuerpo de `POST /api/v1/rotations`
- **Notas:** Decisión 12. Reemplaza, para el MVP, a la finca temporal (HU-141 y HU-145, que pasaron a P1 el 11 de octubre de 2026): sin cuenta se consulta por municipio, área y cultivo anterior. Agregada el 11 de octubre de 2026.

### HU-101 · Prioridades del agricultor

- **Historia:** Como agricultor, quiero indicar qué me importa más en la rotación, para que el ranking de estrategias refleje mis prioridades.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cuatro controles: agua, suelo, ingreso y riesgo, cada uno de 0 a 5 (`priorities` de `POST /api/v1/rotations`)
  - [ ] El ranking se actualiza al cambiarlos
  - [ ] La web envía `sowing_date`: la fecha en que se sembraría el primer ciclo, la que eligió en la entrada (HU-214); no se pide ningún otro periodo
  - [ ] Con todas las prioridades en 0, la web no envía la petición y pide subir al menos una
- **Contrato que toca:** `POST /api/v1/rotations`
- **Notas:** Con cuenta, los cultivos anteriores salen del historial del terreno que se va a sembrar: los de todas las temporadas de las que viene (`follows_season_ids`, HU-165); sin cuenta, el usuario elige a mano el cultivo anterior. Estas cuatro prioridades son las de las rotaciones; las de las señales (una por señal, para el semáforo de cada ciclo) están en HU-202. Usan el mismo control visual.

### HU-102 · Estrategias con ciclos, desglose y salud del suelo

- **Historia:** Como agricultor, quiero ver cada estrategia con sus ciclos, su desglose, cómo cuida mi suelo y por qué se descartaron otras, para decidir con confianza.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Cada estrategia es una tarjeta con sus ciclos en orden: cultivo, fecha de siembra, cosecha estimada con su base y la luz del ciclo con forma y texto. El descanso se ve como «Descanso»
  - [ ] Desglose por criterio (agua, suelo, ingreso y riesgo) con su puntaje y el total
  - [ ] **La rotación actual va primero**, rotulada «Lo que usted siembra hoy», con sus mismos ciclos, criterios y salud del suelo, y sus problemas a la vista (`issues`: la regla que viola o el ciclo de alto riesgo). Cada estrategia sugerida dice en qué gana o pierde frente a ella (`vs_current`), con forma y texto. Sin rotación actual, la web lo dice y ofrece escribirla (HU-223)
  - [ ] Bloque «Salud del suelo» con sus cinco criterios (nitrógeno, carbono orgánico, suelo cubierto, corte de plagas y erosión), cada uno con su nivel en forma y texto, su razón y su fuente; un criterio `insufficient_data` se ve «Sin datos suficientes», no como malo (R1)
  - [ ] Rótulo visible: «Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo»
  - [ ] El suelo usado lleva su rango y el rótulo de estimación (R10)
  - [ ] Las estrategias excluidas y su motivo se ven a pedido: la regla que viola, «No se da en su zona» con el dato de la ficha y su fuente, o «Alto riesgo en el ciclo 2: heladas» con la razón
  - [ ] Sin estrategias válidas, estado vacío con las exclusiones a la vista y un texto que propone cambiar la fecha o el número de ciclos
  - [ ] Tocar un ciclo abre su detalle (HU-215)
  - [ ] Rótulo visible: «Es información para decidir. La decisión es suya»
- **Reglas que aplican:** R1, R2, R3, R5, R10
- **Contrato que toca:** respuesta de `POST /api/v1/rotations` (`strategies`, `current_strategy`, `vs_current`, `cycles`, `scores`, `soil_health`, `excluded`)
- **Notas:** Cambiada el 11 de octubre de 2026 a estrategias de hasta 3 ciclos con salud del suelo (decisión 12); pasó de M a L. El resaltado de un cultivo alternativo del diagnóstico se fue con HU-197 a P1. **8 de noviembre de 2026 (decisión 14):** suma la rotación actual como referencia y la erosión; el diseño de «Estrategias de rotación» cambia en Figma antes de programarla.

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
