# Contratos de datos y de API

Los identificadores del código van en inglés y en `snake_case` para evitar tildes; los textos de la interfaz van en español. En lugar de una tabla larga de indicadores, se usan pocas tablas por granularidad: así cada fila tiene una llave clara y cada columna una unidad fija.

> **Estado:** propuesta congelable. Se congela en HU-011 y HU-012. **Responsables: Haider y Felipe.** Después de congelado, cualquier cambio lo hace o lo aprueba uno de los dos, porque rompe el trabajo en paralelo.

## Tablas publicadas (Parquet)

| Tabla | Llave primaria | Columnas principales | Origen |
|---|---|---|---|
| `municipalities` | `municipality_id` (DIVIPOLA, 5 dígitos) | `name`, `department_id`, `department`, `lat`, `lon`, `altitude_m`, `climate_cell_elevation_m` (altura de la celda de NASA POWER que lo cubre), `source_ids` | DANE, modelo de elevación y NASA |
| `crops` | `crop_id` | `name_es`, `kind` (`crop`, `cover` para abono verde o cobertura, `fallow` para descanso), `archetype` (cómo se dibuja: `tuber`, `root`, `bulb`, `leafy`, `cereal`, `climbing_legume`, `bush_legume`, `creeping`, `tall_grass`, `shrub_fruit`, `tree_fruit`), `family`, `cycle_months`, `sowing_semesters`, `water_need`, `root_type`, `fixes_nitrogen`, `altitude_min_m`, `altitude_max_m`, `base_temp_c`, `ph_min`, `ph_max` (rango que tolera), `ph_opt_min`, `ph_opt_max` (rango óptimo) — nulos si no hay fuente —, `source_ids` | Catálogo |
| `rotation_rules` | `rule_id` | `kind` (`filter`, `bonus`, `penalty`), `condition`, `effect`, `criterion`, `source_id` | Catálogo |
| `climate_semester` | `municipality_id`, `year`, `semester` | `precip_mm`, `precip_normal_mm`, `precip_anomaly_pct`, `temp_mean_c`, `temp_anomaly_c`, `valid_days`, `quality`, `source_id` | NASA |
| `climate_day` | `municipality_id`, `date` | `temp_min_c`, `temp_max_c`, `quality`, `source_id` | NASA (para la etapa del cultivo, HU-150) |
| `climate_normal_doy` | `municipality_id`, `doy` (1 a 366) | `temp_min_c`, `temp_max_c` normales de ese día del año (promedio 1991–2020, suavizado), `source_id` | NASA (para estimar el crecimiento después de hoy, HU-186) |
| `climate_risk_month` | `municipality_id`, `month` (1 a 12) | `frost_freq_pct` (porcentaje de años con al menos un día de mínima menor que 2 °C en ese mes), `frost_days_mean`, `heavy_rain_days_mean` (P1), `dry_window_freq_pct` (P1, años con 3 días seguidos de menos de 5 mm), `blight_days_mean` (P1, días favorables a la gota), `years`, `quality`, `source_id` | NASA (HU-045) |
| `climate_month` | `municipality_id`, `year`, `month` | `precip_mm`, `precip_normal_mm`, `precip_dry_mm` (año seco), `et0_mm`, `et0_normal_mm`, `quality`, `source_id` | NASA |
| `crop_stages` | `crop_id`, `stage` | `days`, `kc`, `gdd` (grados-día que cierran la etapa; nulo si no hay fuente), `frost_sensitive` (la helada daña en esta etapa), `source_id` | Catálogo (FAO-56 o fuente local) |
| `supply_semester` | `municipality_id`, `crop_id`, `year`, `semester` | `planted_ha`, `harvested_ha`, `production_t`, `yield_t_ha`, `planted_change_pct`, `dept_share_pct`, `preliminary`, `quality`, `source_id` | EVA |
| `market_month` (P1) | `crop_id`, `market_id`, `month` | `price_cop_kg`, `volume_t`, `seasonal_index`, `quality`, `source_id` | SIPSA |
| `municipality_boundaries` | `municipality_id` | `geometry` (polígono WGS84 simplificado), `source_id` | DANE (Marco Geoestadístico Nacional) |
| `soil_grid` | `cell_id` | `lon`, `lat`, `ph`, `ph_p05`, `ph_p95`, `soc_g_kg` (carbono orgánico), `nitrogen_g_kg`, `clay_pct`, `sand_pct`, `silt_pct`, `texture_class`; promedio ponderado de 0 a 30 cm de cada celda de 250 m de la región; `source_id` | SoilGrids de ISRIC (HU-181) |
| `soil_municipality` | `municipality_id` | Las mismas propiedades que `soil_grid`, como mediana de las celdas dentro del municipio, más `cells`, `quality` y `source_id` | SoilGrids (HU-181) |
| `sources` | `source_id` | `name`, `institution`, `url`, `downloaded_at`, `period_covered`, `license`, `notes` | Todas |
| `manifest.json` | — | `dataset_version`, `rules_version`, `created_at`, `region`, filas y cobertura por tabla | Pipeline |

### Supuestos por confirmar en la fase 0

- Todas las temperaturas publicadas (`climate_day`, `climate_semester`, `climate_month` y `climate_risk_month`) se corrigen por altitud: la celda de NASA POWER tiene unos 50 km y su altura puede diferir cientos de metros de la del municipio. La corrección usa la diferencia entre `altitude_m` y `climate_cell_elevation_m` con un gradiente térmico con fuente (HU-044). Así la etapa del cultivo, la ET0 y las heladas usan la misma temperatura.
- El umbral de helada es una mínima menor que 2 °C a 2 m, el criterio de amenaza que usa la UPRA con datos del IDEAM.

- Que EVA trae código DIVIPOLA (HU-001).
- Que el semestre A va de enero a junio y el B de julio a diciembre. La metodología EVA define periodos de recolección que hay que mapear con cuidado.
- `planted_change_pct` compara contra el promedio de los tres mismos semestres anteriores.
- `quality` toma valores como `ok` o `partial` (por ejemplo, cuando faltan semestres previos o hay pocos días válidos). La lista exacta se fija en HU-011.

## Base de datos de cuentas (PostgreSQL)

Decisión 6 de `docs/decisiones.md` y regla R9. PostgreSQL propio en Docker, aparte del dataset publicado. El motor no la lee: la API consulta los lotes y le pasa al motor solo lo que necesita.

| Tabla | Llave primaria | Columnas principales | Notas |
|---|---|---|---|
| `users` | `user_id` (UUID) | `username` (único), `password_hash`, `display_name`, `role` (`farmer` por defecto; ver «Roles»), `blocked_at` (nulo si no está bloqueado), `consent_version`, `consent_at`, `created_at`, `updated_at` | Sin correo, celular, documento de identidad ni dirección. La contraseña se guarda solo como hash Argon2 |
| `sessions` | `session_id` (UUID) | `user_id`, `token_hash`, `created_at`, `expires_at` | Una fila por sesión abierta. Se guarda el hash del token, nunca el token. Vence a los 30 días |
| `lots` | `lot_id` (UUID) | `user_id`, `municipality_id`, `name`, `geometry` (polígono GeoJSON en WGS84, dibujado en el mapa; nulo si el usuario aún no lo dibuja), `area_ha`, `deleted_at`, `created_at`, `updated_at` | Un usuario tiene uno o varios lotes; la «zona» es el municipio (R7). Con polígono, `area_ha` se calcula de él y el polígono debe caer dentro de su municipio |
| `seasons` | `season_id` (UUID) | `lot_id`, `crop_id`, `sowing_date`, `harvest_date` (nula si sigue en curso), `diagnosis_light`, `diagnosis_action`, `dataset_version`, `rules_version`, `deleted_at`, `created_at` | Una temporada por cultivo y ciclo en el lote. Guarda el diagnóstico que se vio al sembrar, con sus versiones (R4) |

- Borrar un usuario borra en cascada, y para siempre, sus sesiones, lotes, temporadas y tickets (R9).
- Borrar un lote o una temporada es reversible: se marca `deleted_at` y se puede restaurar durante 30 días; después se borra para siempre. El agricultor y el administrador pueden restaurar.
- Un polígono de lote debe ser válido (sin cruces), tener área mayor que cero y caer dentro de `municipality_boundaries` de su municipio; si no, 422.
- `activity_log`: trazabilidad de lo que hacen agricultores y administradores. Ver «Trazabilidad» más abajo.
- El suelo de un lote **no se guarda**: la API lo calcula al vuelo como la mediana de las celdas de `soil_grid` que toca su polígono. Un lote sin polígono usa `soil_municipality`.
- `support_tickets` (P1): `ticket_id`, `user_id`, `lot_id` (opcional), `message`, `status` (`open`, `in_progress`, `closed`), `created_at`, `closed_at`.
- `crop_id` y `municipality_id` deben existir en el catálogo publicado; si no, 422.
- Un lote tiene como máximo una temporada en curso (`harvest_date` nula). Crear otra sin cerrar la anterior, o con `sowing_date` anterior a la cosecha previa, responde 422.
- El **progreso** no se guarda: la API lee las temporadas del lote y le pide al motor que evalúe las reglas de filtro sobre ese historial (temporadas registradas, rotaciones que cumplen las reglas, hitos).

### Trazabilidad: `activity_log` (HU-178)

Registro de lo que hace cada persona con una cuenta: el agricultor sobre sus datos y el administrador sobre los datos de otros. Es distinto de los logs de la terminal (HU-177, más abajo en «Logs de la terminal»): aquellos son para operar el servidor y se pierden; este se guarda en PostgreSQL para poder responder «quién hizo qué, cuándo y sobre qué».

| Columna | Qué guarda |
|---|---|
| `event_id` (UUID) | Llave primaria |
| `occurred_at` | Fecha y hora UTC |
| `request_id` | El mismo identificador de la petición que sale en la terminal y en la cabecera `X-Request-ID`: une las dos trazas |
| `actor_user_id`, `actor_role` | Quién lo hizo. Nulo solo en un inicio de sesión fallido con un usuario que no existe |
| `subject_user_id` | De quién son los datos afectados. Igual a `actor_user_id` cuando el agricultor actúa sobre lo suyo |
| `action` | Qué hizo, del catálogo de abajo |
| `object_type`, `object_id` | Sobre qué: `user`, `session`, `lot`, `season` o `ticket`, y su id |
| `outcome` | Estado del evento: `ok`, `denied` (sin permiso, bloqueado, demasiados intentos) o `failed` (error de validación o interno) |
| `ticket_id`, `reason` | Obligatorios en las acciones de un administrador sobre datos ajenos |
| `details` (JSONB) | Solo los **nombres** de los campos que cambiaron (por ejemplo `["name", "geometry"]`), nunca sus valores |

Catálogo de `action`:

| Quién | Acciones |
|---|---|
| Agricultor | `auth.registered`, `auth.login`, `auth.login_failed`, `auth.logout`, `auth.password_changed`, `profile.updated`, `consent.accepted`, `lot.created`, `lot.updated`, `lot.deleted`, `lot.restored`, `season.created`, `season.updated`, `season.deleted`, `season.restored`, `ticket.opened`, `account.deleted` |
| Administrador (P1) | `admin.user_viewed`, `admin.user_created`, `admin.user_blocked`, `admin.user_unblocked`, `admin.role_changed`, `admin.lot_deleted`, `admin.lot_restored`, `admin.season_deleted`, `admin.season_restored`, `admin.ticket_updated`, `admin.activity_viewed` |
| Desarrollador (solo desarrollo) | `dev.fixtures_loaded` |

Reglas del registro:

- **Nunca se guardan** contraseñas, tokens, cookies, el polígono ni los valores de los campos; tampoco el usuario que se intentó en un inicio de sesión fallido (podría ser una contraseña escrita en el campo equivocado), ni la IP.
- El evento se escribe **en la misma transacción** que el cambio: no hay cambio sin traza ni traza de un cambio que no ocurrió. Los intentos `denied` y `failed` se escriben aparte.
- **Solo se agrega.** El usuario de base de datos de la API tiene `INSERT` y `SELECT` sobre `activity_log`, no `UPDATE` ni `DELETE`; solo la tarea de limpieza y el borrado de cuenta usan otro rol.
- Se conserva **180 días** y luego se borra.
- **Los endpoints de cálculo no escriben aquí** (R9): consultar un diagnóstico, una rotación o un plan de agua no deja rastro en la base de datos.
- **Al borrar la cuenta** se borran los eventos del agricultor. Las acciones de administradores sobre sus datos se conservan, pero con `subject_user_id`, `object_id` y `reason` en nulo, para no perder quién hizo qué sin guardar de quién era.
- Lo dice el consentimiento versión 2 (HU-163): «registramos lo que hace con su cuenta durante 180 días para su seguridad».

Respuesta de `GET /api/v1/me/activity` (la de `GET /api/v1/admin/activity` es igual, más `actor_user_id`, `subject_user_id` y `request_id`):

```json
{
  "items": [
    {
      "event_id": "5f0c…",
      "occurred_at": "2026-11-14T15:02:11Z",
      "action": "lot.restored",
      "actor_role": "admin",
      "object_type": "lot",
      "object_id": "a81e…",
      "outcome": "ok",
      "ticket_id": "c4d2…",
      "details": {"fields": []}
    }
  ],
  "next_before": "2026-11-14T15:02:11Z"
}
```

`next_before` es nulo cuando no hay más páginas. Al agricultor nunca se le muestra quién es el administrador, solo `actor_role`.

### Logs de la terminal (HU-177)

No son parte de la API ni se consultan desde la web; se documentan aquí porque fijan qué se puede escribir y qué no. Los escribe `structlog` a la salida estándar: con color en desarrollo y una línea JSON por evento en producción.

```json
{"ts": "2026-11-14T15:02:11.204Z", "level": "info", "event": "request", "request_id": "9b1e…", "method": "POST", "route": "/api/v1/lots/{lot_id}/restore", "status": 200, "duration_ms": 18, "user_id": "3c7a…", "role": "farmer", "dataset": "2026.11.1", "rules": "1.4.0"}
```

| Campo | Siempre | Notas |
|---|---|---|
| `ts`, `level`, `event`, `request_id` | Sí | `level`: `debug` (solo desarrollo), `info`, `warning` (`403`, `429`), `error` (`500`, con la traza del error) |
| `method`, `route`, `status`, `duration_ms` | En peticiones | `route` es la plantilla de la ruta, no la URL con sus parámetros de consulta |
| `user_id`, `role` | Si hay sesión | Nunca el `username` ni el nombre |
| `dataset`, `rules` | En endpoints de cálculo | Versiones usadas (R4) |

Nunca se escriben: contraseñas, tokens, cookies, la cabecera `Authorization`, polígonos ni los cuerpos de los endpoints de cálculo (R9). Un procesador de redacción borra esas llaves de cualquier evento.

## Endpoints

| Endpoint | Uso | Prioridad |
|---|---|---|
| `GET /api/v1/catalogs/municipalities` | Municipios habilitados de la región: `municipality_id`, `name`, `department`, `lat`, `lon` | P0 |
| `GET /api/v1/catalogs/crops` | Cultivos habilitados: `crop_id`, `name_es`, `kind`, `family`, `sowing_semesters`. El diagnóstico solo acepta `kind = crop`; las rotaciones aceptan los tres | P0 |
| `GET /api/v1/catalogs/municipalities/{municipality_id}/soil` | Suelo estimado del municipio (`soil_municipality`) con su incertidumbre y `source_id` | P0 |
| `GET /api/v1/trends?municipality_id=&crop_id=` | Series para las gráficas (ver «Cuerpos y respuestas») | P0 |
| `POST /api/v1/diagnostics` | Diagnóstico de una ventana de siembra | P0 |
| `POST /api/v1/rotations` | Ranking de rotaciones según prioridades | P0 |
| `POST /api/v1/water-plans` | Plan de agua de una finca | P0 |
| `POST /api/v1/calendar` | Calendario de un cultivo en un municipio: mes a mes, qué tan bueno es sembrar y el riesgo de heladas; en P1 también aguaceros (cuándo abonar), ventanas secas (labores y cosecha) y gota (ver «Cuerpos y respuestas») | P0 |
| `GET /api/v1/version` | Versiones del dataset y de las reglas, región y fuentes (HU-122) | P0 |
| `POST /api/v1/scenarios` | Escenario hipotético y diferencias con el caso base | P1 |

Condiciones actuales (decisión 7):

| Endpoint | Uso | Prioridad |
|---|---|---|
| `GET /api/v1/conditions?municipality_id=` | Condición aproximada actual del municipio para la escena, de Open-Meteo: `status`, `precipitation_mm`, `cloud_cover_pct`, `wind_speed_kmh`, `wind_direction_deg`, `temp_c`, `observed_at`, `source_id`. Caché de 15 minutos. Solo el «ahora», sin pronóstico | P0 |

`status` usa los valores de `specs/01-reglas.md`: `available` o `insufficient_data`. Sin datos del proveedor responde `200` con `status = insufficient_data` y valores nulos. Nunca entra al motor. La noche y el día los calcula la web con `lat` y `lon` del catálogo.

Endpoints de cuenta (requieren sesión, salvo `register` y `login`):

| Endpoint | Uso | Prioridad |
|---|---|---|
| `POST /api/v1/auth/register` | Crear cuenta: `username`, `password`, `display_name`, `consent_version` y `consent_accepted`. Sin `consent_accepted = true`, responde 422 | P0 |
| `POST /api/v1/auth/login` | Iniciar sesión con `username` y `password`; deja la cookie de sesión | P0 |
| `POST /api/v1/auth/logout` | Cerrar la sesión actual | P0 |
| `GET /api/v1/me` | Perfil y consentimiento del usuario | P0 |
| `PATCH /api/v1/me` | Editar el perfil: `display_name` y `username`. Responde el perfil actualizado | P0 |
| `POST /api/v1/me/password` | Cambiar la contraseña con `current_password` y `new_password`. Cierra las demás sesiones del usuario; la actual sigue abierta | P0 |
| `DELETE /api/v1/me` | Borrar la cuenta con sus sesiones, lotes y temporadas | P0 |
| `GET /api/v1/lots` · `POST /api/v1/lots` | Listar y crear lotes | P0 |
| `GET`, `PATCH`, `DELETE /api/v1/lots/{lot_id}` | Ver, editar y borrar un lote. `GET` trae la temporada en curso con su etapa estimada (ver «Cuerpos de cuenta»). `DELETE` es reversible durante 30 días | P0 |
| `POST /api/v1/lots/{lot_id}/restore` | Restaurar un lote borrado hace menos de 30 días | P0 |
| `GET /api/v1/catalogs/municipalities/{municipality_id}/boundary` | Límite del municipio en GeoJSON, para centrar el mapa y validar el dibujo en la web | P0 |
| `GET /api/v1/me/activity?before=&limit=` | Mi actividad: los eventos de `activity_log` del usuario y las acciones de soporte sobre sus datos, del más reciente al más antiguo, paginados (`limit` hasta 50). Ver «Trazabilidad» | P0 |
| `POST /api/v1/me/tickets` · `GET /api/v1/me/tickets` | Reportar un problema (opcionalmente sobre un lote) y ver sus tickets | P1 |
| `GET /api/v1/lots/{lot_id}/seasons` · `POST /api/v1/lots/{lot_id}/seasons` | Historial del lote y nueva temporada | P0 |
| `PATCH /api/v1/seasons/{season_id}` | Registrar la cosecha o corregir una temporada | P0 |
| `GET /api/v1/lots/{lot_id}/progress` | Progreso derivado del historial | P0 |
| `GET /api/v1/lots/{lot_id}/growth` | Línea de tiempo del cultivo en curso, de la siembra a la cosecha estimada, para simular el paso del tiempo (ver «Cuerpos de cuenta») | P0 |

**Cómo viaja la credencial:** el usuario y la contraseña solo se envían una vez, en `/auth/register` y `/auth/login`, siempre por HTTPS. La API responde con un token de sesión aleatorio de 256 bits; en la base de datos se guarda solo su hash. De ahí en adelante cada petición lleva únicamente ese token, nunca la contraseña. El token viaja en una cookie `httpOnly` (el JavaScript de la página no lo puede leer), `Secure` (solo por HTTPS) y `SameSite=Lax`; además, la API rechaza las peticiones que cambian datos si su cabecera `Origin` no es la de la web (protección contra CSRF). Como la API y la web comparten origen, no hace falta CORS. Contraseña de al menos 8 caracteres. Tras 5 intentos fallidos de inicio de sesión en 15 minutos, responde 429; los intentos fallidos de cambiar la contraseña cuentan igual. Recuperar la contraseña queda en P1, porque no se guarda correo ni celular. Un usuario solo ve y modifica sus propios lotes: pedir uno ajeno responde 404.

### Roles (documentado; se implementa en HU-170)

Cada usuario tiene un `role`. Hoy solo existe `farmer`; los otros dos quedan definidos para no rehacer el esquema después.

| Rol | Valor | Quién es | Qué puede hacer | Dónde existe |
|---|---|---|---|---|
| Agricultor | `farmer` | El usuario final | Consultar, sus lotes, sus temporadas y su cuenta. **Nunca ve datos inventados**: solo el dataset publicado y lo que él registró (R5) | Producción y desarrollo. Es el rol por defecto al registrarse |
| Administrador web | `admin` | Quien opera la web y da soporte | Lo del agricultor, más: ver a los agricultores con sus lotes, temporadas y tickets; borrar y restaurar lotes y temporadas para resolver un ticket; crear, bloquear y desbloquear usuarios; ver métricas de uso agregadas y la bitácora. Toda acción queda en `activity_log` | Producción y desarrollo. Solo lo asigna otro administrador o la configuración inicial |
| Desarrollador | `developer` | El equipo, con la app en modo desarrollo | Lo del administrador, más: simulaciones con datos inventados (HU-014), crear datos de prueba y saltarse los topes y límites (intentos, ritmo, velocidad del recorrido) | **Solo en desarrollo** (`AGROSENSE_SIMULATION=true`). La API se niega a arrancar en producción si existe un usuario `developer` o si la simulación está activa |

Endpoints previstos (P1, sin implementar; requieren sesión y el rol indicado, si no `403`):

| Endpoint | Rol | Uso |
|---|---|---|
| `GET /api/v1/admin/users` | `admin` | Lista de usuarios: `user_id`, `username`, `display_name`, `role`, `created_at`, `blocked_at`, número de lotes y de tickets abiertos |
| `GET /api/v1/admin/users/{user_id}` | `admin` | Ficha de un agricultor: perfil, lotes (también los borrados hace menos de 30 días), temporadas y tickets. Se registra en `activity_log` como `admin.user_viewed` |
| `DELETE` y `POST …/restore` en `/api/v1/admin/lots/{lot_id}` y `/api/v1/admin/seasons/{season_id}` | `admin` | Borrar o restaurar un lote o una temporada de un agricultor. Exige `reason` y, si viene de un ticket, `ticket_id` |
| `GET /api/v1/admin/tickets` · `PATCH /api/v1/admin/tickets/{ticket_id}` | `admin` | Bandeja de tickets y cambio de estado |
| `POST /api/v1/admin/users` | `admin` | Crear un usuario con `username`, `display_name` y una contraseña temporal |
| `PATCH /api/v1/admin/users/{user_id}` | `admin` | Bloquear o desbloquear (`blocked`), y cambiar el rol entre `farmer` y `admin` |
| `GET /api/v1/admin/activity?user_id=&action=&outcome=&from=&to=&before=&limit=` | `admin` | Bitácora: eventos de `activity_log` con filtros, paginados. Consultarla también queda registrado (`admin.activity_viewed`) |
| `GET /api/v1/admin/metrics` | `admin` | Métricas agregadas: consultas por día, cuentas creadas, municipios y cultivos más consultados. Sin datos personales |
| `POST /api/v1/dev/fixtures` | `developer` | Cargar datos de prueba en la base de desarrollo |

- Un usuario bloqueado no puede iniciar sesión (`403` con `account_blocked`) y sus sesiones abiertas se cierran.
- En desarrollo, toda respuesta construida con datos simulados lleva `"simulated": true` en la raíz; la web muestra la franja «Modo simulación · datos de ejemplo» (HU-014, R5). En producción ese campo no existe.
- El administrador ve datos personales de los agricultores, así que el texto de consentimiento lo dice («el equipo de soporte puede ver sus lotes para resolver un problema») y sube a `consent_version` 2 (HU-163). El agricultor ve en «Mi actividad» (`GET /me/activity`) qué acciones de soporte se hicieron sobre sus datos.
- Por decidir: qué más hace el administrador, y si su panel va en esta web o en una aparte.

### Cómo se conectan cálculo y cuentas

- `/diagnostics`, `/rotations`, `/water-plans` y `/calendar` **no guardan nada**, con o sin cuenta. Con sesión, `/diagnostics` y `/rotations` aceptan `lot_id` solo para leer el polígono del lote y calcular su suelo; el resultado es el mismo que si se enviara ese suelo.
- Para las rotaciones de un lote, la web envía los cultivos de sus temporadas anteriores en `previous_crop_ids`. Sin cuenta, el usuario elige a mano el cultivo anterior.
- Para el plan de agua de una zona, la web arma `crops` con los lotes de ese municipio: `total_area_ha` es la suma de sus áreas y `area_pct` la parte de cada lote.

### Identificador de petición

Toda respuesta lleva la cabecera `X-Request-ID` (UUID). Si la petición trae una válida, se respeta; si no, la API la crea. Ese identificador aparece en cada línea de log de la terminal y en `activity_log.request_id`, y la web lo muestra en los errores («Código para soporte: …») para que un ticket se pueda rastrear.

### Errores

| Situación | Respuesta |
|---|---|
| Entrada inválida (municipio o cultivo fuera del catálogo, diagnóstico de un cultivo con `kind` distinto de `crop`, prioridades fuera de rango, porcentajes de finca que pasan de 100, registro sin consentimiento, temporada en curso duplicada, nombre vacío, contraseña nueva de menos de 8 caracteres o igual a la actual) | `422` |
| Endpoint de cuenta sin sesión válida, usuario y contraseña incorrectos, o `lot_id` en `/diagnostics` o `/rotations` sin sesión | `401` |
| Contraseña actual incorrecta al cambiarla | `403` (la sesión sigue abierta) |
| Rol sin permiso para el endpoint, o cuenta bloqueada al iniciar sesión | `403` |
| Nombre de usuario ya registrado, al crear la cuenta o al editar el perfil | `409` |
| Demasiados intentos de inicio de sesión | `429` |
| Lote o temporada que no existe o es de otro usuario | `404` |
| Entrada válida sin datos | `200` con `insufficient_data` en la señal |
| Fallo interno | `500` con `{"error": {"code": "...", "message": "...", "request_id": "..."}}` |

## Cuerpos y respuestas

Los ejemplos son ilustrativos, no son datos reales. Toda respuesta de cálculo trae `versions` con `dataset` y `rules` (R4).

### Cuerpo de `POST /api/v1/diagnostics`

```json
{ "municipality_id": "MUNICIPIO_ID", "crop_id": "papa", "year": 2026, "semester": "B", "lot_id": null }
```

`lot_id` es opcional y exige sesión: con él, la señal de suelo usa el suelo del lote en lugar del del municipio. Un lote ajeno responde 404. **No se guarda nada (R9).** La respuesta está en «Respuesta de diagnóstico», más abajo.

### Respuesta de `GET /api/v1/trends`

Dos series separadas, cada una con su unidad, para no mezclar unidades en un eje (W3):

- `climate`: por año y semestre, `precip_mm` y `precip_normal_mm` (mm). Es el nombre de la serie, no una señal: la señal se llama `rain`.
- `supply`: por año y semestre, `planted_ha` (ha) y `preliminary`.

Sin datos para una serie, la serie viene vacía con `status = insufficient_data`.

### Respuesta de `GET /api/v1/version`

`dataset_version`, `rules_version`, `created_at`, `region` y `sources` (lista con `source_id`, `name`, `institution`, `url` y `license`). Es lo que muestra el panel «¿Cómo funciona y de dónde sale esto?».

### Cuerpo de `POST /api/v1/rotations`

```json
{
  "municipality_id": "MUNICIPIO_ID",
  "year": 2027,
  "semester": "A",
  "previous_crop_ids": ["papa"],
  "priorities": { "water": 3, "soil": 5, "income": 2, "risk": 4 },
  "lot_id": null
}
```

`previous_crop_ids` lleva de 1 a 3 cultivos del catálogo (de cualquier `kind`), el más reciente primero. `lot_id` es opcional y exige sesión, igual que en el diagnóstico. Con el suelo (del lote o del municipio): un cultivo cuyo rango de pH tolerado queda fuera de **todo** el intervalo `ph_p05`–`ph_p95` se excluye por regla (R3); el carbono orgánico bajo bonifica abonos verdes, descanso y leguminosas en el criterio «suelo», con reglas de `rotation_rules` con fuente. Cada prioridad es un entero de 0 a 5; fuera de rango, o todas en 0, responde 422. La respuesta trae el ranking con el puntaje de 0 a 100 por criterio, el total ponderado, de 2 a 4 razones por opción, las opciones excluidas con la regla que las excluyó, y `versions`.

### Cuerpo de `POST /api/v1/water-plans`

```json
{
  "municipality_id": "MUNICIPIO_ID",
  "total_area_ha": 5.0,
  "crops": [
    { "crop_id": "papa", "area_pct": 60, "sowing_date": "2026-03-15" },
    { "crop_id": "arveja", "area_pct": 30, "sowing_date": "2026-04-01" }
  ]
}
```

La suma de `area_pct` no puede pasar de 100. Lo que falta es terreno en descanso o sin sembrar. Con cuenta, solo entran los lotes con una temporada en curso. La respuesta trae, por cultivo y por finca, el déficit mensual y el volumen en m³ para año normal y año seco, con rangos y el rótulo de estimación (R10). **Este endpoint no guarda nada (R9)**, aunque el usuario tenga cuenta.

### Cuerpo y respuesta de `POST /api/v1/calendar`

```json
{ "municipality_id": "MUNICIPIO_ID", "crop_id": "papa" }
```

Responde 12 meses. Cada mes trae `month` y estos bloques, con `status`, `level` y `reasons` como las señales (R1):

- `sowing`: qué tan bueno es sembrar ese mes. Se evalúa si la lluvia normal cubre la etapa inicial del cultivo (balance de M7) y el riesgo de helada en sus etapas sensibles. `unfavorable` si el mes no está en `sowing_semesters`.
- `frost`: `frost_freq_pct` del mes y nivel según `thresholds.yaml`.
- P1: `fertilizing` (días de aguacero), `field_work` (ventanas secas para labores y cosecha) y `blight` (días favorables a la gota, solo para cultivos con esa regla).

Más `best_sowing_months` (de 1 a 3 meses) y `versions`. No guarda nada (R9). El diagnóstico usa este mismo cálculo para la señal `frost`. La vista del lote lo combina con el plan de agua: el calendario no repite el riego.

### Cuerpos de cuenta

- `PATCH /api/v1/me`: `display_name` (1 a 40 caracteres) y `username` (3 a 30 caracteres: letras minúsculas sin tilde, números, punto y guion bajo), ambos opcionales. Cambiar el usuario no cierra la sesión. El consentimiento no se edita aquí: para retirarlo se borra la cuenta.
- `POST /api/v1/me/password`: `current_password` y `new_password` (al menos 8 caracteres y distinta de la actual). Responde `204`.
- `POST /api/v1/lots` y `PATCH /api/v1/lots/{lot_id}`: `name`, `municipality_id` y `geometry` (polígono GeoJSON). Sin `geometry`, `area_ha` (mayor que cero) es obligatoria; con `geometry`, `area_ha` la calcula la API y se ignora la enviada.
- Respuesta de `GET /api/v1/lots/{lot_id}`: el lote, `soil` (las propiedades de `soil_grid` como mediana del polígono, con `basis`: `lot` o `municipality`, y `cells`) y `current_season` (nula si no hay temporada en curso) con `crop_id`, `sowing_date`, `days_since_sowing`, `stage`, `stage_progress_pct`, `stage_method` (`thermal_time` si se usó la temperatura acumulada del municipio, `calendar` si se usó la duración por días porque faltan datos de temperatura o grados-día con fuente), `thermal_data_until` (fecha del último dato de temperatura usado; nula con `calendar`) y `versions`. Es una estimación con el clima del municipio, no una observación del lote (HU-150).
- Respuesta de `GET /api/v1/lots/{lot_id}/growth`: `points` (uno por semana, de la siembra a la cosecha estimada) con `date`, `stage`, `stage_progress_pct`, `gdd_accumulated` y `basis`: `observed` mientras hay temperatura real (`climate_day`, hasta `thermal_data_until`) y `normal_year` después (`climate_normal_doy`). Más `today`, `harvest_estimate` (fecha, siempre con `basis`) y `versions`. Lo `normal_year` es una estimación con un año normal, **no un pronóstico**: la web lo rotula así. Sin temperatura con fuente o sin grados-día del cultivo, se usa la duración por calendario y se dice (R1). No guarda nada.
- `POST /api/v1/lots/{lot_id}/seasons`: `crop_id`, `sowing_date` y el diagnóstico que vio el usuario al sembrar (`diagnosis_light`, `diagnosis_action`, `dataset_version`, `rules_version`), que la web toma de la respuesta de `/diagnostics`. Si no consultó el diagnóstico, esos campos van nulos.
- `PATCH /api/v1/seasons/{season_id}`: `harvest_date` o correcciones de `crop_id` y `sowing_date`.
- Respuesta de `GET /api/v1/lots/{lot_id}/progress`: `seasons_count`, `valid_rotations_count` y `milestones` (cada uno con `milestone_id`, `achieved_at` y `basis`: la regla de `rotation_rules` o el hecho registrado que lo produce), más `versions`.

### Respuesta de diagnóstico

```json
{
  "request": {
    "municipality_id": "MUNICIPIO_ID",
    "crop_id": "papa",
    "year": 2026,
    "semester": "B"
  },
  "overall": {
    "light": "yellow",
    "action": "wait_other_semester",
    "reasons": ["Una señal desfavorable no crítica con lluvia favorable: esperar otro semestre"]
  },
  "signals": {
    "rain": {
      "status": "available",
      "level": "favorable",
      "critical": false,
      "indicators": ["precip_anomaly_pct"],
      "reasons": ["Lluvia del semestre dentro del rango favorable"]
    },
    "frost": {
      "status": "available",
      "level": "moderate",
      "critical": false,
      "indicators": ["frost_freq_pct"],
      "reasons": ["Sembrando en agosto, hubo heladas en la floración 2 de cada 10 años"]
    },
    "soil": {
      "status": "available",
      "level": "favorable",
      "critical": false,
      "indicators": ["ph"],
      "reasons": ["pH estimado de 5,2 a 5,8, dentro del rango de la papa. Estimación de 250 m: confírmelo con un análisis de suelo"]
    },
    "supply": {
      "status": "available",
      "level": "unfavorable",
      "critical": false,
      "indicators": ["planted_change_pct"],
      "reasons": ["Área sembrada mayor que el promedio de los tres semestres B anteriores"]
    },
    "market": {
      "status": "insufficient_data",
      "level": null,
      "critical": false,
      "indicators": [],
      "reasons": ["Sin datos de mercado para la zona"]
    }
  },
  "limitations": ["Datos EVA del último año son preliminares", "Suelo estimado para el municipio, no para su lote"],
  "versions": { "dataset": "2026.11.0", "rules": "1.0.0" }
}
```

## Valores permitidos y semáforo

Ver `specs/01-reglas.md` (valores permitidos y agregación inicial del semáforo).
