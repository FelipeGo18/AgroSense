---
id: EP-16
titulo: "Cuentas, lotes y progreso"
prioridad: P0
fase: [Fase 0, Evento]
rol: "Motor y API, con Web"
agentes: [motor-api, web]
subsistemas: [M8, W7, W9]
depende_de: [HU-012]
reglas: [R3, R4, R5, R7, R8, R9, R10]
estado: pendiente
---

# EP-16 · Cuentas, lotes y progreso

**Resultado esperado:** Un agricultor crea su cuenta, registra uno o varios lotes en una o varias zonas, los divide y junta por partes como trabaja, y al volver encuentra sus lotes con su historial (incluido lo que borró hace menos de 30 días, para restaurarlo) y su progreso. Sin cuenta, puede consultar: los datos se envían solo para calcular y no se guardan (R9).

Decisión 6 de `docs/decisiones.md` y regla R9. Cuentas en PostgreSQL (en la nube para el equipo y la demo, desde el 10 de noviembre de 2026; en Docker Compose para las pruebas) con autenticación propia. Capacidad y orden de recorte en `docs/plan-48h.md`.

El diseño y las pantallas se prototipan en la fase 0 (EP-15); el código de cuentas se hace en el evento.

**Recorte del MVP (11 de octubre de 2026):** quedan en P0 las cuentas mínimas (esquema, registro, entrar, salir, consentimiento y borrar la cuenta: HU-161, HU-162, HU-163, HU-166 y HU-168, que el proyecto no recorta), los lotes con polígono, su suelo y la capa satelital de la NASA (HU-164, HU-182, HU-211), las temporadas simples (HU-165) y Mi finca reducida a una sola zona (HU-169). Pasaron a P1: editar el perfil y la contraseña (HU-160), la trazabilidad y Mi actividad (HU-178), restaurar lo borrado (HU-204; borrar un lote o una siembra sigue siendo posible), el progreso (HU-167) y el lote vivo (HU-187). Desde el lote se entra a las estrategias de rotación (HU-214).

## Historias de usuario

### HU-160 · Editar mi perfil y cambiar la contraseña

- **Historia:** Como agricultor, quiero cambiar mi nombre, mi usuario y mi contraseña, para mantener mi cuenta a mi gusto y segura.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] `PATCH /api/v1/me` y `POST /api/v1/me/password` del contrato
  - [x] `PATCH /api/v1/me` acepta `priorities`: un entero de 0 a 5 por señal; nulo vuelve a los pesos de AgroSense; fuera de rango o todas en 0, 422
  - [x] 409 si el usuario nuevo ya existe; 403 si la contraseña actual es incorrecta; 422 si la nueva es corta o igual a la actual
  - [x] Cambiar la contraseña exige la actual y cierra las demás sesiones del usuario; los intentos fallidos cuentan para el límite de 429
  - [x] En la web, Mi cuenta permite editar nombre y usuario en el sitio y cambiar la contraseña en su propia vista, con estados de guardado y error
  - [x] No se pide ningún dato personal nuevo: las prioridades son preferencias, no datos de la finca (R9)
  - [x] (Web, 12 de octubre de 2026) «Mi cuenta» en `/mi-cuenta`: ver y editar el nombre y el usuario, lo que se guarda con la versión y la fecha del consentimiento, preferencias de este dispositivo (modo ligero y sonido), cerrar sesión y borrar la cuenta con confirmación. «Cambiar contraseña» en `/mi-cuenta/contrasena`. Son páginas con sesión: sin ella llevan a «Entrar»
  - [x] (Web, 13 de octubre de 2026) La tarjeta «Sus prioridades» de Mi cuenta (`web/src/pages/account/PrioritiesCard.tsx`): los seis pesos con semillas, se guardan al tocarlas (`PATCH /me`), dice si se usan las propias o el criterio de AgroSense, muestra ese criterio (`GET /version`) y permite volver a él. Con todas en 0 no envía nada. Agua, heladas y calor dicen que un riesgo grave cuenta siempre
  - [x] (Web) El interruptor «Modo ligero» de las preferencias: se guarda en el navegador y, prendido, quita las animaciones, los recorridos, el scroll suave (Lenis), GSAP y el movimiento de la mascota. El interruptor vive en `web/src/lib/lightMode.ts`; lo que el modo ligero apague de más (la escena 3D, imágenes pesadas) lo engancha Haider ahí, que es quien lleva el modo ligero
- **Reglas que aplican:** R9
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. Mientras no exista, las prioridades de las señales se recuerdan en el navegador también con cuenta (HU-202). Aprobado por Felipe el 10 de octubre de 2026. Revisión de seguridad obligatoria (agente `security`). **Pendiente en Figma (12 de octubre de 2026):** Mi cuenta tiene ahora una tarjeta propia «Mi actividad» con su botón, antes de «Borrar mi cuenta» (antes era solo un enlace en «Lo que guardamos de usted»); falta pasarla a `design/pantallas/cuenta.py` y a Figma. **Estado al 13 de octubre de 2026:** hechos el backend (con pruebas en `tests/accounts/test_account.py`) y las pantallas. Revisión de seguridad hecha y arreglada el 14 y 15 de octubre (ver HU-162); borrar la cuenta pide la contraseña. La tarjeta «Sus prioridades» se hizo el 13 de octubre con los pesos provisionales de HU-198. El interruptor de modo ligero de Mi cuenta usa el mismo interruptor de la barra (HU-158).

### HU-178 · Trazabilidad de lo que hacen agricultores y administradores

- **Historia:** Como agricultor, quiero ver qué se hizo con mi cuenta y mis lotes, y como equipo queremos saber quién hizo qué y cuándo, para confiar en la app y resolver tickets.
- **Prioridad:** P1 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] Tabla `activity_log` con migración, según «Trazabilidad» del contrato
  - [x] Cada endpoint de cuenta escribe su evento en la misma transacción que el cambio; los intentos `denied` y `failed` también quedan
  - [ ] Prueba: ningún endpoint de cálculo escribe en `activity_log` (R9)
  - [x] Prueba: ningún evento guarda contraseñas, tokens, el polígono ni valores de campos
  - [ ] El usuario de la API no puede modificar ni borrar eventos; la limpieza de 180 días corre con otro rol
  - [ ] Borrar la cuenta borra los eventos del agricultor y anonimiza las acciones de administradores sobre sus datos
  - [x] `GET /me/activity` y la pantalla «Mi actividad» en Mi cuenta, con el estado de cada evento (`ok`, `denied`, `failed`)
  - [x] El `request_id` de cada evento coincide con el de la terminal (HU-177)
  - [x] (Web, 12 de octubre de 2026) «Mi actividad» en `/mi-cuenta/actividad`: cada evento en palabras, con quién lo hizo (usted o soporte), cuándo y su resultado con forma y texto; solo los nombres de los campos que cambiaron; de a 50 con «Ver más antiguos». «¿Ve algo que no hizo?» lleva a cambiar la contraseña mientras no exista «Reportar un problema» (HU-170)
- **Reglas que aplican:** R9
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. En el MVP la tabla `activity_log` no existe; los logs de la terminal (HU-177) siguen. Reemplaza a `admin_actions`: las acciones del administrador son eventos de la misma tabla, y su bitácora (`GET /admin/activity`) llega con HU-170 (P1). El consentimiento lo menciona desde la versión 2 (vigente: 3, HU-163). Definido el 10 de octubre de 2026. Revisión de seguridad obligatoria. **Estado al 13 de octubre de 2026:** hechos la tabla (migración 1.3), los eventos de los endpoints de cuenta, `GET /me/activity` y la pantalla. Faltan: la prueba de que los endpoints de cálculo no escriben (todavía no existen), los permisos de solo agregar y la limpieza de 180 días con otro rol, y anonimizar las acciones de administradores (no hay administradores hasta HU-170; borrar la cuenta ya borra los eventos del agricultor). Revisión de seguridad hecha el 14 de octubre (ver HU-162): un bloqueo deja un solo evento por ventana, la limpieza de 180 días corre también al arrancar (todavía con el usuario de la API) y «Mi actividad» ya no pierde eventos con la misma hora. **9 de noviembre de 2026 (aprobado por Felipe):** la limpieza ya no corre al iniciar sesión; la hace el mantenimiento de las cuentas (`backend/accounts/maintenance.py`), que borra también las sesiones vencidas, al arrancar y con `python -m backend.accounts.maintenance` para programarlo. Ningún endpoint limpia.

### HU-170 · Roles: agricultor, administrador y desarrollador

- **Historia:** Como equipo, queremos tres roles con permisos distintos, para operar la web y probarla sin mezclar datos inventados con los del agricultor.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Columna `role` (`farmer`, `admin`, `developer`) y `blocked_at` en `users`, con migración
  - [ ] Endpoints de `admin` y `dev` del contrato; `403` si el rol no alcanza
  - [ ] El agricultor nunca recibe datos simulados; las respuestas simuladas llevan `simulated: true` (R5)
  - [ ] El administrador ve a cada agricultor con sus lotes, temporadas y tickets, y puede borrar y restaurar lotes y temporadas con motivo; toda acción queda en `activity_log` (HU-178)
  - [ ] El agricultor reporta un problema con un ticket y ve en Mi cuenta las acciones de soporte sobre sus datos
  - [ ] Bitácora del administrador (`GET /admin/activity`) con filtros por usuario, acción, estado y fechas
  - [ ] La API no arranca en producción si hay usuarios `developer` o la simulación está activa
  - [ ] Un usuario bloqueado no entra y pierde sus sesiones abiertas
  - [ ] Tabla `usage_daily` con migración, según el contrato: `day`, `endpoint`, `municipality_id`, `crop_id` y `count`
  - [ ] Cada endpoint de cálculo (`/diagnostics`, `/rotations`, `/calendar`, `/water-plans` y `/scenarios`) suma 1 a su fila, con el `crop_id` que fija el contrato; si la base de datos falla, la consulta responde igual
  - [ ] Prueba: `usage_daily` no tiene ninguna columna que identifique a una persona ni datos de la finca, y no se puede unir con `activity_log` (R9)
  - [ ] Las métricas son agregadas: consultas por día y municipios y cultivos más consultados salen de `usage_daily` (contador anónimo); lotes y siembras, de las cuentas. Un grupo con menos de 5 va en «Otros». El consentimiento (desde la versión 2) avisa que soporte puede ver los lotes (R9)
- **Reglas que aplican:** R5, R9
- **Notas:** Definido el 10 de octubre de 2026. El contador `usage_daily` entra con esta HU (P1): en el P0 los endpoints de cálculo no escriben nada en la base de datos. Falta decidir el resto de funciones del administrador y si su panel va en esta web (supuesto: en `/admin`, solo en escritorio, `specs/05-frontend.md`). El modo desarrollador amplía HU-014. Revisión de seguridad obligatoria.

### HU-161 · Esquema de cuentas y migraciones

- **Historia:** Como desarrollador, quiero las tablas `users`, `sessions`, `lots` y `seasons` con migraciones, para guardar cuentas de forma reproducible.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] Tablas y columnas del contrato, con migraciones de Alembic: `users`, `sessions`, `login_attempts`, `lots`, `seasons`, `support_tickets`, `activity_log` y `usage_daily`. Las migraciones son de toda la base de datos (`backend/db/migrations/`) y se numeran `1.1`, `1.2` … `1.9` y después `2.1`, con el primer número como carpeta (`1/1.1_…`); el número lo pone `python -m backend.db.revision`
  - [x] PostgreSQL en Docker Compose con volumen persistente
  - [x] Antes de aplicar o deshacer una migración se hace una copia de seguridad de la base de datos (`python -m backend.db.migrate`); si la copia falla, no se migra, y `alembic upgrade` directo se niega a correr
  - [x] La base de datos solo cambia con migraciones que quedan en el repositorio; las pruebas fallan si los modelos cambian sin migración, si quedan dos migraciones finales o si una no se puede deshacer (`backend/README.md`)
  - [x] Borrar un usuario borra en cascada sus sesiones, lotes y temporadas y, cuando existan (P1), sus tickets y sus eventos de `activity_log`
  - [ ] `municipality_id` y `crop_id` se validan contra el catálogo publicado (`municipality_id` hecho el 15 de octubre de 2026 en la API de lotes; `crop_id` espera al catálogo de cultivos)
- **Reglas que aplican:** R7, R9
- **Contrato que toca:** base de datos de cuentas de `specs/02-contratos.md`
- **Notas:** `activity_log` (HU-178) y `support_tickets` (HU-170) son P1: en el MVP no se crean.

### HU-162 · Autenticación

- **Historia:** Como agricultor, quiero crear una cuenta e iniciar sesión de forma sencilla, para volver a mis lotes desde cualquier dispositivo.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] `POST /auth/register`, `/auth/login` y `/auth/logout` del contrato, con usuario y contraseña; `GET /me` y `DELETE /me`
  - [x] Contraseña guardada solo como hash Argon2; sesión en cookie `httpOnly`, `Secure` y `SameSite=Lax`, con el hash del token en `sessions`
  - [x] 409 si el usuario ya existe; 429 tras 5 intentos fallidos en 15 minutos; cerrar sesión invalida la sesión en la base de datos
  - [x] Los endpoints de cuenta responden 401 sin sesión válida
  - [x] Una petición que cambia datos con un `Origin` que no es el de la web responde 403
  - [x] Ninguna clave ni secreto en el repositorio
  - [x] La API sube siempre. Las cuentas solo se atienden con la base de datos arriba y el esquema en la última migración; si no, responden 503 (`accounts_database_down` o `accounts_migration_pending`), el log dice el motivo con las dos versiones, `GET /health` lo informa y la web sigue en modo sin cuenta
  - [x] Pantallas de entrar y crear cuenta en la web (`web/src/pages/auth/`), contra la API real; con sesión, la barra muestra el nombre y «Cerrar sesión»
  - [x] El formulario cabe entero en la primera pantalla, sin hacer scroll, en escritorio (desde 1366 × 700) y en móvil (desde 390 × 664); el pie de página va debajo. Crear cuenta va en dos columnas en escritorio y en dos pasos en móvil (datos y consentimiento). En teléfonos más bajos (360 × 640) el paso del consentimiento sí necesita un poco de scroll
  - [x] Revisión de seguridad: hecha y arreglada (14 y 15 de octubre de 2026)
  - [x] (15 de octubre de 2026) Límites por conexión: 5 contraseñas malas por usuario y conexión, 20 por usuario desde cualquier conexión, 30 inicios de sesión y 10 registros por conexión, y como mucho 4 cálculos de Argon2 a la vez (`backend/accounts/limits.py`). La IP no se guarda
  - [x] (15 de octubre de 2026) Borrar la cuenta pide la contraseña (`DELETE /me` con `password`), también en el diálogo de Mi cuenta
- **Reglas que aplican:** R9
- **Notas:** Recuperar la contraseña queda en P1. Revisión de seguridad obligatoria (agente `security`). Backend hecho el 12 de octubre de 2026 (`backend/api/auth.py`). Supuestos por confirmar: crear la cuenta deja la sesión abierta y responde el perfil (201); el usuario se compara en minúsculas y sin espacios al entrar; con la cuenta bloqueada una sesión ya abierta responde 401. El tope de intentos es por usuario y vive en la tabla `login_attempts` (sobrevive a un reinicio). Desde el 12 de octubre de 2026 se construye la versión completa, no el recorte del MVP: el backend también tiene `PATCH /me`, `POST /me/password` (HU-160), `GET /me/activity` y la bitácora `activity_log` (HU-178). **Revisión de seguridad (13 y 14 de octubre de 2026, agente `security`):** sin hallazgos críticos ni altos. Arreglado el 14 de octubre (`tests/accounts/test_seguridad.py`): el tope de intentos se anota antes de verificar la contraseña (ya no se salta con peticiones a la vez); un bloqueo deja un solo evento por ventana; la limpieza de 180 días también corre al arrancar; «Mi actividad» ya no pierde eventos con la misma hora; cabeceras de seguridad y `Cache-Control: no-store` en lo de la cuenta; la documentación de la API solo en desarrollo; copias de `backups/` solo para el dueño; el log no repite direcciones inexistentes ni caracteres de control, y las trazas de base de datos no llevan valores. El 15 de octubre, con la decisión de Felipe: límites por conexión (el bloqueo por contraseñas malas ya es de la conexión, no de la cuenta; el registro tiene tope por conexión; Argon2 con tope de cálculos a la vez) y `DELETE /me` pide la contraseña (`tests/accounts/test_seguridad.py`). **Pendiente en Figma:** el campo de contraseña del diálogo «¿Borrar su cuenta?» (`design/pantallas/cuenta.py`).

### HU-163 · Consentimiento y tratamiento de datos

- **Historia:** Como agricultor, quiero saber qué se guarda de mí y aceptarlo, para confiar en la app.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [x] Texto corto en español claro de qué se guarda y para qué, enlazado a la política de tratamiento de datos (Ley 1581 de 2012). Hecho el 13 de octubre de 2026: el consentimiento de «Crear cuenta» enlaza a la página de la política, que ya existe; su revisión legal es el criterio de abajo
  - [x] Sin aceptar, no se crea la cuenta: la web no envía nada y la API responde 422
  - [x] Se guarda `consent_version` y `consent_at`
  - [ ] La versión vigente es la **3**. Dice que se guarda la ubicación (polígono) de cada lote (HU-164), que soporte puede ver los lotes (HU-170), que se registra la actividad de la cuenta durante 180 días (HU-178) y, nuevo en la versión 3, si el lote tiene riego (`irrigated`, HU-164), que se guardan sus prioridades (`priorities`, HU-160) y que lo que siembra se suma sin su nombre a los totales de siembras de su municipio, solo con al menos 5 cuentas (HU-200)
  - [x] El registro envía `consent_version = 3` y la API guarda esa versión
  - [x] (Sustituido el 12 de octubre de 2026: la web muestra el texto completo de la versión 3, porque se construye la versión final.) En el MVP el texto solo nombra lo que el MVP guarda: usuario, nombre, lotes con su ubicación y su riego, y siembras. El soporte, el registro de actividad y las prioridades en el perfil entran al texto cuando existan sus HU (HU-170, HU-178 y HU-160, P1); mientras tanto las prioridades se recuerdan en el navegador. Se intenta incluir HU-160 en el MVP: es la primera HU del P1 que se retoma si alcanza el tiempo
  - [x] (Web, 13 de octubre de 2026) La página de la política en `/politica-de-datos` (`web/src/pages/policy/`): se lee sin cuenta y dice qué se guarda, qué no, para qué, quién lo ve, cuánto tiempo y cómo borrarlo. Lleva a la vista el aviso «Este texto todavía necesita revisión legal» mientras `LEGAL_REVIEW_PENDING` sea verdadero
  - [ ] Revisión legal del texto de la política y canal de contacto del responsable; al tenerlos, se apaga `LEGAL_REVIEW_PENDING`
- **Reglas que aplican:** R9
- **Notas:** La versión 2 sumó el polígono, el soporte y la actividad (10 de octubre de 2026). La versión 3 suma el riego y las prioridades guardadas en el perfil; aprobada por Felipe el 11 de octubre de 2026. Las siembras como totales anónimos de oferta (HU-200, P1) entran en la versión 3 (`specs/01-reglas.md`, «Varias fuentes»). Por decidir: qué pasa con una cuenta que aceptó una versión anterior (por ejemplo, pedir que acepte la nueva al iniciar sesión). Mientras no haya usuarios reales, la 3 es la primera versión en producción. Supuesto por confirmar: la API responde 422 si `consent_version` no es la vigente (el contrato solo dice 422 sin `consent_accepted`). Revisión del texto legal por confirmar con la región: la Ley 1581 de 2012 es de Colombia (decisión 11). **Por decidir (11 de octubre de 2026):** con el recorte del MVP, la actividad de la cuenta (HU-178), el soporte (HU-170) y las prioridades en el perfil (HU-160) son P1; el texto de la versión 3 los nombra. Hay que decidir si el MVP publica un texto que solo diga lo que hace el MVP (y la versión 3 completa llega con el P1) o si se mantiene la versión 3 tal cual.

### HU-164 · Lotes del usuario

- **Historia:** Como agricultor, quiero dibujar mis lotes en un mapa real, editarlos y borrarlos, en una o varias zonas, para tener mi finca completa y ubicada.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] Endpoints de `lots` del contrato del P0, con `geometry` (polígono GeoJSON). Borrar marca `deleted_at` y el lote deja de verse; restaurarlo es HU-204 (P1)
  - [x] El lote guarda `irrigated` (si tiene riego): el formulario pregunta «¿Este lote tiene riego?» con «Sí», «No» y «Todavía no sé»; sin respuesta queda nulo y se puede cambiar después con `PATCH`
  - [ ] Con `lot_id`, el diagnóstico y las estrategias toman `irrigated` del lote; con `irrigated` nulo, se evalúa como sin riego y la limitación lo dice
  - [x] En la web, un mapa base de OpenStreetMap centrado en el municipio, donde el agricultor dibuja el contorno del lote; el área se calcula sola. La capa satelital de la NASA es HU-211
  - [x] El polígono debe ser válido y caer dentro de su municipio (422 si no), y se ve el límite municipal mientras se dibuja
  - [x] Si no puede o no quiere dibujar, escribe el área a mano y el lote queda sin ubicación; puede dibujarlo después («Dibujar en el mapa», entrega 2)
  - [x] Un usuario no ve ni modifica lotes ajenos (404)
  - [x] «Editar lote», desde la cabecera del lote, cambia el nombre, el contorno (moviendo los puntos en el mapa) y el riego; dice que al cambiar el riego se recalculan el diagnóstico, las estrategias y el agua del lote, y que las siembras ya registradas guardan el diagnóstico que vieron
  - [x] Editar el lote a un área menor que la de sus temporadas en curso responde 422
  - [ ] «Borrar este lote» pide confirmación. P1 (HU-204): dice hasta qué fecha se puede restaurar y, en Mi finca, los lotes borrados hace menos de 30 días se ven aparte («Borrados hace poco») con «Restaurar»
  - [ ] Desde el lote, «Ver estrategias de rotación» abre HU-214 con el lote
- **Reglas que aplican:** R7, R9
- **Notas:** Restaurar lo borrado pasó a P1 el 11 de octubre de 2026 (HU-204): recorte del MVP. Un `PATCH` que deja el lote más chico que el área de sus temporadas en curso responde 422 y la pantalla lo avisa (aprobado por Felipe el 11 de octubre de 2026). Con el polígono, la ficha del lote muestra su suelo estimado (HU-182). La ubicación del lote es un dato personal: entra en el texto de consentimiento (HU-163). El clima de NASA POWER sigue siendo el de la celda de unos 50 km que contiene al lote, no del lote; el polígono abre la puerta a datos por lote en P1 (HU-043). Mapa y librería en `specs/05-frontend.md`. Ampliado el 10 de octubre de 2026. `irrigated` se agregó el 11 de octubre de 2026: con riego, la falta de lluvia no es un riesgo en la señal `water` (HU-071). Es un dato mínimo que se usa (R9); el consentimiento versión 3 lo nombra (HU-163). **Entrega 1 (15 de octubre de 2026):** API de lotes (`backend/api/lots.py`: listar, crear, ver, editar y borrar; ajeno o borrado da 404; `lot.created`, `lot.updated` y `lot.deleted` en la actividad) y, en la web, «Agregar lote» sin dibujar (municipio, área a mano, nombre y riego) y el lote con «Editar lote» y «Borrar este lote». **Mientras no llegue la entrega 2 (el mapa), un `geometry` responde 422 `geometry_not_available`.** Diseños aprobados por Felipe el 15 de octubre: `design/pantallas/sin_dibujo.py`, `agregar.py` y `editar.py`, sin el mapa. Pruebas en `tests/accounts/test_lotes.py` y `web/src/pages/farm/farm.test.tsx`. **Entrega 2 (15 de octubre de 2026):** el lote se dibuja en el mapa real (MapLibre GL 6 y Terra Draw sobre OpenFreeMap) con el límite de su municipio punteado; la barra tiene Dibujar, Mover puntos, Deshacer y Borrar, y el área del dibujo se ve al instante (en el navegador, sobre una esfera de igual área; la que se guarda la calcula la API sobre el elipsoide). Si el dibujo se sale del municipio, la web lo dice y no deja guardar; la API lo valida igual (`backend/api/lot_geometry.py`, pruebas en `tests/accounts/test_lotes.py`). «Escribir el área a mano» sigue disponible, y si el navegador no puede mostrar el mapa se ofrece eso. «Dibujar en el mapa» dibuja un lote que se guardó sin dibujo. Figma: «Dibuje su lote», «se sale del municipio», «D1 · Editar lote». No se dibujó «¿Ya sembró algo en este lote?»: las siembras son la entrega 3 (HU-165).

### HU-165 · Temporadas e historial del lote

- **Historia:** Como agricultor, quiero registrar qué sembré, en qué parte del lote, qué había antes en ese terreno y cuándo coseché, dividiendo y juntando partes como yo trabajo, para que las recomendaciones usen mi historial real.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] Endpoints de `seasons` del contrato
  - [x] Un lote puede tener varios cultivos a la vez, cada uno en una parte de su área (`area_ha`); la suma de las temporadas en curso no pasa del área del lote (422)
  - [x] Al registrar una siembra, la web pregunta «¿Qué había antes en este terreno?» y deja elegir **una o varias** temporadas cosechadas del lote, o ninguna («Nada: es la primera siembra aquí»). Se guardan en `follows_season_ids`
  - [x] **Dividir:** una temporada cosechada puede tener varias sucesoras. Ejemplo: al cosechar una papa de 1 ha, se siembran 0,5 ha de fresa y 0,5 ha de ajo, las dos con la papa en `follows_season_ids`
  - [x] **Juntar:** una temporada puede venir de varias. Ejemplo: después de cosechar la fresa y el ajo, se siembra 1 ha de arveja con las dos en `follows_season_ids`
  - [x] Validaciones (422): cada temporada de `follows_season_ids` es del mismo lote, está cosechada y su `harvest_date` es igual o anterior a la `sowing_date` de la nueva; el área de una temporada no pasa de la suma de las áreas de las que viene más el área libre del lote, y la suma de las temporadas en curso nunca pasa del área del lote
  - [x] Cada temporada guarda el diagnóstico visto al sembrar (`diagnosis_light`, `diagnosis_light_default`, `diagnosis_action`, `diagnosis_weights`, `diagnosis_irrigated`) con `dataset_version` y `rules_version`: es el diagnóstico de la ventana que empieza en su `sowing_date`
  - [x] `diagnosis_action` acepta solo `sow`, `other_window`, `rotate` y `review_data`; si el agricultor no consultó el diagnóstico, esos campos van nulos
  - [ ] Las estrategias de rotación de un terreno reciben los cultivos de todas las temporadas de las que viene
  - [x] La etapa de cada temporada en curso sale de las etapas por calendario (HU-220, `stage_method = calendar`)
  - [x] Borrar una temporada marca `deleted_at` y deja de verse; listarla y restaurarla es HU-204 (P1)
  - [x] Web (Figma: «Registrar la siembra», «Registrar la cosecha», «Siembra / Editar»): el lote muestra cada siembra en curso con cultivo, etapa, día, la barra de etapas y la cosecha estimada (rotulada como salida de la duración de las etapas, no del lote); «Registrar siembra» si queda área libre; «Registrar cosecha», «Corregir» y lo ya cosechado. «Cómo queda el lote» muestra las partes como una barra de área. Mi finca dice los cultivos en curso de cada lote
- **Reglas que aplican:** R4, R9
- **Contrato que toca:** `seasons` (con `follows_season_ids`), `POST /api/v1/lots/{lot_id}/seasons`, `PATCH /api/v1/seasons/{season_id}`, tabla de errores
- **Notas:** Las partes son de área, no se dibujan en el mapa; el suelo es el mismo para todo el lote. Decidido el 11 de octubre de 2026 y ampliado el mismo día: el agricultor divide su lote como quiera; una temporada puede venir de varias y tener varias sucesoras (`follows_season_ids`, antes `follows_season_id` singular). Ejemplo de uso: hoy siembra papa en la mitad; en un mes divide la otra mitad en fresa y ajo; al cosechar la papa, reparte ese terreno. Pasa de M a L. La regla de áreas es una sola (`specs/02-contratos.md`): el área de una temporada no pasa de la suma de las áreas de las que viene más el área libre del lote, y la suma de las temporadas en curso nunca pasa del área del lote; eso basta para que un terreno no se reparta dos veces. Por eso juntar dos temporadas de 1 ha en una de 2 ha es válido, y una sucesora puede ocupar el terreno anterior más terreno libre (por ejemplo, 1,5 ha después de una papa de 1 ha, si hay 0,5 ha libres). Cada temporada guarda las dos luces (`diagnosis_light`, con los pesos con que se vio, y `diagnosis_light_default`, con los de AgroSense) y esos pesos (`diagnosis_weights`) (R4). Por decidir: el orden de `previous_crop_ids` cuando hay varias anteriores cosechadas el mismo día. Entrega 3 de Mis lotes (17 de octubre de 2026): API, etapa por calendario y pantallas. Además valida que la siembra y la cosecha no sean posteriores a hoy y que una cosecha con sucesoras no se deshaga; la cosecha se registra en `activity_log` como `season.updated`. Falta el criterio de las estrategias, que llega con EP-08.

### HU-204 · Historial con lo borrado y «Restaurar»

- **Historia:** Como agricultor, quiero ver en el historial del lote lo que borré hace poco y poder restaurarlo, para corregir un error sin perder mis datos.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `GET /api/v1/lots/{lot_id}/seasons` trae las temporadas borradas hace menos de 30 días, con `deleted_at` y `restorable_until`; las borradas hace 30 días o más no vienen
  - [ ] Lo mismo para los lotes: `GET /api/v1/lots` trae los borrados hace menos de 30 días y `POST /api/v1/lots/{lot_id}/restore` los restaura con las temporadas que se borraron con ellos; en Mi finca se ven aparte («Borrados hace poco»)
  - [ ] En la web, las borradas se ven aparte, con el rótulo «Borrada · se puede restaurar hasta <fecha>» y el botón «Restaurar», que llama a `POST /api/v1/seasons/{season_id}/restore`
  - [ ] Al restaurar, la temporada vuelve al historial y al progreso y, si existe `activity_log` (HU-178), queda el evento `season.restored`
  - [ ] Restaurar valida lo mismo que crear: si la temporada restaurada hace pasar las temporadas en curso del área del lote, o sus `follows_season_ids` ya no son válidas, responde 422 y la web dice por qué
  - [ ] Restaurar después de 30 días, o algo que no está borrado, responde 404
  - [ ] Cada botón tiene una acción definida
- **Reglas que aplican:** R9
- **Contrato que toca:** `GET /api/v1/lots/{lot_id}/seasons`, `POST /api/v1/seasons/{season_id}/restore`, `activity_log`
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. Borrar un lote o una siembra sigue siendo posible en el MVP (HU-164, HU-165); los datos quedan marcados con `deleted_at` y se borran para siempre a los 30 días. La restauración de lotes, que estaba en HU-164, se movió aquí. Decidido el 11 de octubre de 2026 (antes «cómo se listan los borrados» estaba por decidir). El contrato fija los códigos (`POST /api/v1/seasons/{season_id}/restore`): restaurar vuelve a validar el área y las temporadas de las que viene (422 si ya no cabe); pasados los 30 días, o si no está borrada, 404; lo borrado no cuenta en el área libre ni en el progreso. Los lotes borrados vienen en `GET /lots` con `restorable_until` y se restauran desde «Borrados hace poco» en Mi finca (HU-164).

### HU-166 · Borrar mi cuenta

- **Historia:** Como agricultor, quiero borrar mi cuenta y todo lo que registré, para tener control de mis datos.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `DELETE /api/v1/me` borra usuario, sesiones, lotes y temporadas (también los borrados que aún se podían restaurar) y, cuando existan (P1), sus tickets y sus eventos de `activity_log`, con las acciones de administradores sobre sus datos anonimizadas
  - [ ] Confirmación clara en la web antes de borrar
  - [ ] Prueba automática del borrado en cascada
- **Reglas que aplican:** R9
- **Notas:** No se recorta: es parte de las cuentas que el proyecto no recorta mientras haya cuentas (`CLAUDE.md`).

### HU-167 · Progreso del lote

- **Historia:** Como agricultor, quiero ver el progreso de mis lotes, para sentir que mi trabajo avanza y cuidar el suelo.
- **Prioridad:** P1 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Derivado de `seasons`: temporadas registradas, rotaciones que cumplen las reglas de filtro, hitos
  - [ ] `rotations` trae una entrada por cada relación entre una temporada y una de sus sucesoras (`from_season_id`, `to_season_id`), con `valid` y `violated_rule_ids`: la lista de reglas de `rotation_rules` que viola, vacía si cumple. Al dividir, una temporada da varias entradas; al juntar, una sucesora recibe varias
  - [ ] Una relación que no cumple se muestra como hecho, con las reglas que viola y su fuente, sin castigo ni puntaje (R3)
  - [ ] Las temporadas borradas no cuentan en el progreso mientras estén borradas
  - [ ] Cada hito cita la regla o el hecho que lo produce; ningún puntaje inventado
  - [ ] Sin temporadas, muestra un estado vacío que invita a registrar la primera
  - [ ] Prueba: un terreno dividido en dos sucesoras da dos relaciones; dos temporadas juntadas en una dan dos relaciones hacia la misma
- **Reglas que aplican:** R3, R5, R8
- **Contrato que toca:** `GET /api/v1/lots/{lot_id}/progress`
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. `violated_rule_ids` reemplaza a la regla única por par; cambió el 11 de octubre de 2026 con `follows_season_ids`. Lo borrado no cuenta en el área libre ni en el progreso (`specs/02-contratos.md`, `POST /api/v1/seasons/{season_id}/restore`).

### HU-168 · Registro, sesión y paso de invitado a cuenta

- **Historia:** Como invitado, quiero crear mi cuenta sin perder lo que ya consulté, para guardarlo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Vistas de registro, inicio de sesión y perfil con el estilo de `specs/05-frontend.md`
  - [ ] Al registrarse después de consultar estrategias sin cuenta, el municipio, el área y el cultivo anterior que escribió se ofrecen para crear su primer lote (sin dibujar), que puede dibujar después
  - [ ] Quien vuelve con sesión entra directo a Mi finca
  - [ ] P1 (con HU-141): la finca temporal del dispositivo se ofrece para guardar como un lote con una temporada por cultivo, cada una con su parte del área
- **Reglas que aplican:** R9
- **Notas:** Ajustada el 11 de octubre de 2026 al recorte del MVP: la finca temporal pasó a P1 y sin cuenta se consulta por municipio, área y cultivo anterior (HU-214).

### HU-187 · El lote vivo

- **Historia:** Como agricultor, quiero ver mi lote con sus cultivos creciendo, el clima de ahora y si es probable que haya que regar, para sentir mi finca en la app y entenderla de un vistazo.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Diorama low-poly del lote: cubos de tierra juntos, y cada cultivo en curso ocupa tantos cubos como su parte del área (al menos uno), cada uno con su arquetipo (`crops.archetype`) y su etapa (HU-150); la parte libre se ve como tierra en descanso
  - [ ] Alrededor del lote, la finca hecha de bloques: terreno de pasto, camino de tierra entre las camas, cerca de madera con faroles y portón, casa con techo escalonado, porche y materas, huerta de flores, árbol y un perro acostado. Es ambiente: no muestra ningún dato ni tiene controles
  - [ ] El diorama se puede recorrer: arrastrar para moverse, pellizcar o la rueda para acercarse, y botón para volver a encuadrar; en móvil, el gesto con un dedo mueve la escena y no la página
  - [ ] Tocar un cultivo lo elige: la línea de tiempo y la tarjeta del cultivo pasan a ese cultivo
  - [ ] Línea de tiempo del cultivo elegido que se arrastra y se reproduce, de la siembra a la cosecha estimada (HU-186); los demás cultivos del lote avanzan a la misma fecha; todo punto estimado con un año normal (lo que va después del último dato de temperatura, `thermal_data_until`) lleva «Estimación con un año normal, no es pronóstico»
  - [ ] Clima de ahora en la escena (HU-175): día, atardecer, noche, nubes, lluvia, viento y escarcha si la mínima de ahora baja de 2 °C. Nunca cambia un resultado (decisión 7); sin datos en vivo, clima neutro rotulado
  - [ ] Si el plan de agua marca déficit este mes, el suelo se ve seco con un aviso que depende del riego del lote (`irrigated`): con riego, «Riego probable este mes · estimación»; sin riego o sin definir, «La lluvia no alcanza este mes · estimación» (R10)
  - [ ] Tocar el cultivo muestra su etapa, los días desde la siembra y el método (temperatura o calendario)
  - [ ] El ambiente está animado: el viento pasa en ráfagas y las matas se inclinan en ola, la lluvia cae en bucle y salpica, las nubes derivan, las estrellas titilan, la escarcha brilla y se derrite al salir el sol, y de día, sin lluvia ni viento fuerte, de vez en cuando cruza una mariposa
  - [ ] Con movimiento reducido o en modo ligero, la escena es estática: la imagen fija del estado de ahora, con la misma información y los mismos rótulos
  - [ ] La animación se pausa cuando la pestaña no se ve y limita las partículas en móvil
- **Reglas que aplican:** R1, R5, R10
- **Notas:** Pasó a P1 el 11 de octubre de 2026: recorte del MVP. En el MVP el lote se ve en 2D: su mapa con la capa de la NASA (HU-211), su suelo, sus temporadas y la entrada a las estrategias. Los estados del clima que no ocurren ahora solo se ven en el modo simulación de desarrollo (HU-014). Cultivos perennes (caña, frutales) tienen arquetipo visual, pero su manejo por temporadas de varios años queda fuera del P0. Decidido el 11 de octubre de 2026.

### HU-169 · Mi finca con varios lotes y zonas

- **Historia:** Como agricultor, quiero ver mis lotes de mi zona en el mapa y abrir uno, para manejar mi finca y planear su próxima siembra.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] Los lotes del usuario en el mapa real con sus polígonos (HU-164) y la capa de la NASA (HU-211), cada uno con sus cultivos y etapas; los lotes sin dibujar se ven en una lista (hecho sin la capa de la NASA, que es HU-211, y sin las etapas, que esperan a HU-165)
  - [ ] **Una sola zona:** Mi finca muestra los lotes de un municipio, sin selector de zonas. Si el usuario tiene lotes en otro municipio, se ven en la lista con su municipio y abrirlos centra el mapa allí
  - [ ] Detalle de lote en 2D con su suelo (HU-185), sus temporadas en curso y cosechadas, y «Ver estrategias de rotación» (HU-214)
  - [ ] En la próxima siembra, la pregunta «¿Qué había antes en este terreno?» permite elegir una o varias temporadas cosechadas (HU-165)
  - [x] «Agregar lote» abre el mapa del municipio para dibujar (HU-164), sin descenso
  - [ ] Cada botón tiene una acción o una navegación definida
- **Reglas que aplican:** R1, R5, R9, R10
- **Notas:** Reducida el 11 de octubre de 2026 al recorte del MVP: una sola zona, sin selector, sin lote vivo (HU-187, P1), sin progreso (HU-167, P1) y sin «Restaurar» (HU-204, P1); pasó de L a M. **Entrega 1 (15 de octubre de 2026):** Mi finca en `/mi-finca` con la lista de lotes sin dibujar (municipio, área y siembras en curso) y «Agregar lote»; el lote en `/mi-finca/lotes/{{id}}` con sus siembras en curso, su suelo («sin datos» hasta HU-181) y editar o borrar. Sin mapa todavía. No se dibuja «Registrar siembra», «Dibujar en el mapa» ni «Ver estrategias de rotación» hasta que tengan función. **Ajuste del 15 de octubre (pedido por Felipe):** las pantallas siguen los marcos de Figma («D0 · Agregar lote o zona», «D1 · Editar lote», «Lote sin dibujar»): tarjeta sobre el paisaje con la mascota (`FormScene`, con la entrada de GSAP que se queda quieta en modo ligero), «Cancelar» para volver, «Editar lote» en su propia ruta (`/mi-finca/lotes/{id}/editar`) con «Borrar este lote» adentro, y el paso 2 y la edición en dos columnas. Mi finca, Agregar lote (los dos pasos), el lote y Editar lote caben sin scroll en escritorio desde 1366 × 700; en el celular el paso 2, el lote y la edición necesitan algo de scroll. **Entrega 2 (15 de octubre de 2026):** Mi finca muestra los lotes dibujados en el mapa (tocar uno lo abre) y en «En el mapa», y los demás en «Sin dibujar», con «Dibujar en el mapa». El mapa encuadra el municipio del primer lote dibujado. El lote muestra su contorno en el mapa. Pruebas en `web/src/pages/farm/farm.test.tsx` (con un doble del mapa, porque el entorno de pruebas no tiene WebGL) y recorrido real con Playwright.

### HU-211 · Capa satelital de la NASA en el mapa del lote

- **Historia:** Como agricultor, quiero ver mi lote sobre una imagen satelital y el verdor de la NASA, para reconocer mi terreno y ver de dónde salen los datos.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] El mapa del lote (MapLibre) suma capas WMTS de NASA GIBS: una imagen satelital de color real y una de NDVI, que el agricultor prende y apaga
  - [ ] Cada capa dice su producto, su fecha y su resolución, y la atribución que pida GIBS (R8)
  - [ ] Una imagen de días con nubes se ve como tal; el rótulo dice que la imagen es de la fecha indicada, no de hoy, y que el verdor es de la zona a la resolución del producto (R10)
  - [ ] Si GIBS no responde, el mapa sigue con OpenStreetMap y lo dice; dibujar el lote no depende de la capa
  - [ ] La capa es solo para ver: no entra al motor ni cambia un resultado
  - [ ] Funciona en el mapa de dibujo (HU-164) y en Mi finca (HU-169)
  - [ ] Entrada de GIBS en `sources` con sus condiciones de uso verificadas
- **Reglas que aplican:** R5, R8, R10
- **Notas:** Decisión 12. Resuelve la «capa satelital por definir» de `specs/05-frontend.md`. Los nombres exactos de las capas, su resolución y las condiciones de uso se verifican antes de usarlas (`docs/fuentes.md`). Es lo segundo que se recorta si falta tiempo, después de SMAP. Agregada el 11 de octubre de 2026.
