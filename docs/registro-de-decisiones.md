# Registro de decisiones

Las decisiones de arquitectura se explican en `decisiones.md`. Aquí se registran las decisiones puntuales con su fecha. Para cambiar una, se edita su fila y los documentos que la reflejan.

## Tomadas

| Decisión | Elegida | Fecha |
|---|---|---|
| Herramienta de backlog | GitHub Projects | 10 oct 2026 |
| Framework de la API | FastAPI (Axum descartado, ver `specs/04-stack.md`) | 10 oct 2026 |
| Cuentas y regla R9 | Cuentas con lotes y temporadas; R9 reescrita (decisión 6) | 10 oct 2026 |
| Clima en vivo | Ambiente de la escena, nunca insumo de la decisión (decisión 7) | 10 oct 2026 |
| Responsables del contrato | Haider y Felipe: cualquiera de los dos cambia `specs/02-contratos.md` o aprueba cada cambio | 10 oct 2026 |
| Base de datos | PostgreSQL propio en Docker, sin servicios gestionados (Supabase descartado) | 10 oct 2026 |
| Inicio de sesión | Autenticación propia: usuario y contraseña (Argon2), sesión en cookie; recuperar la contraseña en P1 | 10 oct 2026 |
| Condiciones actuales | Open-Meteo, solo el «ahora», sin pronóstico | 10 oct 2026 |
| Dónde se prepara el frontend | Fase 0 en este repositorio (`web/`, EP-15); la app de la demo, en un repositorio nuevo durante el evento | 10 oct 2026 |
| Estilo | Inspiración de estilo en *The Farmer Was Replaced* y la web de GTA VI, sin copiar sus elementos (`specs/05-frontend.md`) | 10 oct 2026 |
| Inicio | Mascota satélite; habla de AgroSense, no del problema ni de NASA | 10 oct 2026 |
| Navegación | Una experiencia continua con URL por nivel y por lote; quien vuelve con sesión entra directo a Mi finca | 10 oct 2026 |
| Paleta y semáforo | Paleta del moodboard más un rojo (#B83A2B); variantes oscuras para texto; botón principal en oliva oscuro con texto blanco; tonos claros siempre con texto noche (HU-152, `design/tokens/tokens.json`) | 10 oct 2026 |
| Tipografía | Fredoka 600 para títulos y Atkinson Hyperlegible para texto, 18 px corriente y 14 px mínimo (HU-152) | 10 oct 2026 |
| Variables de Figma | No se crean: los tokens viven en `design/tokens/tokens.json` y en Figma como frame de muestras con nombre (Tokens Studio es de pago) | 10 oct 2026 |
| Lenguaje visual de los componentes | Diorama low-poly: esquinas biseladas, caras trianguladas y canto en lugar de sombra; nada con esquinas redondas. Descartados «instrumento de campo» y «cuaderno de campo» (HU-153) | 10 oct 2026 |
| Orden de trabajo del frontend | Cada pieza se diseña y aprueba primero en Figma; el código va después | 10 oct 2026 |
| Control de prioridad | Cinco semillas y un «0» que se tocan, en lugar de un deslizador (se retira Radix Slider) | 10 oct 2026 |
| Mascota | Semilla Sputnik: semilla germinando en estilo de caricatura de los años 60; raíces por antenas, brote por antena de señal. La semilla cambia según el contexto; la cara y el brote son la identidad (HU-171) | 10 oct 2026 |
| Fondos y recorrido con scroll | Fondos en capas SVG generadas por código; el scroll mueve una línea de tiempo de GSAP, no un video. Técnicas combinadas por momento (máscara, sección fijada con paralaje, 3D como mejora; video atado al scroll solo opcional). Si entra una imagen: AVIF con respaldo WebP (HU-155) | 10 oct 2026 |
| Pruebas de scroll del prototipo | Batería de estrés con `playwright-core` y el Chrome del equipo, fuera de Docker y de CI; excepción de la fase 0 a la regla de no hacer pruebas de navegador (HU-155) | 10 oct 2026 |
| Scroll de los recorridos | El scroll fija el destino y la animación lo sigue con tope de velocidad; imán hacia las paradas con contenido; las escenas de relleno no se detienen. Lenis con inercia 0,09 y tope de 110 px por golpe de rueda (HU-155) | 10 oct 2026 |
| `design/` fuera de `web/` | Se mantiene: `design/` es la fuente del diseño (generadores, láminas, tokens) y `web/` la importa | 10 oct 2026 |
| Etapa del cultivo en Mi finca | Se calcula con la temperatura acumulada del municipio (NASA POWER) desde la siembra; si faltan datos, por calendario y diciéndolo. Es una estimación de la zona, no una observación del lote. Contrato aprobado por Felipe; pendiente: fuentes de grados-día por cultivo (HU-150) | 10 oct 2026 |
| Editar el perfil | Se permite cambiar nombre, usuario y contraseña: `PATCH /api/v1/me` y `POST /api/v1/me/password`, aprobados por Felipe (HU-160) | 10 oct 2026 |
| Roles | Agricultor (`farmer`, por defecto, nunca ve datos inventados), administrador web (`admin`: usuarios, bloqueos, métricas agregadas) y desarrollador (`developer`: simulaciones y sin topes, solo en desarrollo). Documentado; se implementa en HU-170 (P1) | 10 oct 2026 |
| Sesión: cookie y no JWT | Se mantiene la sesión en cookie `httpOnly` respaldada por la tabla `sessions`. La contraseña viaja solo al iniciar sesión, por HTTPS; después cada petición lleva un token de sesión aleatorio en cookie `httpOnly`, cuyo hash se guarda en la base de datos. Un JWT no se puede revocar sin guardar estado en el servidor, y lo necesitamos para cerrar sesión, cerrar las demás al cambiar la contraseña, bloquear usuarios y borrar la cuenta. Web y API comparten origen, así que no aporta nada | 10 oct 2026 |
| Lotes en un mapa real | El agricultor dibuja su lote en un mapa (MapLibre y Terra Draw sobre OpenStreetMap, capa satelital por definir por licencia); el polígono debe caer en su municipio. Si no dibuja, escribe el área. El clima sigue siendo el de la celda de NASA POWER (unos 50 km) que contiene al lote (HU-164) | 10 oct 2026 |
| Administrador y soporte | El administrador sí ve a los agricultores con sus lotes, temporadas y tickets, y puede borrar y restaurar; todo queda auditado (hoy en `activity_log`, HU-178). Borrar lotes y temporadas es reversible 30 días; borrar la cuenta sigue siendo total. El consentimiento sube a la versión 2 para decirlo (HU-170) | 10 oct 2026 |
| Logs y trazabilidad | Dos cosas distintas. **Logs de la terminal** con `structlog` (color en desarrollo, JSON en producción, sin archivos), para operar el servidor (HU-177). **Trazabilidad** en la tabla `activity_log` de PostgreSQL: qué hizo cada agricultor y administrador, con estado `ok`, `denied` o `failed`, solo agregable, 180 días, sin contraseñas, tokens, polígonos ni valores (HU-178). Reemplaza a `admin_actions`. Las une el `request_id`. Los endpoints de cálculo no escriben en ella (R9) | 10 oct 2026 |
| Suelo, heladas y calendario | El suelo entra al P0 con SoilGrids, por municipio y por lote (EP-18). El semáforo pasa de tres a cinco señales: lluvia, heladas, suelo, oferta y mercado; el suelo nunca es crítico. Nueva tabla de acciones por luz. Calendario del cultivo mes a mes (HU-179, HU-180). Las temperaturas se corrigen por altitud (HU-044 pasa a P0). R10 se amplía: el suelo también es una estimación y se dice siempre; R6 menciona el suelo del lote. Con suelo desfavorable la acción es rotar, también en amarillo. La textura no entra a la señal de suelo (no hay rangos de textura con fuente). Aprobado por Felipe; Haider debe enterarse antes de congelar el contrato. Ver `docs/investigacion-decisiones.md` y la decisión 8 | 10 oct 2026 |
| Diseño de la interfaz final | Las pantallas definitivas se diseñan en una sección aparte de Figma, «AgroSense · Pantallas finales», separada de la exploración (moodboard, kit, mascotas, recorridos) | 10 oct 2026 |
| Rotaciones y finca | Se unen en Mi finca, por lote | 10 oct 2026 |
| Audio | P1 (HU-157) | 10 oct 2026 |
| «Acerca de» | Sin sección aparte: el panel «¿Cómo funciona y de dónde sale esto?» cubre fuentes, versión y cómo se decide | 10 oct 2026 |
| Skills de frontend | `greensock/gsap-skills` y `anthemflynn/ccmp` (react-three-fiber), leídas antes de instalarlas | 10 oct 2026 |

## Dependen de una verificación

No se deciden por preferencia: se resuelven con el resultado de la HU indicada y se pasan a la tabla anterior.

| Tema | Se resuelve con | Fecha límite | Rol |
|---|---|---|---|
| Tamaño del equipo | Confirmación de los integrantes | 17 oct | Todos |
| Fuente del clima histórico | HU-002 (enunciado del 28 de octubre) | 30 oct | Datos |
| Región piloto | HU-001 (cobertura de EVA) | 31 oct | Producto y Datos |
| SIPSA en el P0 | HU-003 | 1 nov | Datos |
| Qué código preparado se puede llevar al evento | HU-004 (términos de Space Apps 2026) | 2 nov | Producto |
