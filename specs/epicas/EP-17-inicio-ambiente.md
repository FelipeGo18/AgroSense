---
id: EP-17
titulo: "Inicio, mascota y paisaje vivo"
prioridad: P0
fase: [Fase 0, Evento]
rol: "Web, con Motor y API"
agentes: [web, motor-api]
subsistemas: [W8, M9]
depende_de: [HU-151, HU-154]
reglas: [R1, R5, R8]
estado: en curso
---

# EP-17 · Inicio, mascota y paisaje vivo

**Resultado esperado:** Quien entra conoce AgroSense a través de su mascota satélite, y el paisaje refleja si en el municipio es de día o de noche, si llueve o si hay viento, sin que eso cambie ningún resultado.

La mascota y el prototipo se hacen en la fase 0; el endpoint de condiciones y la integración, en el evento.

## Historias de usuario

### HU-171 · Diseño de la mascota satélite

- **Historia:** Como equipo, quiero una mascota satélite tecnológica y tierna, para que AgroSense tenga una cara reconocible.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] Bocetos y versión final en Figma, en 2D y como modelo 3D low-poly
  - [x] Original: no se parece a un satélite ni personaje de marca existente
  - [x] Legible a 48 px en su versión 2D
- **Notas:** Elegida la **Semilla Sputnik**: una semilla germinando dibujada como caricatura de los años 60 (tinta gruesa, ojos de pastel, brazos de manguera). Las raíces son las antenas barridas, el brote es la antena de señal y las hojas son los paneles. La identidad está en la cara, los brazos, las raíces y el brote; **la semilla puede cambiar según el contexto** (germinada, frijol, maíz y las que se agreguen, por ejemplo según el cultivo consultado). Su estilo se aleja a propósito del low-poly: es «otro material» que viaja por el paisaje. Bocetos en Figma (tres rondas: tres conceptos, nueve estilos y la fusión elegida) y en `design/mascota/`; las propuestas descartadas se conservan. Versión 2D en código: `web/src/components/Mascot.tsx`, con una clase por parte animable. Falta: versión final por capas con puntos de giro en Figma y el modelo 3D.

### HU-172 · Expresiones y animaciones de la mascota

- **Historia:** Como usuario, quiero que la mascota reaccione a lo que pasa, para sentir que la app me acompaña.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Expresiones: reposo, guía, celebra (verde), duda (amarillo), preocupada (rojo), sin datos (no evaluable), cargando, error
  - [ ] «Sin datos» no se parece a «preocupada» (R1)
  - [ ] La expresión acompaña al texto; nunca es la única señal
- **Reglas que aplican:** R1

### HU-173 · Pantalla de inicio

- **Historia:** Como visitante, quiero entender en segundos qué es AgroSense y qué hace, para decidir si la uso.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] La mascota presenta qué es AgroSense y sus tres funciones (diagnóstico, qué sembrar después y agua)
  - [ ] Botones «Consultar sin cuenta» y «Entrar / crear cuenta»
  - [ ] Habla de AgroSense, no del problema ni de NASA
  - [ ] Usable a 360 px y con «reducir movimiento»

### HU-174 · Día y noche en la escena

- **Historia:** Como agricultor, quiero ver mi zona de día o de noche según la hora real, para sentir que es mi lugar.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Calculado en el navegador con la hora y la posición del municipio
  - [ ] Transición suave entre día, atardecer y noche
  - [ ] El texto mantiene el contraste en todas las horas

### HU-175 · Endpoint de condiciones actuales

- **Historia:** Como desarrollador web, quiero la condición aproximada actual del municipio, para que la escena refleje el clima de ahora.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `GET /api/v1/conditions` del contrato, con datos de Open-Meteo y caché de 15 minutos
  - [ ] Solo la condición de ahora; ningún dato de pronóstico
  - [ ] Licencia y atribución de Open-Meteo verificadas y citadas en la app
  - [ ] Sin datos del proveedor: `insufficient_data` y valores nulos
  - [ ] Fuente registrada en `sources`; el motor no usa este endpoint
- **Reglas que aplican:** R5, R8
- **Notas:** NASA POWER no sirve para esto por su retraso de 2 a 7 días (decisión 7).

### HU-176 · Lluvia, nubes y viento en la escena

- **Historia:** Como agricultor, quiero ver si llueve o hace viento en mi zona, para que la app se sienta viva.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Lluvia, nubes y viento con intensidad según la condición
  - [ ] Rótulo «Condición aproximada en <municipio> · <fuente> · <hora>»
  - [ ] Sin datos: clima neutro y rótulo «sin condición en vivo»
  - [ ] Efectos quietos con «reducir movimiento»; ícono en modo ligero
- **Reglas que aplican:** R5
