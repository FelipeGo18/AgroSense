---
id: EP-16
titulo: "Cuentas, lotes y progreso"
prioridad: P0
fase: [Fase 0, Evento]
rol: "Motor y API, con Web"
agentes: [motor-api, web]
subsistemas: [M8, W7, W9]
depende_de: [HU-012]
reglas: [R3, R4, R5, R7, R9]
estado: pendiente
---

# EP-16 · Cuentas, lotes y progreso

**Resultado esperado:** Un agricultor crea su cuenta, registra uno o varios lotes en una o varias zonas, los divide y junta por partes como trabaja, y al volver encuentra sus lotes con su historial (incluido lo que borró hace menos de 30 días, para restaurarlo) y su progreso. Sin cuenta, puede consultar: los datos se envían solo para calcular y no se guardan (R9).

Decisión 6 de `docs/decisiones.md` y regla R9. Cuentas en PostgreSQL propio con autenticación propia, sin servicios externos. Capacidad y orden de recorte en `docs/plan-48h.md`.

El diseño y las pantallas se prototipan en la fase 0 (EP-15); el código de cuentas se hace en el evento.

## Historias de usuario

### HU-160 · Editar mi perfil y cambiar la contraseña

- **Historia:** Como agricultor, quiero cambiar mi nombre, mi usuario y mi contraseña, para mantener mi cuenta a mi gusto y segura.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `PATCH /api/v1/me` y `POST /api/v1/me/password` del contrato
  - [ ] 409 si el usuario nuevo ya existe; 403 si la contraseña actual es incorrecta; 422 si la nueva es corta o igual a la actual
  - [ ] Cambiar la contraseña exige la actual y cierra las demás sesiones del usuario; los intentos fallidos cuentan para el límite de 429
  - [ ] En la web, Mi cuenta permite editar nombre y usuario en el sitio y cambiar la contraseña en su propia vista, con estados de guardado y error
  - [ ] No se pide ni se guarda ningún dato nuevo (R9)
- **Reglas que aplican:** R9
- **Notas:** Aprobado por Felipe el 10 de octubre de 2026. Revisión de seguridad obligatoria (agente `security`).

### HU-178 · Trazabilidad de lo que hacen agricultores y administradores

- **Historia:** Como agricultor, quiero ver qué se hizo con mi cuenta y mis lotes, y como equipo queremos saber quién hizo qué y cuándo, para confiar en la app y resolver tickets.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Tabla `activity_log` con migración, según «Trazabilidad» del contrato
  - [ ] Cada endpoint de cuenta escribe su evento en la misma transacción que el cambio; los intentos `denied` y `failed` también quedan
  - [ ] Prueba: ningún endpoint de cálculo escribe en `activity_log` (R9)
  - [ ] Prueba: ningún evento guarda contraseñas, tokens, el polígono ni valores de campos
  - [ ] El usuario de la API no puede modificar ni borrar eventos; la limpieza de 180 días corre con otro rol
  - [ ] Borrar la cuenta borra los eventos del agricultor y anonimiza las acciones de administradores sobre sus datos
  - [ ] `GET /me/activity` y la pantalla «Mi actividad» en Mi cuenta, con el estado de cada evento (`ok`, `denied`, `failed`)
  - [ ] El `request_id` de cada evento coincide con el de la terminal (HU-177)
- **Reglas que aplican:** R9
- **Notas:** Reemplaza a `admin_actions`: las acciones del administrador son eventos de la misma tabla, y su bitácora (`GET /admin/activity`) llega con HU-170 (P1). El consentimiento versión 2 lo menciona (HU-163). Definido el 10 de octubre de 2026. Revisión de seguridad obligatoria.

### HU-170 · Roles: agricultor, administrador y desarrollador

- **Historia:** Como equipo, queremos tres roles con permisos distintos, para operar la web y probarla sin mezclar datos inventados con los del agricultor.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente (documentado)
- **Criterios de aceptación:**
  - [ ] Columna `role` (`farmer`, `admin`, `developer`) y `blocked_at` en `users`, con migración
  - [ ] Endpoints de `admin` y `dev` del contrato; `403` si el rol no alcanza
  - [ ] El agricultor nunca recibe datos simulados; las respuestas simuladas llevan `simulated: true` (R5)
  - [ ] El administrador ve a cada agricultor con sus lotes, temporadas y tickets, y puede borrar y restaurar lotes y temporadas con motivo; toda acción queda en `activity_log` (HU-178)
  - [ ] El agricultor reporta un problema con un ticket y ve en Mi cuenta las acciones de soporte sobre sus datos
  - [ ] Bitácora del administrador (`GET /admin/activity`) con filtros por usuario, acción, estado y fechas
  - [ ] La API no arranca en producción si hay usuarios `developer` o la simulación está activa
  - [ ] Un usuario bloqueado no entra y pierde sus sesiones abiertas
  - [ ] Las métricas son agregadas; el consentimiento (desde la versión 2) avisa que soporte puede ver los lotes (R9)
- **Reglas que aplican:** R5, R9
- **Notas:** Definido el 10 de octubre de 2026; por ahora solo documentado. Falta decidir el resto de funciones del administrador y si su panel va en esta web. El modo desarrollador amplía HU-014. Revisión de seguridad obligatoria.

### HU-161 · Esquema de cuentas y migraciones

- **Historia:** Como desarrollador, quiero las tablas `users`, `sessions`, `lots` y `seasons` con migraciones, para guardar cuentas de forma reproducible.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Tablas y columnas del contrato, con migraciones de Alembic
  - [ ] PostgreSQL en Docker Compose con volumen persistente
  - [ ] Borrar un usuario borra en cascada sus sesiones, lotes, temporadas, tickets y sus eventos de `activity_log`
  - [ ] `municipality_id` y `crop_id` se validan contra el catálogo publicado
- **Reglas que aplican:** R7, R9
- **Contrato que toca:** base de datos de cuentas de `specs/02-contratos.md`

### HU-162 · Autenticación

- **Historia:** Como agricultor, quiero crear una cuenta e iniciar sesión de forma sencilla, para volver a mis lotes desde cualquier dispositivo.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `POST /auth/register`, `/auth/login` y `/auth/logout` del contrato, con usuario y contraseña
  - [ ] Contraseña guardada solo como hash Argon2; sesión en cookie `httpOnly`, `Secure` y `SameSite=Lax`, con el hash del token en `sessions`
  - [ ] 409 si el usuario ya existe; 429 tras 5 intentos fallidos en 15 minutos; cerrar sesión invalida la sesión en la base de datos
  - [ ] Los endpoints de cuenta responden 401 sin sesión válida
  - [ ] Ninguna clave ni secreto en el repositorio
- **Reglas que aplican:** R9
- **Notas:** Recuperar la contraseña queda en P1. Revisión de seguridad obligatoria (agente `security`).

### HU-163 · Consentimiento y tratamiento de datos

- **Historia:** Como agricultor, quiero saber qué se guarda de mí y aceptarlo, para confiar en la app.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Texto corto en español claro de qué se guarda y para qué, enlazado a la política de tratamiento de datos (Ley 1581 de 2012)
  - [ ] Sin aceptar, no se crea la cuenta
  - [ ] Se guarda `consent_version` y `consent_at`
  - [ ] La versión vigente es la **3**. Dice que se guarda la ubicación (polígono) de cada lote (HU-164), que soporte puede ver los lotes (HU-170), que se registra la actividad de la cuenta durante 180 días (HU-178) y, nuevo en la versión 3, si el lote tiene riego (`irrigated`, HU-164) y que lo que siembra se suma sin su nombre a los totales de siembras de su municipio, solo con al menos 5 cuentas (HU-200)
  - [ ] El registro envía `consent_version = 3` y la API guarda esa versión
- **Reglas que aplican:** R9
- **Notas:** La versión 2 sumó el polígono, el soporte y la actividad (10 de octubre de 2026). La versión 3 suma el riego; aprobada por Felipe el 11 de octubre de 2026. Las siembras como totales anónimos de oferta (HU-200, P1) entran en la versión 3 (`specs/01-reglas.md`, «Varias fuentes»). Por decidir: qué pasa con una cuenta que aceptó una versión anterior (por ejemplo, pedir que acepte la nueva al iniciar sesión). Mientras no haya usuarios reales, la 3 es la primera versión en producción. Supuesto por confirmar: la API responde 422 si `consent_version` no es la vigente (el contrato solo dice 422 sin `consent_accepted`). Revisión del texto legal por confirmar con la región: la Ley 1581 de 2012 es de Colombia (decisión 11).

### HU-164 · Lotes del usuario

- **Historia:** Como agricultor, quiero dibujar mis lotes en un mapa real, editarlos y borrarlos, en una o varias zonas, para tener mi finca completa y ubicada.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Endpoints de `lots` del contrato, con `geometry` (polígono GeoJSON) y restauración durante 30 días
  - [ ] El lote guarda `irrigated` (si tiene riego): el formulario pregunta «¿Este lote tiene riego?» con «Sí», «No» y «Todavía no sé»; sin respuesta queda nulo y se puede cambiar después con `PATCH`
  - [ ] Con `lot_id`, el diagnóstico y el calendario toman `irrigated` del lote; con `irrigated` nulo, se evalúa como sin riego y la limitación lo dice
  - [ ] En la web, un mapa base de OpenStreetMap centrado en el municipio, donde el agricultor dibuja el contorno del lote; el área se calcula sola. La capa satelital entra solo si se aprueba su licencia
  - [ ] El polígono debe ser válido y caer dentro de su municipio (422 si no), y se ve el límite municipal mientras se dibuja
  - [ ] Si no puede o no quiere dibujar, escribe el área a mano y el lote queda sin ubicación; puede dibujarlo después
  - [ ] Un usuario no ve ni modifica lotes ajenos (404)
  - [ ] «Editar lote», desde la cabecera del lote, cambia el nombre, el contorno (moviendo los puntos en el mapa) y el riego; dice que al cambiar el riego se recalculan el diagnóstico, el calendario y el agua del lote, y que las siembras ya registradas guardan el diagnóstico que vieron
  - [ ] Editar el lote a un área menor que la de sus temporadas en curso responde 422
  - [ ] «Borrar este lote» pide confirmación y dice hasta qué fecha se puede restaurar; en Mi finca, los lotes borrados hace menos de 30 días se ven aparte («Borrados hace poco») con «Restaurar» (`POST /api/v1/lots/{lot_id}/restore`)
- **Reglas que aplican:** R7, R9
- **Notas:** Un `PATCH` que deja el lote más chico que el área de sus temporadas en curso responde 422 y la pantalla lo avisa (aprobado por Felipe el 11 de octubre de 2026). Con el polígono, la ficha del lote muestra su suelo estimado (HU-182). La ubicación del lote es un dato personal: entra en el texto de consentimiento (HU-163). El clima de NASA POWER sigue siendo el de la celda de unos 50 km que contiene al lote, no del lote; el polígono abre la puerta a datos por lote en P1 (HU-043). Mapa y librería en `specs/05-frontend.md`. Ampliado el 10 de octubre de 2026. `irrigated` se agregó el 11 de octubre de 2026: con riego, la falta de lluvia no es un riesgo en la señal `water` (HU-071). Es un dato mínimo que se usa (R9); el consentimiento versión 3 lo nombra (HU-163).

### HU-165 · Temporadas e historial del lote

- **Historia:** Como agricultor, quiero registrar qué sembré, en qué parte del lote, qué había antes en ese terreno y cuándo coseché, dividiendo y juntando partes como yo trabajo, para que las recomendaciones usen mi historial real.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Endpoints de `seasons` del contrato
  - [ ] Un lote puede tener varios cultivos a la vez, cada uno en una parte de su área (`area_ha`); la suma de las temporadas en curso no pasa del área del lote (422)
  - [ ] Al registrar una siembra, la web pregunta «¿Qué había antes en este terreno?» y deja elegir **una o varias** temporadas cosechadas del lote, o ninguna («Nada: es la primera siembra aquí»). Se guardan en `follows_season_ids`
  - [ ] **Dividir:** una temporada cosechada puede tener varias sucesoras. Ejemplo: al cosechar una papa de 1 ha, se siembran 0,5 ha de fresa y 0,5 ha de ajo, las dos con la papa en `follows_season_ids`
  - [ ] **Juntar:** una temporada puede venir de varias. Ejemplo: después de cosechar la fresa y el ajo, se siembra 1 ha de arveja con las dos en `follows_season_ids`
  - [ ] Validaciones (422): cada temporada de `follows_season_ids` es del mismo lote, está cosechada y su `harvest_date` es igual o anterior a la `sowing_date` de la nueva; la suma de `area_ha` de las sucesoras de una temporada no pasa de su `area_ha`
  - [ ] Cada temporada guarda el diagnóstico visto al sembrar (`diagnosis_light`, `diagnosis_action`, `diagnosis_irrigated`) con `dataset_version` y `rules_version`: es el diagnóstico de la ventana que empieza en su `sowing_date`
  - [ ] `diagnosis_action` acepta solo `sow`, `other_window`, `rotate` y `review_data`; si el agricultor no consultó el diagnóstico, esos campos van nulos
  - [ ] Las rotaciones de una temporada nueva reciben los cultivos de todas las temporadas de las que viene su terreno
  - [ ] El historial del lote (`GET /lots/{lot_id}/seasons`) incluye las temporadas borradas hace menos de 30 días (HU-204)
- **Reglas que aplican:** R4, R9
- **Contrato que toca:** `seasons` (con `follows_season_ids`), `POST /api/v1/lots/{lot_id}/seasons`, `PATCH /api/v1/seasons/{season_id}`, tabla de errores
- **Notas:** Las partes son de área, no se dibujan en el mapa; el suelo es el mismo para todo el lote. Decidido el 11 de octubre de 2026 y ampliado el mismo día: el agricultor divide su lote como quiera; una temporada puede venir de varias y tener varias sucesoras (`follows_season_ids`, antes `follows_season_id` singular). Ejemplo de uso: hoy siembra papa en la mitad; en un mes divide la otra mitad en fresa y ajo; al cosechar la papa, reparte ese terreno. Pasa de M a L. **Error del contrato a corregir:** al juntar dos temporadas de 1 ha en una de 2 ha, la sucesora mide 2 ha y pasa del área de cada anterior, así que la validación actual daría 422 en un caso válido. Propuesta para Haider o Felipe: validar que el área de una temporada no pase de la suma de las áreas de las que viene más el área libre del lote, y que la suma de las sucesoras de una temporada que solo vienen de ella no pase de su área. Por decidir también: si una sucesora puede ocupar parte del terreno anterior más terreno libre (por ejemplo, 1,5 ha después de una papa de 1 ha); qué diagnóstico se guarda en `diagnosis_light` cuando las dos luces difieren y si hay que guardar los pesos con que se vio (R4); el orden de `previous_crop_ids` cuando hay varias anteriores cosechadas el mismo día.

### HU-204 · Historial con lo borrado y «Restaurar»

- **Historia:** Como agricultor, quiero ver en el historial del lote lo que borré hace poco y poder restaurarlo, para corregir un error sin perder mis datos.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `GET /api/v1/lots/{lot_id}/seasons` trae las temporadas borradas hace menos de 30 días, con `deleted_at` y `restorable_until`; las borradas hace 30 días o más no vienen
  - [ ] En la web, las borradas se ven aparte, con el rótulo «Borrada · se puede restaurar hasta <fecha>» y el botón «Restaurar», que llama a `POST /api/v1/seasons/{season_id}/restore`
  - [ ] Al restaurar, la temporada vuelve al historial y al progreso, y queda el evento `season.restored` en `activity_log`
  - [ ] Restaurar valida lo mismo que crear: si la temporada restaurada hace pasar las temporadas en curso del área del lote, o sus `follows_season_ids` ya no son válidas, responde 422 y la web dice por qué
  - [ ] Restaurar después de 30 días responde 404
  - [ ] Cada botón tiene una acción definida
- **Reglas que aplican:** R9
- **Contrato que toca:** `GET /api/v1/lots/{lot_id}/seasons`, `POST /api/v1/seasons/{season_id}/restore`, `activity_log`
- **Notas:** Decidido el 11 de octubre de 2026 (antes «cómo se listan los borrados» estaba por decidir). Supuestos por confirmar: el 422 al restaurar y el 404 pasados 30 días (el contrato no fija esos códigos). Los lotes borrados vienen en `GET /lots` con `restorable_until` y se restauran desde «Borrados hace poco» en Mi finca (HU-164).

### HU-166 · Borrar mi cuenta

- **Historia:** Como agricultor, quiero borrar mi cuenta y todo lo que registré, para tener control de mis datos.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `DELETE /api/v1/me` borra usuario, sesiones, lotes, temporadas, tickets y sus eventos de `activity_log` (las acciones de administradores sobre sus datos quedan anonimizadas)
  - [ ] Confirmación clara en la web antes de borrar
  - [ ] Prueba automática del borrado en cascada
- **Reglas que aplican:** R9

### HU-167 · Progreso del lote

- **Historia:** Como agricultor, quiero ver el progreso de mis lotes, para sentir que mi trabajo avanza y cuidar el suelo.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
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
- **Notas:** `violated_rule_ids` reemplaza a la regla única por par; cambió el 11 de octubre de 2026 con `follows_season_ids`. Supuesto por confirmar: que las temporadas borradas no cuenten en el progreso (el contrato no lo dice).

### HU-168 · Registro, sesión y paso de invitado a cuenta

- **Historia:** Como invitado, quiero crear mi cuenta sin perder lo que ya consulté, para guardarlo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Vistas de registro, inicio de sesión y perfil con el estilo de `specs/05-frontend.md`
  - [ ] Al registrarse, la finca temporal del dispositivo se ofrece para guardar como un lote con una temporada por cultivo, cada una con su parte del área
  - [ ] Quien vuelve con sesión entra directo a Mi finca, sin descenso
- **Reglas que aplican:** R9

### HU-187 · El lote vivo

- **Historia:** Como agricultor, quiero ver mi lote con sus cultivos creciendo, el clima de ahora y si es probable que haya que regar, para sentir mi finca en la app y entenderla de un vistazo.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Diorama low-poly del lote: cubos de tierra juntos, y cada cultivo en curso ocupa tantos cubos como su parte del área (al menos uno), cada uno con su arquetipo (`crops.archetype`) y su etapa (HU-150); la parte libre se ve como tierra en descanso
  - [ ] Alrededor del lote, la finca hecha de bloques: terreno de pasto, camino de tierra entre las camas, cerca de madera con faroles y portón, casa con techo escalonado, porche y materas, huerta de flores, árbol y un perro acostado. Es ambiente: no muestra ningún dato ni tiene controles
  - [ ] El diorama se puede recorrer: arrastrar para moverse, pellizcar o la rueda para acercarse, y botón para volver a encuadrar; en móvil, el gesto con un dedo mueve la escena y no la página
  - [ ] Tocar un cultivo lo elige: la línea de tiempo y la tarjeta del cultivo pasan a ese cultivo
  - [ ] Línea de tiempo del cultivo elegido que se arrastra y se reproduce, de la siembra a la cosecha estimada (HU-186); los demás cultivos del lote avanzan a la misma fecha; todo punto estimado con un año normal (lo que va después del último dato de temperatura, `thermal_data_until`) lleva «Estimación con un año normal, no es pronóstico»
  - [ ] Clima de ahora en la escena (HU-175): día, atardecer, noche, nubes, lluvia, viento y escarcha si la mínima de ahora baja de 2 °C. Nunca cambia un resultado (decisión 7); sin datos en vivo, clima neutro rotulado
  - [ ] Si el plan de agua marca déficit este mes, el suelo se ve seco con el aviso «Riego probable este mes · estimación» (R10)
  - [ ] Tocar el cultivo muestra su etapa, los días desde la siembra y el método (temperatura o calendario)
  - [ ] El ambiente está animado: el viento pasa en ráfagas y las matas se inclinan en ola, la lluvia cae en bucle y salpica, las nubes derivan, las estrellas titilan, la escarcha brilla y se derrite al salir el sol, y de día, sin lluvia ni viento fuerte, de vez en cuando cruza una mariposa
  - [ ] Con movimiento reducido o en modo ligero, la escena es estática: la imagen fija del estado de ahora, con la misma información y los mismos rótulos
  - [ ] La animación se pausa cuando la pestaña no se ve y limita las partículas en móvil
- **Reglas que aplican:** R1, R5, R10
- **Notas:** Los estados del clima que no ocurren ahora solo se ven en el modo simulación de desarrollo (HU-014). Cultivos perennes (caña, frutales) tienen arquetipo visual, pero su manejo por temporadas de varios años queda fuera del P0. Decidido el 11 de octubre de 2026.

### HU-169 · Mi finca con varios lotes y zonas

- **Historia:** Como agricultor, quiero ver todos mis lotes en el paisaje y cambiar de zona, para manejar mi finca completa.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Los lotes del usuario en el mapa real con sus polígonos (HU-164), cada uno con sus cultivos y etapas; al abrir uno, el lote vivo (HU-187)
  - [ ] Selector de zona si hay lotes en varios municipios
  - [ ] Detalle de lote con ahora, próxima siembra, agua e historial (con lo borrado y «Restaurar», HU-204)
  - [ ] En «Próxima siembra», la pregunta «¿Qué había antes en este terreno?» permite elegir una o varias temporadas cosechadas (HU-165)
  - [ ] Agregar lote con mini descenso al municipio elegido
- **Reglas que aplican:** R1, R5, R9, R10
