---
id: EP-17
titulo: "Inicio, mascota y paisaje vivo"
prioridad: P0
fase: [Fase 0, Evento]
rol: "Web, con Motor y API"
agentes: [web, motor-api]
subsistemas: [W8, M9]
depende_de: [HU-151]
reglas: [R1, R5, R8]
estado: en curso
---

# EP-17 · Inicio, mascota y paisaje vivo

**Resultado esperado:** Quien entra entiende en segundos qué es AgroSense y empieza a usarlo, con la mascota satélite en su versión estática. En P1, la mascota se anima y el paisaje refleja si en el municipio es de día o de noche, si llueve o si hay viento, sin que eso cambie ningún resultado.

**Recorte del MVP (11 de octubre de 2026):** queda en P0 la pantalla de inicio sin 3D (HU-173), con la mascota en su versión 2D ya diseñada, que guía el recorrido volando entre paradas. Pasaron a P1 el diseño final y las animaciones de la mascota (HU-171, HU-172) y el clima en vivo en la escena (HU-174 a HU-176).

## Historias de usuario

### HU-173 · Pantalla de inicio

- **Historia:** Como visitante, quiero entender en segundos qué es AgroSense y qué hace, para decidir si la uso.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] La mascota (`Mascot` 2D) presenta qué es AgroSense y lo que hace con cuatro preguntas: qué siembro y en qué orden (estrategias de rotación), si conviene cada siembra (la revisión de cada ciclo), cuánta agua va a necesitar (el agua del plan) y qué cambió en su zona
  - [x] El inicio es un recorrido de paradas con scroll suave (GSAP y Lenis): portada, «Cuatro preguntas», «Así se revisa un ciclo» y «De dónde salen los datos». Se avanza con el scroll, con el enlace de cada parada o con los puntos del borde, que dicen en cuál va; al llegar, el foco queda en el título de la parada
  - [x] La mascota guía el recorrido: cada parada le reserva un lugar y una sola mascota vuela de uno al siguiente; si el lugar no se ve, espera en una esquina. Lo que dice va escrito al lado (nunca es la única señal)
  - [x] La Tierra gira de fondo en la portada (continentes reales, en un lienzo 2D); al bajar frena con la región piloto al frente y se acerca. Fuera de la pantalla deja de dibujarse
  - [x] Botones «Consultar sin cuenta» y «Entrar». Mientras su pantalla no esté programada llevan a una página que lo dice; «Consultar sin cuenta» irá a la entrada de las estrategias (HU-214)
  - [ ] Habla de AgroSense, no del problema ni de NASA
  - [x] Sin escena 3D ni three.js: la pantalla es 2D (HU-158)
  - [x] Usable a 360 px y con «reducir movimiento»: sin scroll suave, giro ni vuelo; cada parada muestra su mascota quieta
  - [x] El resultado de muestra va rotulado como ejemplo (R5) y la señal sin datos no se pinta como riesgo (R1)
  - [x] Ningún enlace sin destino: «Reportar un problema» (P1) y las redes sin dirección no se dibujan. Las direcciones de las redes salen de las variables `VITE_SOCIAL_*` (`web/.env`), no del código
  - [x] Sonido de la interfaz con su control en la barra: arranca apagado, se prende y se quita con un botón que dice su estado, y la preferencia se recuerda en el navegador. Suena al prenderlo y al pasar de una parada a otra, y pone música de fondo: un archivo si `VITE_MUSIC_URL` lo indica o, si no, una melodía generada por la web. Con la pestaña escondida la música se calla. La página se entiende igual sin sonido
  - [x] La Tierra se puede girar arrastrándola con el ratón o con el dedo (en táctil, el arrastre vertical sigue haciendo scroll); al soltarla retoma su giro
  - [x] Las piezas de cada parada entran y salen con una animación sutil de GSAP, distinta en cada una: la portada llega de lado, las preguntas suben, el ejemplo entra por los dos lados y las fuentes aparecen creciendo. Con «reducir movimiento» no hay ninguna
- **Reglas que aplican:** R5
- **Notas:** Programada el 11 de octubre de 2026 en `web/src/pages/landing/` desde el diseño de Figma (`design/pantallas/inicio.py`), con el recorrido, la mascota guía y la Tierra girando pedidos por Felipe. Ajustada el 11 de octubre de 2026 al flujo del MVP (decisión 12). El registro de decisiones dice que el inicio «no habla de NASA»; con la NASA en el núcleo, nombrar los datos de la NASA en una línea del inicio queda por decidir (`docs/registro-de-decisiones.md`).

### HU-171 · Diseño de la mascota satélite

- **Historia:** Como equipo, quiero una mascota satélite tecnológica y tierna, para que AgroSense tenga una cara reconocible.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] Bocetos y versión final en Figma, en 2D y como modelo 3D low-poly
  - [x] Original: no se parece a un satélite ni personaje de marca existente
  - [x] Legible a 48 px en su versión 2D
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. El MVP usa la versión estática 2D ya diseñada. Elegida la **Semilla Sputnik**: una semilla germinando dibujada como caricatura de los años 60 (tinta gruesa, ojos de pastel, brazos de manguera). Las raíces son las antenas barridas, el brote es la antena de señal y las hojas son los paneles. La identidad está en la cara, los brazos, las raíces y el brote; **la semilla puede cambiar según el contexto** (germinada, frijol, maíz y las que se agreguen, por ejemplo según el cultivo consultado). Su estilo se aleja a propósito del low-poly: es «otro material» que viaja por el paisaje. Bocetos en Figma (tres rondas: tres conceptos, nueve estilos y la fusión elegida) y en `design/mascota/`; las propuestas descartadas se conservan. Versión 2D en código: `web/src/components/mascot/Mascot.tsx`, con una clase por parte animable. Falta: versión final por capas con puntos de giro en Figma y el modelo 3D.

### HU-172 · Expresiones y animaciones de la mascota

- **Historia:** Como usuario, quiero que la mascota reaccione a lo que pasa, para sentir que la app me acompaña.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Expresiones: reposo, guía, celebra (verde), duda (amarillo), preocupada (rojo), sin datos (no evaluable), cargando, error
  - [ ] «Sin datos» no se parece a «preocupada» (R1)
  - [ ] La expresión acompaña al texto; nunca es la única señal
- **Reglas que aplican:** R1
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. Adelanto del 12 de octubre de 2026 (fase 0), en los formularios de entrar, crear cuenta y cambiar contraseña (`web/src/components/mascot/reactions.ts` y `SceneLife.tsx`): la mascota mira el campo donde se escribe, se tapa los ojos en la contraseña y espía cuando está a la vista, dice que no cuando la API rechaza, celebra al entrar o crear la cuenta, brinca si la tocan, bosteza y se duerme tras 45 s sin actividad, y reacciona a una mariposa y al viento. Gestos nuevos: atenta, tapándose los ojos, espiando, negando, bostezando y dormida. Todo se apaga con «reducir movimiento» y con el modo ligero. Faltan las expresiones de los resultados (duda, preocupada, cargando, error).

### HU-174 · Día y noche en la escena

- **Historia:** Como agricultor, quiero ver mi zona de día o de noche según la hora real, para sentir que es mi lugar.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Calculado en el navegador con la hora y la posición del municipio
  - [ ] Transición suave entre día, atardecer y noche
  - [ ] El texto mantiene el contraste en todas las horas
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. Adelanto del 12 de octubre de 2026 (fase 0): el paisaje de los formularios se tiñe de amanecer, día, atardecer o noche según la hora del dispositivo (`web/src/lib/dayPhase.ts`, `SceneAmbient.tsx`), sin transición y sin la posición del municipio, porque esas pantallas no tienen zona. Los criterios de esta HU siguen pendientes.

### HU-175 · Endpoint de condiciones actuales

- **Historia:** Como desarrollador web, quiero la condición aproximada actual del municipio, para que la escena refleje el clima de ahora.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `GET /api/v1/conditions` del contrato, con datos de Open-Meteo y caché de 15 minutos
  - [ ] Solo la condición de ahora; ningún dato de pronóstico
  - [ ] Licencia y atribución de Open-Meteo verificadas y citadas en la app
  - [ ] Sin datos del proveedor: `insufficient_data` y valores nulos
  - [ ] Fuente registrada en `sources`; el motor no usa este endpoint
- **Reglas que aplican:** R5, R8
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. NASA POWER no sirve para esto por su retraso de 2 a 7 días (decisión 7).

### HU-176 · Lluvia, nubes y viento en la escena

- **Historia:** Como agricultor, quiero ver si llueve o hace viento en mi zona, para que la app se sienta viva.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Lluvia, nubes y viento con intensidad según la condición
  - [ ] Rótulo «Condición aproximada en <municipio> · <fuente> · <hora>»
  - [ ] Sin datos: clima neutro y rótulo «sin condición en vivo»
  - [ ] Efectos quietos con «reducir movimiento»; ícono en modo ligero
- **Reglas que aplican:** R5
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. Adelanto del 12 de octubre de 2026 (fase 0): en los formularios hay ambiente de decoración (sombras de nubes, pájaros, luciérnagas de noche y una llovizna pasajera al azar; `SceneAmbient.tsx`). No es la condición de ninguna zona, no lleva rótulo y no entra a ningún cálculo. Cuando exista esta HU, en las pantallas con zona la lluvia y el viento salen solo de la condición en vivo, con su rótulo (R5).
