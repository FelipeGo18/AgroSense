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
- Tiene una versión 2D (`Mascot` en `web/src/components/`) para la interfaz, el modo ligero, los estados y los íconos, y tendrá una 3D para la escena.
- Sus expresiones refuerzan el resultado; nunca son la única forma de comunicarlo.
- Es original: no copia a ningún satélite ni personaje de marca existente.

## Mapa de la web

### Modelo

**Usuario → zonas (municipios) → lotes → temporadas.** Un usuario con cuenta puede tener varios lotes en varias zonas. Un lote grande puede tener varios cultivos a la vez: cada temporada ocupa una parte de su área y sabe qué había antes en ese terreno. El agricultor divide y junta partes como trabaja: una temporada puede venir de una o varias anteriores y tener varias sucesoras, así que el historial de un lote es una red de terrenos que se dividen y se juntan, no una sola fila. Cada temporada registra un cultivo, su parte del área, sus fechas y el diagnóstico que se vio al sembrar. Sin cuenta, hay una sola **finca temporal** en el dispositivo: área total y porcentaje por cultivo.

### Partes

| Parte | Quién | Qué hace el usuario | Qué ve |
|---|---|---|---|
| A. Inicio | Todos | Conoce AgroSense; elige consultar sin cuenta o entrar | La mascota presenta qué es AgroSense y las tres cosas que hace |
| B. Descenso | Invitado y usuario nuevo | Busca su municipio (satélite) y lo ve entre sus vecinos (región). Con cuenta, al llegar al municipio dibuja su primer lote en el mapa real, le pone nombre, dice si tiene riego y registra el cultivo y la fecha de siembra (HU-164) | La cámara baja guiada por la mascota hasta el municipio o hasta el lote |
| C. Consulta | Todos | Elige cultivo, cuándo sembrar (un mes de los próximos doce y, si quiere, una semana) y si tiene riego; si quiere, mueve sus prioridades (un peso de 0 a 5 por señal, que empiezan en los de AgroSense, con «Volver al criterio de AgroSense»); para «qué sembrar después», sin cuenta elige a mano el cultivo anterior | Si el cultivo no se da en su zona, la pantalla lo dice con su razón y ofrece elegir otro. Si se da: acción sugerida primero; luego el semáforo de esa ventana de siembra con sus prioridades y, si el de AgroSense da otra luz, las dos lado a lado («Con sus prioridades: verde · Con el criterio de AgroSense: amarillo»); las seis señales (agua, heladas, calor, suelo, oferta y mercado) con su calificación de 0 a 100, cuáles no cuentan con sus prioridades y «Lo que más limita»; las fuentes de un indicador juntas, con la usada marcada y las demás «para contrastar»; razones, limitaciones y gráficas. Con la acción «otra ventana», las mejores ventanas de los próximos doce meses y el acceso a «Planear una siembra». Con «rotar», hasta tres cultivos alternativos que en esa ventana salen bien en clima y tienen mejor oferta. Ranking de rotaciones con desglose. Rótulo: «Es información para decidir. La decisión es suya» |
| D. Mi finca | Con cuenta (inicio de quien vuelve); sin cuenta, la finca temporal | Con cuenta: recorre sus lotes, cambia de zona y abre un lote. Sin cuenta: registra área y porcentaje por cultivo | El mapa real con sus lotes, cada uno con sus cultivos y etapas; sin cuenta, la finca temporal con su plan de agua |
| D0. Mis lotes | Con cuenta | Ve todos sus lotes en el mapa real y abre uno | Polígonos con los cultivos y las etapas de cada lote, avisos de riego o helada, y agregar lote |
| D1. Lote · ahora | Con cuenta | Recorre el diorama (arrastrar y acercar), toca un cultivo para elegirlo, mueve la línea de tiempo o la reproduce | El lote vivo (HU-187): diorama de cubos de tierra juntos, en el que cada cultivo ocupa tantos cubos como su parte del área, cada uno según su arquetipo y su etapa, dentro de una finca de bloques (casa, cerca con faroles, huerta, árbol y un perro acostado), el clima de ahora animado (viento que pasa, lluvia que cae, nubes, estrellas, escarcha y una mariposa ocasional), el suelo seco si es probable regar, y la línea de tiempo de la siembra a la cosecha (observada hasta el último dato de temperatura y estimada con un año normal después). En modo ligero o con movimiento reducido, la escena es estática. Guion en Figma («Ambiente del lote vivo») | Cultivo, etapa y días desde la siembra; su suelo estimado (pH, carbono orgánico, textura) con rango y rótulo de estimación |
| D1b. Lote · calendario | Con cuenta; sin cuenta, desde la consulta | Elige un cultivo y la lectura; mueve sus prioridades; toca un mes para ver sus semanas y sus razones | Dos lecturas. «Mi cultivo» (si ya está sembrado): de la siembra a la cosecha estimada, la etapa de cada mes, las heladas y el calor con «Vigile» en las etapas sensibles y el riego probable; en P1, abonar, labores y cosecha, gota y vender. «Planear una siembra» (parte libre, otro cultivo o sin cuenta): las ventanas de siembra de los próximos doce meses ordenadas primero por lo que más limita a cada una y, entre parecidas, por sus prioridades (las mismas seis de la consulta), con el factor limitante de cada ventana, las de alto riesgo aparte, la calificación de cada señal y, al tocar un mes, el detalle por semanas. Si el cultivo no se da en la zona, lo dice y ofrece elegir otro. Rótulo: «Según la historia de la zona. No es un pronóstico» |
| D2. Lote · próxima siembra | Con cuenta | Elige la parte del lote que va a sembrar, responde «¿Qué había antes en este terreno?» eligiendo una o varias temporadas cosechadas (o «Nada: es la primera siembra aquí») y mueve sus prioridades (agua, suelo, ingreso y riesgo) | El historial real de ese terreno (los cultivos de todas las temporadas de las que viene) y el suelo del lote; el diagnóstico de la siguiente ventana para la mejor opción; qué sembrar después, ordenado por sus prioridades, con las opciones excluidas a pedido. En P1, los riesgos que cubre un seguro (HU-188) y la lluvia en años de El Niño y La Niña (HU-189) |
| D3. Lote · agua | Con cuenta | Revisa el plan | Calendario de riego del lote y total de la zona, con rangos y rótulo de estimación |
| D4. Lote · historial y progreso | Con cuenta | Registra cosecha y nueva siembra; restaura una temporada borrada | Línea de tiempo de temporadas con sus divisiones y uniones, cada relación con su rotación (cumple o qué reglas viola, sin castigo) e hitos. Aparte, lo borrado hace menos de 30 días con «Borrada · se puede restaurar hasta <fecha>» y el botón «Restaurar» |
| E. Agregar lote o zona | Con cuenta | Agrega un lote en su zona o en otro municipio | Mini descenso desde la finca al nuevo municipio |
| F. Cuenta | Con cuenta | Registro, sesión, consentimiento, perfil, preferencias, borrar cuenta | Vistas de cuenta |
| Pie de página | Todos | Navega, abre las fuentes, la política o reporta un problema; sigue al equipo | Los cerros del paisaje y una franja de tierra facetada con marca, «Explorar», «Datos y cuenta», redes del equipo (GitHub, Instagram, LinkedIn, YouTube), enlace al sitio y «© 2026 RealE4Life. Todos los derechos reservados.». Va en las vistas largas (portada, resultado, señales, rotaciones, calendario sin cuenta, Mi cuenta, Mi actividad, la finca temporal y las cinco pestañas del lote: ahora, calendario, próxima siembra, agua e historial); no en los pasos de una sola tarea (entrar, crear cuenta, buscar municipio, dibujar, editar o agregar un lote, elegir cultivo, registrar cosecha y siembra, guardar la finca temporal) ni en Mis lotes, donde el mapa ocupa la pantalla. Faltan las URL de las redes y el dominio |
| Transversal | Todos | — | Panel «¿Cómo funciona y de dónde sale esto?» (cómo se decide el semáforo, fuentes y versión de los datos, HU-122), estados, rótulo de ejemplo, condición en vivo, modo ligero y sonido (P1) |

### Sin cuenta y con cuenta

| Función | Sin cuenta | Con cuenta |
|---|---|---|
| Diagnóstico de una ventana de siembra | Sí; dice a mano si tiene riego | Sí; el riego y el suelo salen del lote |
| Comparar ventanas («Planear una siembra») | Sí, desde la consulta | Sí, en cada lote |
| Qué sembrar después | Sí, eligiendo a mano el cultivo anterior | Sí, con el historial real de la parte del lote que va a sembrar |
| Plan de agua | La finca temporal, que se envía solo para calcular y no se guarda | Todos sus lotes, guardados |
| Varios lotes y zonas | No | Sí |
| Historial y progreso | No | Sí |
| Pasar a una cuenta | Al registrarse, la finca temporal se ofrece para guardar: un lote con una temporada por cultivo, cada una con su parte del área | — |

### Progreso

El progreso es la parte de «juego», y solo refleja hechos registrados y reglas con fuente (R5, R8): temporadas registradas, rotaciones que cumplen las reglas de filtro, e hitos como «primera rotación con leguminosa». No hay puntajes inventados de «salud del suelo»: el suelo que se muestra es el estimado por SoilGrids, con su rango. El lote cambia visualmente con su historial.

### Flujos

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

## Ambiente en vivo

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
- **Cultivo no apto.** Letrero propio, «No se da en su zona», sin semáforo: la nota de aptitud de 0 a 100, la escala de cinco semillas, la razón (altitud o temperatura frente a la ficha) con su fuente, «Elegir otro cultivo» y las alternativas.
- **Agua sin riego.** En un lote sin riego, el déficit no se dice «riego probable» sino «En estos meses la lluvia no alcanza: el cultivo pasaría sed».
- **Historial.** Una línea de tiempo con bifurcaciones (un terreno se divide) y uniones (varios se juntan). En móvil, una lista por siembra con «viene de…».

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
| Estado | Zustand (escena y cámara) y TanStack Query (API) | Zustand comparte estado entre DOM y canvas sin re-render de todo el árbol |
| UI | Tailwind y componentes propios en estilo diorama low-poly (`web/src/components/`, pieza base `Plate`); primitivas de Radix solo donde hagan falta (diálogos, menús) | Control total de la silueta biselada; Radix aporta accesibilidad en lo complejo |
| Gráficas | SVG propio animado con GSAP | Pocas gráficas (agua de la ventana, área sembrada, calendario de agua) y control total del estilo |
| Audio (P1) | Howler.js | Ambiente y efectos de interfaz con control de volumen y silencio |
| Sesión | Cookie de sesión de la API (sin librería extra) | Registro e inicio de sesión con usuario y contraseña contra `/api/v1/auth` |
| Datos | `openapi-typescript` y MSW | Igual que el resto del proyecto: tipos del contrato y respuestas simuladas |
| Assets 3D | glTF comprimido con `gltf-transform` | Un solo formato liviano |
| Tierra del inicio | Continentes reales de Natural Earth 1:110m (paquete `world-atlas`, dominio público), facetados como el kit y con el color de cada faceta tomado de la imagen Blue Marble de la NASA. En 3D, una icosfera con React Three Fiber que gira; en modo ligero, la misma Tierra en SVG con proyección ortográfica de `d3-geo`. En reposo gira de oeste a este; al bajar frena con la región piloto al frente (hoy Colombia, supuesto hasta que el reto confirme la región, decisión 11) y empieza el descenso | Fiel a la geografía real y ligada a los datos de la NASA, sin salir del estilo low-poly. Diseño en `design/globo/` |
| Mapa del lote | MapLibre GL JS con Terra Draw (adaptador de MapLibre) para dibujar el contorno; mapa base OpenStreetMap (OpenFreeMap) y capa satelital por definir tras revisar su licencia | Dibujar el lote sobre el mundo real y centrar en el municipio. Licencias abiertas y sin clave de API para el mapa base |
| Diseño | Figma (conectado por el MCP TalkToFigma) | Moodboard, tokens, componentes y pantallas |
| Calidad | ESLint, Prettier y Vitest; las pruebas corren en Docker | Configuración mínima y el mismo entorno para todos |
| Pruebas de scroll | `playwright-core` con el Chrome del equipo (`npm --prefix web run test:scroll`). Solo en la fase 0 y fuera de Docker y de CI | Los recorridos con GSAP y Lenis dependen de tiempos reales de cuadro: scroll brusco, táctil, teclado y cambio de tamaño no se pueden comprobar con Vitest |
| Lenguaje | TypeScript 6.0 | `typescript-eslint` aún no soporta la 7; se sube cuando lo haga |

**Descartado por ahora:** Recharts (cuesta adaptarlo al estilo), MapLibre para la vista regional (la cubre el descenso; MapLibre sí entra para dibujar el lote), Next.js y Astro (no hay servidor Node en el despliegue).

## Modo simulación

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
