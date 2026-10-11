---
id: EP-16
titulo: "Cuentas, lotes y progreso"
prioridad: P0
fase: [Fase 0, Evento]
rol: "Motor y API, con Web"
agentes: [motor-api, web]
subsistemas: [M8, W7, W9]
depende_de: [HU-012]
reglas: [R4, R5, R7, R9]
estado: pendiente
---

# EP-16 · Cuentas, lotes y progreso

**Resultado esperado:** Un agricultor crea su cuenta, registra uno o varios lotes en una o varias zonas, y al volver encuentra sus lotes con su historial y su progreso. Sin cuenta, puede consultar sin que nada salga de su dispositivo.

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

### HU-170 · Roles: agricultor, administrador y desarrollador

- **Historia:** Como equipo, queremos tres roles con permisos distintos, para operar la web y probarla sin mezclar datos inventados con los del agricultor.
- **Prioridad:** P1 · **Tamaño:** L · **Estado:** pendiente (documentado)
- **Criterios de aceptación:**
  - [ ] Columna `role` (`farmer`, `admin`, `developer`) y `blocked_at` en `users`, con migración
  - [ ] Endpoints de `admin` y `dev` del contrato; `403` si el rol no alcanza
  - [ ] El agricultor nunca recibe datos simulados; las respuestas simuladas llevan `simulated: true` (R5)
  - [ ] El administrador ve a cada agricultor con sus lotes, temporadas y tickets, y puede borrar y restaurar lotes y temporadas con motivo; toda acción queda en `admin_actions`
  - [ ] El agricultor reporta un problema con un ticket y ve en Mi cuenta las acciones de soporte sobre sus datos
  - [ ] La API no arranca en producción si hay usuarios `developer` o la simulación está activa
  - [ ] Un usuario bloqueado no entra y pierde sus sesiones abiertas
  - [ ] Las métricas son agregadas; el consentimiento (versión 2) avisa que soporte puede ver los lotes (R9)
- **Reglas que aplican:** R5, R9
- **Notas:** Definido el 10 de octubre de 2026; por ahora solo documentado. Falta decidir el resto de funciones del administrador y si su panel va en esta web. El modo desarrollador amplía HU-014. Revisión de seguridad obligatoria.

### HU-161 · Esquema de cuentas y migraciones

- **Historia:** Como desarrollador, quiero las tablas `users`, `sessions`, `lots` y `seasons` con migraciones, para guardar cuentas de forma reproducible.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Tablas y columnas del contrato, con migraciones de Alembic
  - [ ] PostgreSQL en Docker Compose con volumen persistente
  - [ ] Borrar un usuario borra en cascada sus sesiones, lotes y temporadas
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
- **Reglas que aplican:** R9

### HU-164 · Lotes del usuario

- **Historia:** Como agricultor, quiero dibujar mis lotes en un mapa real, editarlos y borrarlos, en una o varias zonas, para tener mi finca completa y ubicada.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Endpoints de `lots` del contrato, con `geometry` (polígono GeoJSON) y restauración durante 30 días
  - [ ] En la web, un mapa con imagen satelital centrado en el municipio, donde el agricultor dibuja el contorno del lote; el área se calcula sola
  - [ ] El polígono debe ser válido y caer dentro de su municipio (422 si no), y se ve el límite municipal mientras se dibuja
  - [ ] Si no puede o no quiere dibujar, escribe el área a mano y el lote queda sin ubicación; puede dibujarlo después
  - [ ] Un usuario no ve ni modifica lotes ajenos (404)
- **Reglas que aplican:** R7, R9
- **Notas:** La ubicación del lote es un dato personal: entra en el texto de consentimiento (HU-163). El clima de NASA POWER sigue siendo el de la celda de unos 50 km que contiene al lote, no del lote; el polígono abre la puerta a datos por lote en P1 (HU-043). Mapa y librería en `specs/05-frontend.md`. Ampliado el 10 de octubre de 2026.

### HU-165 · Temporadas e historial del lote

- **Historia:** Como agricultor, quiero registrar qué sembré y cuándo coseché, para que las recomendaciones usen mi historial.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Endpoints de `seasons` del contrato
  - [ ] Cada temporada guarda el diagnóstico visto al sembrar con `dataset_version` y `rules_version`
  - [ ] Las rotaciones del lote reciben los cultivos de sus temporadas anteriores
- **Reglas que aplican:** R4, R9

### HU-166 · Borrar mi cuenta

- **Historia:** Como agricultor, quiero borrar mi cuenta y todo lo que registré, para tener control de mis datos.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] `DELETE /api/v1/me` borra usuario, sesiones, lotes y temporadas
  - [ ] Confirmación clara en la web antes de borrar
  - [ ] Prueba automática del borrado en cascada
- **Reglas que aplican:** R9

### HU-167 · Progreso del lote

- **Historia:** Como agricultor, quiero ver el progreso de mis lotes, para sentir que mi trabajo avanza y cuidar el suelo.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Derivado de `seasons`: temporadas registradas, rotaciones que cumplen las reglas de filtro, hitos
  - [ ] Cada hito cita la regla o el hecho que lo produce; ningún puntaje inventado
  - [ ] Sin temporadas, muestra un estado vacío que invita a registrar la primera
- **Reglas que aplican:** R5, R8

### HU-168 · Registro, sesión y paso de invitado a cuenta

- **Historia:** Como invitado, quiero crear mi cuenta sin perder lo que ya consulté, para guardarlo.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Vistas de registro, inicio de sesión y perfil con el estilo de `specs/05-frontend.md`
  - [ ] Al registrarse, la finca temporal del dispositivo se ofrece para guardar como lotes, uno por cultivo con su parte del área
  - [ ] Quien vuelve con sesión entra directo a Mi finca, sin descenso
- **Reglas que aplican:** R9

### HU-169 · Mi finca con varios lotes y zonas

- **Historia:** Como agricultor, quiero ver todos mis lotes en el paisaje y cambiar de zona, para manejar mi finca completa.
- **Prioridad:** P0 · **Tamaño:** L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Paisaje con los lotes del usuario, cada uno con su cultivo y etapa
  - [ ] Selector de zona si hay lotes en varios municipios
  - [ ] Detalle de lote con ahora, próxima siembra, agua e historial
  - [ ] Agregar lote con mini descenso al municipio elegido
- **Reglas que aplican:** R1, R5, R9, R10
