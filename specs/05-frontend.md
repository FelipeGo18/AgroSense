# Frontend: visión, estilo y stack

Cómo se ve, se siente y se construye la web de AgroSense. Complementa `03-sistemas.md` (qué hace cada subsistema W) y `04-stack.md` (resumen de tecnologías).

Se ajusta mientras se prototipa. Si un cambio toca las reglas R1–R10 o el contrato de la API, se registra en `docs/decisiones.md` y se refleja en `specs/01-reglas.md` y `specs/02-contratos.md`.

## Dónde se hace qué

| Momento | Qué se hace | Dónde |
|---|---|---|
| Fase 0 (10 oct – 13 nov) | Identidad visual, animaciones, audio, assets 3D y un prototipo navegable del frontend contra datos de ejemplo (EP-15) | Este repositorio, carpeta `web/` y Figma |
| Evento (14 y 15 nov) | La aplicación de la demo, integrada con la API real | Un repositorio nuevo, creado en el evento |

El prototipo sirve para decidir y ensayar el estilo. Qué se puede reutilizar en el evento depende de los términos de Space Apps 2026 (HU-004): hasta confirmarlo, se asume que el código se reescribe y que lo reutilizable son decisiones, diseños en Figma, guías y assets con licencia.

### Diseño: los generadores son la fuente y Figma es la vitrina

Cada pantalla, lámina y pieza del kit se dibuja con código en `design/` (`design/pantallas/*.py`, `design/kit/`, `design/mascota/`, `design/paisaje/`, `design/globo/`). Ese código genera un SVG, que se revisa en el navegador (`design/pantallas/ver.html`) y se envía a Figma con `design/kit/send_to_figma.ts` y el complemento local. Figma es donde el equipo ve, comenta y aprueba.

Reglas:

1. **Un cambio de diseño se hace en el generador**, no a mano en Figma. Luego se regenera el SVG y se reenvía. Así el cambio queda en git y no se pierde al regenerar.
2. **Si alguien edita una pantalla directamente en Figma**, avisa en el canal del equipo y el cambio se pasa al generador antes de volver a enviar esa pantalla. Si no, la próxima regeneración lo pisa.
3. **Lo que solo es acomodo en Figma** no necesita pasar a git: mover o agrandar secciones, ordenar marcos, renombrar capas, comentar. Lo guarda el historial de versiones de Figma.
4. **Las piezas compartidas viven en un solo lugar**: barra superior, pie de página, botones, campos, tarjetas y estados en `design/pantallas/ui.py`; tokens en `design/tokens/`; logos de redes en `design/pantallas/marcas.py`. Ninguna pantalla los copia.
5. **Se commitean los generadores y los SVG que producen**, junto con la spec o el doc que el cambio afecte. Los archivos pesados que se pueden volver a bajar (por ejemplo, la imagen Blue Marble) quedan fuera de git, y el generador dice cómo obtenerlos.
6. **Cualquier archivo de Figma sirve de destino**: en otra cuenta o en otro archivo se abre el complemento local, se toma su canal y se reenvían los SVG.
7. **Los generadores no son parte de la app.** Son la referencia exacta de medidas, colores, textos y estados para programar la web.

## Visión

La web parece un juego, pero es una herramienta real: cada pantalla responde una pregunta del agricultor con datos y reglas explicables. El juego aporta la sensación (tacto, ritmo, satisfacción de ver un resultado), no la mecánica.

### Inspiración, no copia

Las referencias son de **estilo**. No se traslada su estructura ni sus elementos.

| Referencia | Qué tomamos | Qué no tomamos |
|---|---|---|
| *The Farmer Was Replaced* | Low-poly con sombreado plano; paleta cálida y terrosa sobre un fondo frío y suave; luz difusa de diorama; botones gruesos y táctiles | Parcela flotante, ventanas de código, barra de recursos, dron, mecánica de programar |
| Web de *Grand Theft Auto VI* | Navegación narrativa guiada por scroll; transiciones de cámara y máscaras; ritmo cinematográfico | Su contenido, composición y tipografía |

Si una idea se reconoce como «una pieza del juego», se descarta.

### Concepto: del satélite al lote

- **Paisaje con suelo y horizonte.** Un paisaje andino continuo: montañas, niebla en los valles y el mosaico de parcelas en ladera del altiplano. Nada flota.
- **La navegación es un descenso.** La cámara baja del satélite (los datos de NASA) a la región, al municipio y a la finca. Cada nivel es una sección de la app; el scroll o los toques mueven la cámara. Quien vuelve con sesión no repite el descenso: entra directo al nivel de su finca.
- **El paisaje acompaña al dato.** Las parcelas del cultivo consultado se resaltan. El paisaje refuerza, nunca reemplaza, el resultado escrito.
- **El paisaje está vivo.** El cielo y la escena reflejan la condición aproximada de ahora en el municipio: día o noche, lluvia, nubes y viento (ver «Ambiente en vivo»).

### Mascota: la Semilla Sputnik

Una semilla germinando que es un satélite, dibujada como caricatura de los años 60: tinta gruesa, ojos de pastel, brazos de manguera con guantes y pocos colores planos. Es la guía: acompaña el descenso, señala lo importante y reacciona a lo que pasa (celebra un verde, se preocupa con un rojo, se encoge entre niebla con «datos insuficientes» sin que parezca un riesgo). En el inicio presenta qué es AgroSense.

- Las raíces son las antenas barridas del Sputnik: al volar quedan atrás como estela. El brote es la antena de señal y sus hojas son los paneles solares.
- La identidad está en la cara, los brazos, las raíces y el brote. La semilla puede cambiar según el contexto (germinada, frijol, maíz…), por ejemplo con el cultivo consultado.
- Su estilo se aleja a propósito del low-poly de la escena: es «otro material» que viaja por el paisaje.
- Representa el origen de los datos (observación desde el espacio) sin contar la historia de NASA.
- Tiene una versión 2D (`Mascot` en `web/src/components/mascot/`) para la interfaz, el modo ligero, los estados y los íconos, y tendrá una 3D para la escena.
- Sus expresiones refuerzan el resultado; nunca son la única forma de comunicarlo.
- Es original: no copia a ningún satélite ni personaje de marca existente.

## Mapa de la web

### Modelo

**Usuario → zonas (municipios) → lotes → temporadas.** Un usuario con cuenta puede tener varios lotes en varias zonas. Un lote grande puede tener varios cultivos a la vez: cada temporada ocupa una parte de su área y sabe qué había antes en ese terreno. El agricultor divide y junta partes como trabaja: una temporada puede venir de una o varias anteriores y tener varias sucesoras, así que el historial de un lote es una red de terrenos que se dividen y se juntan, no una sola fila. Cada temporada registra un cultivo, su parte del área, sus fechas y el diagnóstico que se vio al sembrar. Sin cuenta, hay una sola **finca temporal** en el dispositivo: área total y porcentaje por cultivo.

### Flujo del MVP

Desde el 11 de octubre de 2026 (decisión 12), **la entrada del lote y de la consulta es «Estrategias de rotación»**:

**lote (o municipio y área, sin cuenta) → estrategias de rotación de 3 ciclos → ciclo de una estrategia (con su diagnóstico) → agua del plan → qué cambió en su zona.**

La web del MVP es 2D: el modo ligero (HU-158) es el modo por defecto. Las pantallas de lo recortado siguen en esta página y en Figma, marcadas como P1; no se borran. La oferta es valor agregado: se ve como una señal más dentro de cada ciclo, nunca como la portada.

### Partes

| Parte | Quién | Qué hace el usuario | Qué ve |
|---|---|---|---|
| **MVP · Estrategias de rotación** (HU-214, HU-101, HU-102) | Todos | Sin cuenta: escribe municipio, área, qué había antes, cuándo sembrar el primer ciclo, si tiene riego y cuántos ciclos (2 o 3). Con cuenta: entra desde su lote. Mueve sus prioridades de la rotación (agua, suelo, ingreso y riesgo) | Tarjetas de estrategias en orden, cada una con sus ciclos (cultivo, siembra, cosecha estimada y luz con forma y texto), su desglose por criterio y el bloque «Salud del suelo» con cuatro criterios (nitrógeno, carbono orgánico, suelo cubierto y corte de plagas), cada uno con nivel, razón y fuente. Las descartadas a pedido, con su motivo («Alto riesgo en el ciclo 2: heladas», «No se da en su zona»). Rótulos: «Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo» y «Es información para decidir. La decisión es suya» |
| **MVP · Ciclo de una estrategia** (HU-215) | Todos | Abre un ciclo, pasa al anterior o al siguiente; con cuenta, registra la siembra del primer ciclo | Reusa el resultado del diagnóstico (parte C): aptitud, semáforo con las dos luces, las seis señales, lo que más limita, razones y limitaciones. Debajo, el agua del plan del ciclo (déficit mensual y volumen en rangos, año normal y seco, rótulo de estimación), la humedad del suelo de la zona según POWER y SMAP lado a lado, y cuándo suele estar verde el campo (MODIS NDVI). Enlace a «Qué cambió en su zona» |
| **MVP · Qué cambió en su zona** (HU-219) | Todos | Llega desde el resultado, desde un ciclo o desde el lote | Por mes, heladas, lluvia y temperatura máxima de dos periodos (por ejemplo, 1981–2000 y 2005–2024), con años y fuente, y las mejores ventanas de cada periodo lado a lado. Rótulo: «Así fue en la historia de su zona. No es un pronóstico». Un valor sin datos se ve «Sin datos suficientes» |
| **MVP · Mapa del lote con capa de la NASA** (HU-211) | Con cuenta | Prende y apaga la imagen satelital y el NDVI mientras dibuja o mira su lote | El mapa de MapLibre con las capas WMTS de NASA GIBS, cada una con su producto, su fecha, su resolución y su atribución. Si GIBS no responde, sigue OpenStreetMap y lo dice |
| A. Inicio | Todos | Conoce AgroSense bajando por un recorrido de paradas (con el scroll, con el enlace de cada parada o con los puntos del borde); elige consultar sin cuenta o entrar | La Tierra gira en el espacio y, al bajar, frena con la región piloto al frente. La mascota guía: vuela del lugar de una parada al de la siguiente y dice una frase en cada una. Sin three.js: la Tierra se dibuja en un lienzo 2D. Con «reducir movimiento» nada gira ni vuela. Presenta el flujo del MVP con cuatro preguntas (estrategias de rotación, revisión de cada ciclo, agua del plan y qué cambió). En la barra, el control de sonido, que arranca apagado |
| B. Descenso (**P1**; en el MVP, un buscador de municipio en 2D) | Invitado y usuario nuevo | Busca su municipio (satélite) y lo ve entre sus vecinos (región). Con cuenta, al llegar al municipio dibuja su primer lote en el mapa real, le pone nombre, dice si tiene riego y registra el cultivo y la fecha de siembra (HU-164) | La cámara baja guiada por la mascota hasta el municipio o hasta el lote |
| C. Consulta suelta: diagnóstico de una ventana (MVP; por mes. Los cultivos alternativos, las semanas y «Planear una siembra» son **P1**) | Todos | Elige cultivo, cuándo sembrar (un mes de los próximos doce y, si quiere, una semana) y si tiene riego; si quiere, mueve sus prioridades (un peso de 0 a 5 por señal, que empiezan en los de AgroSense, con «Volver al criterio de AgroSense»); para «qué sembrar después», sin cuenta elige a mano el cultivo anterior | Si el cultivo no se da en su zona, la pantalla lo dice con su razón y ofrece elegir otro. Si se da: acción sugerida primero; luego el semáforo de esa ventana de siembra con sus prioridades y, si el de AgroSense da otra luz, las dos lado a lado («Con sus prioridades: verde · Con el criterio de AgroSense: amarillo»); las seis señales (agua, heladas, calor, suelo, oferta y mercado) con su calificación de 0 a 100, cuáles no cuentan con sus prioridades y «Lo que más limita»; las fuentes de un indicador juntas, con la usada marcada y las demás «para contrastar»; razones, limitaciones y gráficas. Con la acción «otra ventana», las mejores ventanas de los próximos doce meses y el acceso a «Planear una siembra». Con «rotar», hasta tres cultivos alternativos que en esa ventana salen bien en clima y tienen mejor oferta. Ranking de rotaciones con desglose. Rótulo: «Es información para decidir. La decisión es suya» |
| D. Mi finca (MVP: una sola zona, sin selector; la finca temporal es **P1**) | Con cuenta (inicio de quien vuelve); sin cuenta, la finca temporal | Con cuenta: recorre sus lotes, cambia de zona y abre un lote. Sin cuenta: registra área y porcentaje por cultivo | El mapa real con sus lotes, cada uno con sus cultivos y etapas; sin cuenta, la finca temporal con su plan de agua |
| D0. Mis lotes (MVP, con la capa de la NASA) | Con cuenta | Ve todos sus lotes en el mapa real y abre uno | Polígonos con los cultivos y las etapas de cada lote, avisos de riego o helada, y agregar lote |
| D1. Lote · ahora (**P1**: lote vivo. En el MVP, el detalle 2D del lote con su suelo, sus temporadas y «Ver estrategias de rotación») | Con cuenta | Recorre el diorama (arrastrar y acercar), toca un cultivo para elegirlo, mueve la línea de tiempo o la reproduce | El lote vivo (HU-187): diorama de cubos de tierra juntos, en el que cada cultivo ocupa tantos cubos como su parte del área, cada uno según su arquetipo y su etapa, dentro de una finca de bloques (casa, cerca con faroles, huerta, árbol y un perro acostado), el clima de ahora animado (viento que pasa, lluvia que cae, nubes, estrellas, escarcha y una mariposa ocasional), el suelo seco si es probable regar, y la línea de tiempo de la siembra a la cosecha (observada hasta el último dato de temperatura y estimada con un año normal después). En modo ligero o con movimiento reducido, la escena es estática. Guion en Figma («Ambiente del lote vivo») | Cultivo, etapa y días desde la siembra; su suelo estimado (pH, carbono orgánico, textura) con rango y rótulo de estimación |
| D1b. Lote · calendario (**P1**) | Con cuenta; sin cuenta, desde la consulta | Elige un cultivo y la lectura; mueve sus prioridades; toca un mes para ver sus semanas y sus razones | Dos lecturas. «Mi cultivo» (si ya está sembrado): de la siembra a la cosecha estimada, la etapa de cada mes, las heladas y el calor con «Vigile» en las etapas sensibles y el riego probable; en P1, abonar, labores y cosecha, gota y vender. «Planear una siembra» (parte libre, otro cultivo o sin cuenta): las ventanas de siembra de los próximos doce meses ordenadas primero por lo que más limita a cada una y, entre parecidas, por sus prioridades (las mismas seis de la consulta), con el factor limitante de cada ventana, las de alto riesgo aparte, la calificación de cada señal y, al tocar un mes, el detalle por semanas. Si el cultivo no se da en la zona, lo dice y ofrece elegir otro. Rótulo: «Según la historia de la zona. No es un pronóstico» |
| D2. Lote · próxima siembra (MVP: es la entrada a «Estrategias de rotación» desde el lote) | Con cuenta | Elige la parte del lote que va a sembrar, responde «¿Qué había antes en este terreno?» eligiendo una o varias temporadas cosechadas (o «Nada: es la primera siembra aquí») y mueve sus prioridades (agua, suelo, ingreso y riesgo) | El historial real de ese terreno (los cultivos de todas las temporadas de las que viene) y el suelo del lote; el diagnóstico de la siguiente ventana para la mejor opción; qué sembrar después, ordenado por sus prioridades, con las opciones excluidas a pedido. En P1, los riesgos que cubre un seguro (HU-188) y la lluvia en años de El Niño y La Niña (HU-189) |
| D3. Lote · agua (**P1**; en el MVP el agua se ve en cada ciclo de una estrategia) | Con cuenta | Revisa el plan | Calendario de riego del lote y total de la zona, con rangos y rótulo de estimación |
| D4. Lote · historial y progreso (MVP: el historial y registrar cosecha y siembra; el progreso y «Restaurar» son **P1**) | Con cuenta | Registra cosecha y nueva siembra; restaura una temporada borrada | Línea de tiempo de temporadas con sus divisiones y uniones, cada relación con su rotación (cumple o qué reglas viola, sin castigo) e hitos. Aparte, lo borrado hace menos de 30 días con «Borrada · se puede restaurar hasta <fecha>» y el botón «Restaurar» |
| E. Agregar lote o zona (MVP: agregar lote, sin descenso; varias zonas con selector es **P1**) | Con cuenta | Agrega un lote en su zona o en otro municipio | Mini descenso desde la finca al nuevo municipio |
| F. Cuenta (MVP: registro, entrar, salir, consentimiento y borrar la cuenta; editar el perfil y la contraseña y Mi actividad son **P1**) | Con cuenta | Registro, sesión, consentimiento, perfil, preferencias, borrar cuenta | Vistas de cuenta |
| G. Panel del administrador (P1) | Administrador (`admin`) | Atiende los tickets, ve a los agricultores con sus lotes y temporadas, borra y restaura con motivo, crea y bloquea usuarios, y consulta la bitácora y las métricas (HU-170) | Solo en escritorio, en `/admin`. Es un supuesto hasta decidir si el panel va en esta web o en una aparte (`specs/02-contratos.md`, «Roles») |
| Pie de página | Todos | Navega, abre las fuentes, la política o reporta un problema; sigue al equipo | Los cerros del paisaje y una franja de tierra facetada con marca, «Explorar», «Datos y cuenta», redes del equipo (GitHub, Instagram, LinkedIn, YouTube), enlace al sitio, «© 2026 RealE4Life. Todos los derechos reservados.» y «Hecho para el NASA Space Apps Challenge 2026». Va en las vistas largas (portada, resultado, señales, rotaciones, calendario sin cuenta, Mi cuenta, Mi actividad, la finca temporal y las cinco pestañas del lote: ahora, calendario, próxima siembra, agua e historial); también en entrar y crear cuenta, debajo del formulario (decidido por Felipe el 12 de octubre de 2026); no en los demás pasos de una sola tarea (buscar municipio, dibujar, editar o agregar un lote, elegir cultivo, registrar cosecha y siembra, guardar la finca temporal) ni en Mis lotes, donde el mapa ocupa la pantalla. «Reportar un problema» es P1 (HU-170): mientras no exista, el enlace no se dibuja; sin sesión lleva a «Entrar». Faltan las URL de las redes y el dominio |
| Transversal | Todos | — | Panel «¿Cómo funciona y de dónde sale esto?» (cómo se decide el semáforo, fuentes y versión de los datos, HU-122), estados, rótulo de ejemplo, condición en vivo, modo ligero y sonido (P1) |

### Sin cuenta y con cuenta

| Función | Sin cuenta | Con cuenta |
|---|---|---|
| Estrategias de rotación (MVP) | Sí: municipio, área y, a mano, el cultivo anterior | Sí, desde el lote: su suelo, su altitud, su riego y el historial real del terreno |
| Ciclo de una estrategia con su diagnóstico y su agua (MVP) | Sí; dice a mano si tiene riego. El área se usa solo para calcular y no se guarda | Sí; el riego y el suelo salen del lote |
| Qué cambió en su zona (MVP) | Sí | Sí |
| Diagnóstico suelto de una ventana (MVP) | Sí | Sí |
| Mapa del lote con capa de la NASA (MVP) | No | Sí |
| Lotes e historial de temporadas (MVP) | No | Sí, en una zona |
| Comparar ventanas («Planear una siembra») (P1) | Sí, desde la consulta | Sí, en cada lote |
| Plan de agua de la finca (P1) | La finca temporal, que se envía solo para calcular y no se guarda | Todos sus lotes, guardados |
| Varias zonas, progreso y «Restaurar» (P1) | No | Sí |
| Pasar a una cuenta | Al registrarse, el municipio, el área y el cultivo anterior que escribió se ofrecen para crear su primer lote. En P1, la finca temporal se ofrece para guardar: un lote con una temporada por cultivo | — |

### Progreso

El progreso es la parte de «juego», y solo refleja hechos registrados y reglas con fuente (R5, R8): temporadas registradas, rotaciones que cumplen las reglas de filtro, e hitos como «primera rotación con leguminosa». No hay puntajes inventados de «salud del suelo»: el suelo que se muestra es el estimado por SoilGrids, con su rango. El lote cambia visualmente con su historial.

### Flujos

**Flujos del MVP:**

1. **Invitado:** inicio → «Consultar sin cuenta» → entrada (municipio, área, cultivo anterior, fecha y riego) → estrategias de rotación → ciclo de una estrategia (diagnóstico, agua del plan, verdor) → qué cambió en su zona → invitación a crear cuenta para guardar su lote.
   - Sin estrategias válidas: estado vacío con las descartadas y su motivo, y la propuesta de cambiar la fecha o el número de ciclos.
   - Desde un ciclo con la acción «otra ventana»: mejores ventanas → diagnóstico de la ventana elegida.
   - Diagnóstico suelto: elegir cultivo y mes → resultado → con «rotar», «Ver estrategias de rotación».
2. **Usuario nuevo:** inicio → crear cuenta (consentimiento) → buscar municipio → dibujar el primer lote sobre el mapa con la capa de la NASA → Mi finca.
3. **Usuario que vuelve:** entra directo a Mi finca → abre un lote → «Ver estrategias de rotación» → ciclo → «Registrar esta siembra».
4. **Nueva temporada:** lote → registrar cosecha y siembra → «¿Qué había antes en este terreno?» (una o varias).

**Flujos anteriores** (lo que nombran del descenso, la finca temporal, «Planear una siembra», los cultivos alternativos, el progreso y «Restaurar» es P1):

1. **Invitado:** inicio → consultar sin cuenta → descenso → consulta (cultivo, cuándo sembrar y riego) → resultado de la ventana → finca temporal (opcional) → invitación a crear cuenta para guardar.
   - Si el cultivo no es apto para la zona: resultado «no se da en su zona» → elegir otro cultivo o ver qué sembrar.
   - Si la acción es «otra ventana»: mejores ventanas → diagnóstico de la ventana elegida, o «Planear una siembra» para comparar todas con sus prioridades.
   - Si la acción es «rotar»: cultivos alternativos → diagnóstico de uno de ellos en la misma fecha, o «Qué sembrar después».
   - En cualquier momento: mover sus prioridades → el semáforo y el orden de las ventanas se recalculan; si su luz difiere de la de AgroSense, se ven las dos.
2. **Usuario nuevo:** inicio → crear cuenta → descenso → primer lote → Mi finca.
3. **Usuario que vuelve:** entra directo a Mi finca, en el nivel de finca, sin descenso.
4. **Agregar lote:** Mi finca → mini descenso → nuevo lote.
5. **Nueva temporada:** lote → registrar cosecha y siembra → «¿Qué había antes en este terreno?» (una o varias) → el progreso se actualiza.
6. **Restaurar:** lote → historial → «Restaurar» en una temporada borrada hace menos de 30 días.

### Navegación

Una sola experiencia continua, con una URL por nivel y por lote, para que funcionen el botón atrás, los enlaces compartidos y los saltos directos a un caso en la demo.

### Pantallas por diseñar del MVP

Regla del proyecto: **cada pantalla se diseña y se aprueba en Figma antes de programarla** (con su generador en `design/pantallas/`). Faltan por diseñar, en móvil y en escritorio:

| # | Pantalla | HU | Notas |
|---|---|---|---|
| 1 | Entrada a las estrategias, sin cuenta y desde el lote | HU-214 | Municipio, área, cultivo anterior, fecha, riego y número de ciclos |
| 2 | Estrategias de rotación | HU-101, HU-102 | Tarjetas con ciclos, desglose, salud del suelo, descartadas a pedido y estado vacío |
| 3 | Ciclo de una estrategia | HU-215 | Reusa el resultado del diagnóstico; suma agua del plan, humedad del suelo y verdor; ciclo de descanso |
| 4 | Qué cambió en su zona | HU-219 | Dos periodos por mes, mejores ventanas de cada uno, «Sin datos suficientes» y cultivo no apto |
| 5 | Mapa del lote con capa de la NASA | HU-211 | Control de capas, atribución, fecha de la imagen y estado «GIBS no responde» |
| 6 | Política de tratamiento de datos | HU-163 | Pendiente de la tanda 11 |
| 7 | Editar o borrar una siembra | HU-165 | Pendiente de la tanda 11 |
| 8 | Lote sin dibujar | HU-164 | Pendiente de la tanda 11 |
| 9 | Estados que faltan del resultado | HU-092, HU-094 | Pendiente de la tanda 11 |
| 10 | Rotaciones sin opciones | HU-102 | Pendiente de la tanda 11; ahora es el estado vacío de las estrategias (se puede unir con la 2) |

También hay que revisar las pantallas ya diseñadas que cambian con el MVP: el inicio (sin 3D y con el flujo nuevo), Mi finca (una sola zona), el detalle 2D del lote (sin lote vivo) y Mi cuenta (sin editar perfil ni Mi actividad).

## Ambiente en vivo

**P1 desde el 11 de octubre de 2026** (HU-174 a HU-176): en el MVP no hay escena ni clima en vivo.

La escena refleja la condición aproximada de ahora en el municipio (decisión 7 de `docs/decisiones.md`). Es ambiente: nunca cambia un resultado.

| Condición | Origen | En la escena |
|---|---|---|
| Día, atardecer, noche | Calculado en el navegador con la hora y la posición del municipio | Luz, color del cielo, estrellas, luces de las casas |
| Lluvia | `GET /api/v1/conditions` (Open-Meteo, a partir de modelos) | Partículas de lluvia y charcos según intensidad |
| Nubes | Mismo endpoint | Cobertura y sombra de nubes |
| Viento | Mismo endpoint | Movimiento de cultivos, árboles y niebla según velocidad y dirección |
| Temperatura | Mismo endpoint | Solo como dato en el rótulo |

- Rótulo discreto: «Condición aproximada en <municipio> · <fuente> · <hora>».
- Sin datos del proveedor: clima neutro y rótulo «sin condición en vivo». Nunca se inventa.
- Con «reducir movimiento», los efectos quedan quietos; en modo ligero, la condición se muestra con un ícono.

## Principios de diseño

**Decisiones de pantalla del 11 de octubre de 2026** (se aplican en todas las vistas):

- **Dos juegos de prioridades.** «¿Qué le importa al elegir la fecha?» (seis pesos, uno por señal) y «¿Qué busca en la rotación?» (agua, suelo, ingreso y riesgo) conviven con nombres y paneles distintos. Más adelante se pueden unificar.
- **Dónde se ajustan.** Un resumen plegado, «Criterio de AgroSense · Ajustar» (o «Sus prioridades · Ajustar»), en la consulta, el resultado y el calendario. Abre los seis controles de cinco semillas. Con cuenta se guardan en el perfil; sin cuenta, en el navegador.
- **Dos luces.** Cuando difieren, «Con sus prioridades» va primero y más grande, y «Con el criterio de AgroSense» al lado, nunca escondida. Una línea dice por qué difieren («Usted puso la oferta en 0»). Cada luz dice cuál es su factor que más limita.
- **Número de una ventana.** El principal es la nota del factor que más limita; el secundario, el promedio con sus prioridades.
- **Cultivo no apto.** Letrero propio, «No se da en su zona», sin semáforo: la nota de aptitud de 0 a 100, la escala de cinco semillas, la razón (la altitud frente a la ficha) con su fuente, «Elegir otro cultivo» y las alternativas.
- **Agua sin riego.** En un lote sin riego, el déficit no se dice «riego probable» sino «En estos meses la lluvia no alcanza: el cultivo pasaría sed». Vale en todas las vistas del lote: Mis lotes, lote vivo, calendario y agua.
- **Historial.** Una línea de tiempo con bifurcaciones (un terreno se divide) y uniones (varios se juntan). En móvil, una lista por siembra con «viene de…».

**Decisiones del MVP del 11 de octubre de 2026 (decisión 12):**

- **Las estrategias de rotación son la entrada.** El diagnóstico es la revisión de cada ciclo.
- **La salud del suelo no es una predicción.** Sus cuatro criterios llevan nivel con forma y texto, razón y fuente, y el rótulo «Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo».
- **«Qué cambió» no es un pronóstico.** Lleva siempre «Así fue en la historia de su zona. No es un pronóstico», con los años y la fuente de cada periodo.
- **La NASA se ve en pantalla.** Cada resultado nombra su producto (POWER, IMERG, NASADEM, MODIS, SMAP) y el mapa del lote lleva la capa GIBS. De POWER se dice que es un reanálisis.
- **La humedad del suelo y el verdor son de la zona,** no del lote: llevan su resolución (R10).
- **La oferta es valor agregado:** una señal más dentro del ciclo, nunca la portada.
- **2D por defecto.** La escena 3D, el descenso, el lote vivo y las animaciones de la mascota por partes (HU-172) son P1. El inicio sí tiene recorrido con scroll (GSAP y Lenis), la Tierra girando en un lienzo 2D y la mascota volando entre paradas: no usan three.js y se apagan con «reducir movimiento».

1. **El dato manda.** Semáforo, acción, razones, limitaciones y cifras van en HTML legible por encima del canvas, nunca dibujados dentro de la escena 3D.
2. **El 3D es una mejora.** Sin WebGL, en modo ligero o con «reducir movimiento», la app funciona completa en 2D.
3. **Las reglas también son de diseño:**
   - R1: «datos insuficientes» y «no evaluable» se ven distintos de «desfavorable» (forma, patrón y texto; nunca rojo). En el paisaje se representan como niebla o trazo punteado, no como daño.
   - R5: los datos de ejemplo llevan rótulo visible en pantalla.
   - R9: sin cuenta, la finca se envía solo para calcular y no se guarda; con cuenta, se guarda solo tras el consentimiento y se puede borrar desde la app.
   - R10: todo resultado de riego lleva «Estimación con el clima de la zona. Verifique la humedad del suelo en su lote» y se muestra en rangos. El suelo lleva «Estimación de un mapa global de 250 m. Un análisis de suelo de su lote es más preciso» y se muestra con su rango.
   - `not_applicable` (por ejemplo, heladas o calor en un cultivo que no los sufre) se muestra como «No aplica», distinto de «datos insuficientes» y de «desfavorable».
   - R3: un cultivo que no es apto para la zona no es un semáforo rojo más: la pantalla dice «Este cultivo no se da en su zona», con el dato de la ficha y su fuente, y no dibuja señales ni ventanas.
   - R2: una ventana de alto riesgo se rotula «Alto riesgo» con forma y texto, va después de las demás y nunca entre las mejores, por alto que sea su balance.
   - El orden de las ventanas lleva siempre «Según la historia de la zona. No es un pronóstico»: es una comparación para que decida el agricultor.
   - La señal de agua dice si se evaluó con riego o sin riego; con riego, el riego que haría falta va en rango y con el rótulo de estimación (R10).
   - Prioridades: cuando la luz con las prioridades del agricultor y la de AgroSense difieren, se muestran las dos con forma y texto; nunca se esconde la de AgroSense. Una señal que no cuenta con sus prioridades se sigue viendo, rotulada; un riesgo grave de clima con peso 0 lleva «Cuenta siempre: riesgo grave» (decisión 10).
   - Varias fuentes: los valores de un indicador que vienen de distintas fuentes se muestran juntos, cada uno con su origen y su fecha, y se marca cuál calculó la señal. Nunca se dibuja un valor combinado (decisión 11, R8).
   - Las sugerencias (mejores ventanas, cultivos alternativos, rotaciones) son información: el texto nunca ordena sembrar.
   - Ningún botón o control sin función: cada uno lleva a una acción, un endpoint o una navegación definida.
   - W2: el estado nunca depende solo del color.
4. **Cada acción tiene respuesta.** Tocar, elegir y cambiar prioridades produce un cambio visible inmediato.
5. **Español claro, sin jerga.** La jerga técnica vive en el glosario y en el detalle a pedido.

## Accesibilidad y rendimiento

Metas iniciales; se validan y ajustan con el prototipo.

| Tema | Meta |
|---|---|
| Ancho mínimo | 360 px sin desplazamiento horizontal (HU-096) |
| Accesibilidad | WCAG 2.2 AA; contraste de texto ≥ 4,5:1; foco visible; objetivos táctiles ≥ 44 px |
| Movimiento | Respeta `prefers-reduced-motion`; ninguna información depende de una animación |
| Audio | Apagado por defecto, con control visible; la app se entiende sin sonido |
| JS inicial | ≤ 200 KB comprimido, sin contar la escena 3D |
| Escena 3D | Se carga después de la primera pintura; ≤ 3 MB transferidos en total; modelos comprimidos |
| Carga | LCP ≤ 2,5 s en 4G lento simulado |
| Fluidez | ≥ 30 fps en un Android de gama media; si no se alcanza, pasa sola a modo ligero |

## Stack

Fijar versiones exactas al crear `web/`.

| Capa | Elección | Por qué |
|---|---|---|
| Base | React, TypeScript y Vite | FastAPI sirve el build estático en una sola imagen; no hace falta servidor Node |
| 3D | three.js con React Three Fiber y drei | Low-poly con sombreado plano es barato de renderizar y es la estética buscada |
| Animación | GSAP (ScrollTrigger, SplitText, Flip) con `@gsap/react` | Línea de tiempo precisa para cámara, scroll y UI; GSAP es gratuito con todos sus plugins |
| Scroll | Lenis | Scroll suave que se integra con R3F y ScrollTrigger |
| Rutas | React Router (modo de datos: `createBrowserRouter`), con cada página cargada aparte | Páginas con dirección propia, parámetros (`/lote/:id`) y rutas protegidas por sesión sin escribirlo a mano. Las direcciones viven en `web/src/app/paths.ts` |
| Estado | Zustand (escena y cámara) y TanStack Query (API) | Zustand comparte estado entre DOM y canvas sin re-render de todo el árbol |
| UI | Tailwind y componentes propios en estilo diorama low-poly (`web/src/components/ui/`, pieza base `Plate`); primitivas de Radix solo donde hagan falta (diálogos, menús) | Control total de la silueta biselada; Radix aporta accesibilidad en lo complejo |
| Gráficas | SVG propio animado con GSAP | Pocas gráficas (agua de la ventana, área sembrada, calendario de agua) y control total del estilo |
| Audio | Efectos de interfaz y música de fondo con Web Audio (`web/src/lib/sound.ts`), sin dependencias, con un solo control en la barra (`SoundToggle`). La música es un archivo si `VITE_MUSIC_URL` lo indica; si no, una melodía generada. Howler.js queda para el ambiente por escena (P1) | El sonido entra ya con la opción de quitarlo; el ambiente necesita assets con licencia |
| Sesión | Cookie de sesión de la API (sin librería extra) | Registro e inicio de sesión con usuario y contraseña contra `/api/v1/auth` |
| Datos | `openapi-typescript` y MSW | Igual que el resto del proyecto: tipos del contrato y respuestas simuladas |
| Assets 3D | glTF comprimido con `gltf-transform` | Un solo formato liviano |
| Tierra del inicio | Continentes reales de Natural Earth 1:110m (paquete `world-atlas`, dominio público), facetados como el kit y con el color de cada faceta tomado de la imagen Blue Marble de la NASA. `design/globo/build_globo.py` exporta la malla a `web/src/assets/globe.json` y la web la gira y la proyecta en un lienzo 2D (`components/globe/Earth.tsx`), sin three.js ni `d3-geo`; la versión 3D con React Three Fiber es P1. En reposo gira de oeste a este; al bajar frena con la región piloto al frente (hoy Colombia, supuesto hasta que el reto confirme la región, decisión 11) y empieza el descenso | Fiel a la geografía real y ligada a los datos de la NASA, sin salir del estilo low-poly. Diseño en `design/globo/` |
| Mapa del lote | MapLibre GL JS con Terra Draw (adaptador de MapLibre) para dibujar el contorno; mapa base OpenStreetMap (OpenFreeMap) y capas WMTS de NASA GIBS (imagen satelital y NDVI, HU-211) | Dibujar el lote sobre el mundo real y centrar en el municipio, y que la NASA se vea en pantalla. Licencias abiertas y sin clave de API para el mapa base; las capas, su resolución y las condiciones de uso de GIBS se verifican en HU-211 |
| Diseño | Figma (conectado por el MCP TalkToFigma) | Moodboard, tokens, componentes y pantallas |
| Calidad | ESLint, Prettier y Vitest; las pruebas corren en Docker | Configuración mínima y el mismo entorno para todos |
| Pruebas de scroll | `playwright-core` con el Chrome del equipo (`npm --prefix web run test:scroll`). Solo en la fase 0 y fuera de Docker y de CI | Los recorridos con GSAP y Lenis dependen de tiempos reales de cuadro: scroll brusco, táctil, teclado y cambio de tamaño no se pueden comprobar con Vitest |
| Lenguaje | TypeScript 6.0 | `typescript-eslint` aún no soporta la 7; se sube cuando lo haga |

### Carpetas de `web/`

Páginas en `pages/` y piezas reutilizables en `components/`. El detalle y las reglas de React del proyecto están en `web/README.md`.

| Carpeta | Qué va |
|---|---|
| `src/app/` | Arranque, rutas (`routes.tsx`) y direcciones (`paths.ts`) |
| `src/pages/<página>/` | Una pantalla con dirección propia: solo compone. Sus tramos y sus textos viven con ella |
| `src/components/` | Lo que usan dos páginas o más: `ui/` (el kit), `layout/` (barra, pie, scroll suave), `mascot/` y `globe/` |
| `src/hooks/` y `src/lib/` | Lógica sin JSX: con React y sin React |
| `src/api/` y `src/features/<dominio>/` | Tipos del contrato y respuestas simuladas; lo propio de un dominio (cuentas, lotes, estrategias). Se crean con su primera pieza |

Las páginas de prueba de la fase 0 (el kit y los tres recorridos) están en `pages/lab/`. No se enlazan desde la app: se entra escribiendo la dirección (`/pruebas`, `/kit`, `/recorrido/1` a `/recorrido/3`).

Un enlace a una pantalla diseñada que aún no está programada lleva a una página que lo dice (`pages/pending/`), para que ningún control quede sin función.

**Descartado por ahora:** Recharts (cuesta adaptarlo al estilo), MapLibre para la vista regional (la cubre el descenso; MapLibre sí entra para dibujar el lote), Next.js y Astro (no hay servidor Node en el despliegue).

## Modo simulación

**P1 desde el 11 de octubre de 2026** (HU-014). En el MVP, las respuestas simuladas de HU-013 y un parámetro de la URL bastan para forzar cada estado.

Un modo para que quien desarrolla vea y pruebe cada caso sin depender de la API real, la base de datos ni el clima en vivo (subsistema S5, HU-014).

| Variable | Dónde | Qué activa |
|---|---|---|
| `VITE_SIMULATION=true` | Web | MSW responde todos los endpoints (cálculo, cuentas y condiciones) y aparece el panel de simulación |
| `AGROSENSE_SIMULATION=true` | Backend | Usuario simulado sin iniciar sesión y base de datos de ejemplo, para probar la integración real |

**Panel de simulación** (flotante, se abre con un atajo de teclado):

| Grupo | Controles |
|---|---|
| Resultado | Luz verde, amarilla, roja o no evaluable; roja por helada o calor críticos; cultivo no apto para la zona; aptitud sin datos; acción «otra ventana» con mejores ventanas y sin ninguna; ventana de alto riesgo; con riego y sin riego; mercado sin datos; suelo sin datos; calor sin datos; heladas «no aplica»; señal con calidad `partial`; dos luces distintas (sus prioridades frente a las de AgroSense); riesgo grave con peso 0; acción «rotar» con alternativas y sin ninguna; oferta con dos fuentes que no coinciden |
| Historial | Terreno dividido en dos y dos partes juntadas en una; temporada borrada que se puede restaurar |
| Red | Respuesta lenta, error 422, error 500, sin conexión |
| Usuario | Invitado; usuario nuevo sin lotes; usuario con 3 lotes en 2 zonas; usuario con historial largo |
| Tiempo | Saltar temporadas para ver el progreso; fijar fecha y hora |
| Clima en vivo | Día, atardecer o noche; lluvia, nubes y viento con intensidad; sin condición en vivo |
| Escena | Modo ligero, «reducir movimiento», contador de fps, posición de cámara, repetir el descenso |
| Mascota | Forzar cada expresión |

**Reglas:**

- Mientras está activo, una franja visible dice «Modo simulación · datos de ejemplo» (R5).
- El build de producción no incluye MSW ni el panel; el CI falla si `VITE_SIMULATION` está activo en producción.
- El backend se niega a arrancar si `AGROSENSE_SIMULATION` está activo junto con la configuración de producción.

## Assets y licencias

En el espíritu de R8, cada asset tiene autor, licencia y enlace en `web/public/assets/CREDITS.md`.

| Fuente | Qué aporta | Licencia | Nota |
|---|---|---|---|
| Quaternius LowPoly Crops | Cultivos en 5 etapas de crecimiento | CC0 | Viene en FBX/OBJ; se convierte a glTF |
| Kenney Nature Kit | Árboles, rocas, terreno, plantas | CC0 | — |
| Generados en código | Terreno, parcelas, cielo, efectos | Propios | Procedurales con three.js |
| Mascota satélite | Modelo 3D y versión 2D | Propios | Diseño original del equipo (HU-171) |

Solo se usan assets con licencia que permita uso y modificación. Si un asset se genera con un servicio de IA, se registra el servicio y sus términos.

## Método de motion

Adaptado de las técnicas para animaciones con Claude Opus 5.5 que circulan en X.

1. **Storyboard antes de animar.** Una tabla por secuencia: tiempo, qué se ve, para qué, cómo sale y qué objeto pasa a la siguiente toma.
2. **Primero lo compartido.** Colores, tipografías, modelos y posiciones de enlace entre escenas; luego cada escena como componente con su página de prueba.
3. **Crítico fresco.** Quien construye no juzga su obra: otro agente, sin contexto de la construcción, revisa capturas y devuelve problemas ordenados.
4. **Animación determinista.** Todo valor animado es función del tiempo de la línea de tiempo de GSAP; nada de temporizadores ni aleatoriedad sin semilla. Así la misma secuencia se puede renderizar como video de respaldo (HU-132).
5. **Reglas de escena:** cámara entre 35° y 55°; luz principal suave lateral y luz de contorno; etiquetas en HTML posicionadas desde la escena; 3D solo donde explica algo espacial.

## Skills y agentes

| Skill | Uso | Estado |
|---|---|---|
| [`greensock/gsap-skills`](https://github.com/greensock/gsap-skills) | Oficial de GSAP: core, timeline, ScrollTrigger, plugins, React, rendimiento | Elegida; se instala al crear `web/` |
| `anthemflynn/ccmp` (skill `react-three-fiber`) | R3F, drei, física y postprocesado | Elegida; se instala al crear `web/` |
| [`majidmanzarpour/threejs-game-skills`](https://github.com/majidmanzarpour/threejs-game-skills) | Ideas de UI de juego, QA y audio | Solo referencia (three.js sin R3F) |
| `agrosense-motion` | El método de motion de esta página como skill del proyecto | Se crea en HU-156 |
| `frontend-design`, `web-animations`, `ui-ux-pro-max` | Fundamentos de diseño y animación | Instaladas |

Toda skill de terceros se lee antes de instalarla: son instrucciones que se ejecutan con los permisos de quien la usa.

## Decisiones

Las decisiones de frontend tomadas (estilo, inicio, navegación, audio, skills) están en `docs/registro-de-decisiones.md`. La paleta y las tipografías salen de HU-151 y HU-152.
