# Contratos de datos y de API

Los identificadores del código van en inglés y en `snake_case` para evitar tildes; los textos de la interfaz van en español. En lugar de una tabla larga de indicadores, se usan pocas tablas por granularidad: así cada fila tiene una llave clara y cada columna una unidad fija.

> **Estado:** propuesta congelable. Se congela en HU-011 y HU-012. **Responsables: Haider y Felipe.** Después de congelado, cualquier cambio lo hace o lo aprueba uno de los dos, porque rompe el trabajo en paralelo.

> **Cambios del 11 de octubre de 2026 (decisión 12, MVP):** tablas de los productos NASA (`precip_month`, `soil_moisture_month`, `elevation_grid`, `ndvi_municipality`, `ndvi_municipality_normal`, `ndvi_grid`, `climate_change_month`), humedad del suelo en `climate_month`, `/rotations` con estrategias de hasta 3 ciclos y `soil_health`, y `GET /api/v1/changes`. Las decisiones son de Felipe; los nombres de las tablas y de los campos nuevos son una propuesta del especificador y **quedan pendientes de que Felipe o Haider los revisen antes de congelar**. Hay que avisarle a Haider.

## Tablas publicadas (Parquet)

| Tabla | Llave primaria | Columnas principales | Origen |
|---|---|---|---|
| `municipalities` | `municipality_id` (DIVIPOLA, 5 dígitos) | `name`, `department_id`, `department`, `lat`, `lon`, `altitude_m` (de NASADEM, HU-206), `climate_cell_elevation_m` (altura de la celda de NASA POWER que lo cubre), `source_ids` | DANE, NASADEM y NASA POWER |
| `crops` | `crop_id` | `name_es`, `kind` (`crop`, `cover` para abono verde o cobertura, `fallow` para descanso), `archetype` (cómo se dibuja: `tuber`, `root`, `bulb`, `leafy`, `cereal`, `climbing_legume`, `bush_legume`, `creeping`, `tall_grass`, `shrub_fruit`, `tree_fruit`), `family`, `cycle_months`, `water_need`, `root_type`, `fixes_nitrogen`, `altitude_min_m`, `altitude_max_m` (rango en que se da; fuera de él no es apto para la zona), `base_temp_c`, `heat_max_c` (temperatura máxima que aguanta), los límites de sus curvas de calificación (`temp_min_c`, `temp_opt_min_c`, `temp_opt_max_c`; `altitude_opt_min_m`, `altitude_opt_max_m`, el rango óptimo de altitud, que da la nota informativa de aptitud; y `rain_min_mm`, `rain_opt_min_mm`, `rain_opt_max_mm`, `rain_max_mm`, la lluvia anual que pide el cultivo, de referencia y contraste: la curva de `water` usa `thresholds.yaml`), `ph_min`, `ph_max` (rango que tolera), `ph_opt_min`, `ph_opt_max` (rango óptimo) — nulos si no hay fuente —, `source_ids` | Catálogo |
| `rotation_rules` | `rule_id` | `kind` (`filter`, `bonus`, `penalty`), `condition`, `effect`, `criterion`, `source_id` | Catálogo |
| `climate_risk_week` (P1, HU-193) | `municipality_id`, `week` (1 a 52; los días 365 y 366 van a la semana 52) | Los indicadores de `climate_risk_month` y las normales de `climate_month`, por semana del año y suavizados con las semanas vecinas: `frost_freq_pct`, `tmax_p90_c`, `precip_normal_mm`, `precip_dry_mm`, `et0_normal_mm` y, en P1, `heavy_rain_days_mean`, `dry_window_freq_pct` y `blight_days_mean`; más `years`, `quality`, `source_id` | NASA (para comparar ventanas por semana) |
| `climate_day` | `municipality_id`, `date` | `temp_min_c`, `temp_max_c`, `quality`, `source_id` | NASA POWER (de aquí salen las heladas, el calor y «Qué cambió»; en P1, la etapa del cultivo, HU-150) |
| `climate_normal_doy` (P1, HU-186) | `municipality_id`, `doy` (1 a 366) | `temp_min_c`, `temp_max_c` normales de ese día del año (promedio 1991–2020, suavizado), `source_id` | NASA (para estimar el crecimiento después de hoy, HU-186) |
| `climate_risk_month` | `municipality_id`, `month` (1 a 12) | `frost_freq_pct` (porcentaje de años con al menos un día de mínima menor que 2 °C en ese mes), `frost_days_mean`, `tmax_p90_c` (temperatura máxima que se supera uno de cada diez días de ese mes; para la señal de calor), `heavy_rain_days_mean` (P1), `dry_window_freq_pct` (P1, años con 3 días seguidos de menos de 5 mm), `blight_days_mean` (P1, días favorables a la gota), `years`, `quality`, `source_id` | NASA (HU-045) |
| `climate_month` | `municipality_id`, `year`, `month` | `precip_mm`, `precip_normal_mm`, `precip_dry_mm` (año seco), `et0_mm`, `et0_normal_mm` (ET0 por Penman-Monteith, FAO-56), `soil_wetness_top`, `soil_wetness_root` (humedad del suelo modelada, superficial y de raíces, fracción de 0 a 1), `quality`, `source_id` | NASA POWER (reanálisis; HU-042, HU-143, HU-205) |
| `precip_month` | `municipality_id`, `year`, `month`, `source_id` | `precip_mm` (promedio de las celdas que tocan el municipio), `precip_normal_mm`, `precip_dry_mm`, `normal_period` (los años de la normal), `quality` | GPM IMERG, lluvia por satélite de unos 10 km (HU-207). La lluvia de NASA POWER sigue en `climate_month` |
| `soil_moisture_month` | `municipality_id`, `year`, `month`, `source_id` | `sm_surface_m3_m3`, `sm_rootzone_m3_m3` (humedad superficial y de raíces, en m³/m³), `quality` | SMAP nivel 4, 9 km, desde 2015 (HU-210). Solo para contrastar; unidad distinta de la de POWER |
| `elevation_grid` | `cell_id` | `lon`, `lat`, `altitude_m`, `source_id`; resolución por confirmar en HU-206 (30 m o remuestreada) | NASADEM (HU-206); para la altitud de un lote |
| `ndvi_municipality` | `municipality_id`, `year`, `period` (1 a 23: el compuesto de 16 días del año) | `ndvi_median`, `valid_pixels_pct` (píxeles sin nubes), `quality`, `source_id` | MODIS MOD13Q1, 250 m (HU-208) |
| `ndvi_municipality_normal` | `municipality_id`, `period` (1 a 23) | `ndvi_normal`, `years`, `quality`, `source_id` | MODIS MOD13Q1 (HU-208) |
| `ndvi_grid` | `cell_id`, `period` (1 a 23) | `lon`, `lat`, `ndvi_normal`, `years`, `valid_pct`, `quality`, `source_id`; celdas de 250 m de la región | MODIS MOD13Q1 (HU-209); para el verdor de un lote |
| `climate_change_month` | `municipality_id`, `period_id`, `month` (1 a 12), `source_id` | `frost_freq_pct`, `tmax_p90_c` (nulos en las filas de una fuente de lluvia), `precip_normal_mm`, `years`, `quality` | NASA POWER y GPM IMERG (HU-216); para «Qué cambió» |
| `crop_stages` | `crop_id`, `stage` | `days`, `kc`, `gdd` (grados-día que cierran la etapa; nulo si no hay fuente), `frost_sensitive` (la helada daña en esta etapa), `heat_sensitive` (el calor por encima de `heat_max_c` daña en esta etapa), `source_id` | Catálogo (FAO-56 o fuente local) |
| `supply_semester` | `municipality_id`, `crop_id`, `year`, `semester`, `source_id` | `planted_ha`, `harvested_ha`, `production_t`, `yield_t_ha`, `planted_change_pct`, `dept_share_pct`, `preliminary`, `quality` | EVA |
| `market_month` (P1) | `crop_id`, `market_id`, `month` | `price_cop_kg`, `volume_t`, `seasonal_index`, `quality`, `source_id` | SIPSA |
| `market_price_day` (HU-221; agregada el 20 de octubre de 2026, **por aprobar**) | `product_id`, `market_id`, `date` | `product` (nombre del DANE sin asterisco), `group`, `several_varieties` (el asterisco de SIPSA: junta variedades), `market`, `municipality_id` (de la central), `min_cop_kg` y `max_cop_kg` (nulos si el DANE no los da), `avg_cop_kg`, `source_id`. Solo las centrales de `region.yaml` | SIPSA (servicio web del DANE) |
| `market_price_season` (HU-221; **por aprobar**) | `product_id`, `market_id`, `month` | `seasonal_index` (precio del mes sobre el promedio de su mismo año, promediado entre años; 1 = un mes como cualquiera), `years`, `first_year`, `last_year`, `source_id`. Solo productos con 3 o más años completos | SIPSA |
| `municipality_boundaries` | `municipality_id` | `geometry` (polígono WGS84 simplificado), `source_id` | DANE (Marco Geoestadístico Nacional) |
| `soil_grid` | `cell_id` | `lon`, `lat`, `ph`, `ph_p05`, `ph_p95`, `soc_g_kg` (carbono orgánico), `nitrogen_g_kg`, `clay_pct`, `sand_pct`, `silt_pct`, `texture_class`; promedio ponderado de 0 a 30 cm de cada celda de 250 m de la región; `source_id` | SoilGrids de ISRIC (HU-181) |
| `soil_municipality` | `municipality_id` | Las mismas propiedades que `soil_grid`, como mediana de las celdas dentro del municipio, más `cells`, `quality` y `source_id` | SoilGrids (HU-181) |
| `sources` | `source_id` | `name`, `institution`, `url`, `downloaded_at`, `period_covered`, `coverage` (país o región que cubre), `license`, `notes` | Todas. Un indicador puede tener varias fuentes; `sources.yaml` dice cuál usa cada señal en cada región y las demás se muestran para contrastar |
| `manifest.json` | — | `dataset_version`, `rules_version`, `created_at`, `region`, `periods` (los periodos de «Qué cambió»: `period_id`, `start_year`, `end_year`, `source_id`), filas y cobertura por tabla | Pipeline |

### Decisiones sobre el clima publicado

- Todas las temperaturas publicadas (`climate_day`, `climate_month`, `climate_risk_month` y `climate_risk_week`) se corrigen por altitud: la celda de NASA POWER tiene unos 50 km y su altura puede diferir cientos de metros de la del municipio. La corrección usa la diferencia entre `altitude_m` y `climate_cell_elevation_m` con un gradiente térmico con fuente (HU-044). Así la etapa del cultivo, la ET0 y las heladas usan la misma temperatura.
- El umbral de helada es una mínima menor que 2 °C a 2 m, el criterio de amenaza que usa la UPRA con datos del IDEAM.
- NASA POWER es un **reanálisis** (un modelo con observaciones asimiladas), no una observación directa; su entrada en `sources` lo dice. Es la serie larga (desde 1981).
- La lluvia tiene dos fuentes: NASA POWER (`climate_month`) y GPM IMERG (`precip_month`). `sources.yaml` dice cuál calcula la señal `water` en cada región; la otra se muestra para contrastar. Nunca se promedian ni una rellena a la otra.
- La humedad del suelo tiene dos fuentes con unidades distintas: la de POWER (`soil_wetness_*`, fracción de 0 a 1) y la de SMAP (`sm_*_m3_m3`). No se convierten una en otra.
- El suelo, la altitud y el verdor de un lote **no se guardan**: la API los calcula al vuelo como la mediana de las celdas de `soil_grid`, `elevation_grid` y `ndvi_grid` que toca su polígono.
- En el MVP las señales de heladas y calor leen `climate_risk_month`; `climate_risk_week` llega en P1.

### Supuestos por confirmar en la fase 0

- Que EVA trae código DIVIPOLA (HU-001).
- Que, en EVA, el semestre A va de enero a junio y el B de julio a diciembre. La metodología EVA define periodos de recolección que hay que mapear con cuidado. El semestre solo existe en `supply_semester`: la decisión se toma sobre ventanas de siembra (ver `specs/01-reglas.md`) y la oferta se lee del semestre en que cae la fecha de siembra.
- `planted_change_pct` compara contra el promedio de los tres mismos semestres anteriores.
- `quality` toma valores como `ok` o `partial` (por ejemplo, cuando faltan semestres previos o hay pocos días válidos). La lista exacta se fija en HU-011.

## Base de datos de cuentas (PostgreSQL)

Decisión 6 de `docs/decisiones.md` y regla R9. PostgreSQL propio en Docker, aparte del dataset publicado. El motor no la lee: la API consulta los lotes y le pasa al motor solo lo que necesita.

| Tabla | Llave primaria | Columnas principales | Notas |
|---|---|---|---|
| `users` | `user_id` (UUID) | `username` (único), `password_hash`, `display_name`, `role` (`farmer` por defecto; ver «Roles»), `blocked_at` (nulo si no está bloqueado), `consent_version`, `consent_at`, `priorities` (los pesos de 0 a 5 por señal que el agricultor eligió; nulo = los de AgroSense), `created_at`, `updated_at` | Sin correo, celular, documento de identidad ni dirección. La contraseña se guarda solo como hash Argon2 |
| `sessions` | `session_id` (UUID) | `user_id`, `token_hash`, `created_at`, `expires_at` | Una fila por sesión abierta. Se guarda el hash del token, nunca el token. Vence a los 30 días |
| `lots` | `lot_id` (UUID) | `user_id`, `municipality_id`, `name`, `geometry` (polígono GeoJSON en WGS84, dibujado en el mapa; nulo si el usuario aún no lo dibuja), `area_ha`, `irrigated` (si el lote tiene riego; nulo si no lo ha dicho), `deleted_at`, `created_at`, `updated_at` | Un usuario tiene uno o varios lotes; la «zona» es el municipio (R7). Con polígono, `area_ha` se calcula de él y el polígono debe caer dentro de su municipio |
| `seasons` | `season_id` (UUID) | `lot_id`, `crop_id`, `area_ha` (la parte del lote que ocupa), `follows_season_ids` (lista de las temporadas que había antes en ese terreno; vacía si es la primera), `diagnosis_irrigated` (el `irrigated` con que se vio el diagnóstico), `diagnosis_light_default` (la luz con los pesos de AgroSense), `diagnosis_weights` (los pesos con que se vio; `diagnosis_light` es la luz con esos pesos), `sowing_date`, `harvest_date` (nula si sigue en curso), `diagnosis_light`, `diagnosis_action`, `dataset_version`, `rules_version`, `deleted_at`, `created_at` | Una temporada por cultivo y ciclo en una parte del lote. Un lote grande puede tener varios cultivos a la vez, cada uno en su parte. Guarda el diagnóstico que se vio al sembrar, con sus versiones (R4) |

- Borrar un usuario borra en cascada, y para siempre, sus sesiones, lotes, temporadas, tickets y sus eventos de `activity_log` (R9).
- Borrar un lote o una temporada es reversible: se marca `deleted_at` y se puede restaurar durante 30 días; después se borra para siempre. Borrar un lote borra con él sus temporadas, y restaurarlo las restaura. El agricultor y el administrador pueden restaurar.
- Un polígono de lote debe ser válido (sin cruces), tener área mayor que cero y caer dentro de `municipality_boundaries` de su municipio; si no, 422.
- `activity_log`: trazabilidad de lo que hacen agricultores y administradores. Ver «Trazabilidad» más abajo.
- `login_attempts` (agregada el 12 de octubre de 2026; aprobada por Felipe): `attempt_id`, `username_hash` y `attempted_at`. Una fila por intento fallido de entrar, de cambiar la contraseña o de borrar la cuenta, solo para el **tope general** de 20 intentos en 15 minutos por usuario desde cualquier conexión (cambiado el 15 de octubre de 2026; aprobado por Felipe: antes era el único tope, de 5). El tope de 5 por conexión vive en memoria (ver «Cómo viaja la credencial»). Guarda el hash del usuario que se intentó, nunca el texto (podría ser una contraseña escrita en el campo equivocado), ni la IP. Las filas de más de 15 minutos se borran solas. La fila se anota **antes** de verificar la contraseña y se quita si era la buena, para que varias peticiones a la vez no se salten el tope; un intento rechazado con 429 no se anota, así que no alarga el bloqueo. Está en la base de datos para que el tope sobreviva a un reinicio.
- `usage_daily` (P1, HU-170): contador anónimo de uso para las métricas. En el P0 la tabla no existe y los endpoints de cálculo no escriben nada en la base de datos. Columnas: `day` (fecha), `endpoint` (`diagnostics`, `rotations`, `changes`, `calendar`, `water_plans`, `scenarios`), `municipality_id`, `crop_id` y `count`; llave (`day`, `endpoint`, `municipality_id`, `crop_id`). Cada consulta de cálculo suma 1 a su fila. El `crop_id` que se cuenta: en `/diagnostics`, `/changes`, `/calendar` y `/scenarios`, el cultivo consultado; en `/water-plans`, una fila por cultivo; en `/rotations`, el primer cultivo de `previous_crop_ids` (el más reciente). No tiene usuario, sesión, IP, hora, fecha de siembra, prioridades, área ni riego, ni se puede unir con `activity_log`. Se conserva como estadística. No cambia ningún resultado (R4). Si falla, la consulta responde igual.
- El suelo de un lote **no se guarda**: la API lo calcula al vuelo como la mediana de las celdas de `soil_grid` que toca su polígono. Un lote sin polígono usa `soil_municipality`.
- `support_tickets` (P1): `ticket_id`, `user_id`, `lot_id` (opcional), `message`, `status` (`open`, `in_progress`, `closed`), `created_at`, `closed_at`.
- `crop_id` y `municipality_id` deben existir en el catálogo publicado; si no, 422.
- Un lote puede tener varias temporadas en curso a la vez, cada una en una parte del lote. Las partes son de área, no de forma: no se dibujan. La suma de `area_ha` de las temporadas en curso no puede pasar del `area_ha` del lote; si pasa, 422. Vale también al editar el lote: un `PATCH` que lo deja más chico que lo que ocupan sus temporadas en curso responde 422. Sin `area_ha`, la temporada ocupa todo lo que queda libre.
- El agricultor divide su lote como quiera: puede sembrar hoy la mitad y otra parte en un mes, y al cosechar puede repartir ese terreno entre varios cultivos o juntar varias partes en una. Por eso una temporada puede venir de varias (`follows_season_ids`) y tener varias sucesoras.
- Cada temporada de `follows_season_ids` es una temporada cosechada del mismo lote, con `harvest_date` igual o anterior a `sowing_date`. El área de una temporada no puede pasar de la suma de las áreas de las que viene más el área libre del lote. La suma de las temporadas en curso nunca pasa del área del lote, y eso basta para que un terreno no se reparta dos veces. Así se puede dividir un terreno en varios y juntar varios en uno. Si algo no se cumple, 422.
- Esas relaciones son el historial de cada terreno: para las rotaciones y el progreso, los cultivos anteriores de una temporada son los de todas las temporadas de las que viene.
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
- Un bloqueo por demasiados intentos (429) deja **un** evento `denied` por ventana de 15 minutos, no uno por petición; con un usuario que no existe, ninguno (14 de octubre de 2026, revisión de seguridad; aprobado por Felipe).
- **Solo se agrega.** El usuario de base de datos de la API tiene `INSERT` y `SELECT` sobre `activity_log`, no `UPDATE` ni `DELETE`; solo la tarea de limpieza y el borrado de cuenta usan otro rol.
- Se conserva **180 días** y luego se borra. La limpieza corre al arrancar la API y en cada inicio de sesión correcto.
- **Los endpoints de cálculo no escriben aquí** (R9): consultar un diagnóstico, una rotación o un plan de agua no deja ningún evento. Desde HU-170 (P1) solo suma 1 al contador anónimo `usage_daily`, que no dice quién consultó.
- **Al borrar la cuenta** se borran los eventos del agricultor. Las acciones de administradores sobre sus datos se conservan, pero con `subject_user_id`, `object_id` y `reason` en nulo, para no perder quién hizo qué sin guardar de quién era.
- Lo dice el consentimiento desde la versión 2 (vigente: 3, HU-163): «registramos lo que hace con su cuenta durante 180 días para su seguridad».

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

`next_before` es nulo cuando no hay más páginas. Varios eventos pueden tener la misma hora (los de una misma petición): si el corte de una página cae entre ellos, la página se alarga hasta incluirlos a todos, así que puede traer algunos más que `limit` (14 de octubre de 2026; aprobado por Felipe: antes se perdían). Al agricultor nunca se le muestra quién es el administrador, solo `actor_role`.

### Logs de la terminal (HU-177)

No son parte de la API ni se consultan desde la web; se documentan aquí porque fijan qué se puede escribir y qué no. Los escribe `structlog` a la salida estándar: con color en desarrollo y una línea JSON por evento en producción. En la consola cada parte tiene su color: el nivel (gris `debug`, verde `info`, amarillo `warning`, rojo `error`), el mensaje (blanco), el código de la respuesta (verde, amarillo o rojo), el endpoint (azul claro) y lo demás atenuado.

```json
{"ts": "2026-11-14T15:02:11.204Z", "level": "info", "event": "request", "request_id": "9b1e…", "method": "POST", "route": "/api/v1/lots/{lot_id}/restore", "status": 200, "duration_ms": 18, "user_id": "3c7a…", "role": "farmer", "dataset": "2026.11.1", "rules": "1.4.0"}
```

| Campo | Siempre | Notas |
|---|---|---|
| `ts`, `level`, `event`, `request_id` | Sí | `level`: `debug` (solo desarrollo), `info`, `warning` (todo lo rechazado, de `400` a `499`, y `503`), `error` (`500`, con la traza del error). Cambiado el 12 de octubre de 2026: antes solo `403` y `429` eran `warning` |
| `detail` | Sí | Qué pasó, en español y en palabras: «Inicio de sesión rechazado: usuario no registrado», «Perfil actualizado: display_name». Puede decir más que la respuesta (por ejemplo, si falló el usuario o la contraseña), porque solo se ve en la terminal del servidor. Nunca repite lo que escribió la persona |
| `endpoint` | En peticiones que llegan a una ruta | La función que atendió, como `auth.login`. Solo en el log: la respuesta no lo lleva |
| `method`, `route`, `status`, `duration_ms` | En peticiones | `route` es la plantilla de la ruta, no la URL con sus parámetros de consulta. Una dirección que no existe en la API se escribe `[sin ruta]`: nunca lo que llegó |
| `user_id`, `role` | Si hay sesión | Nunca el `username` ni el nombre |
| `dataset`, `rules` | En endpoints de cálculo | Versiones usadas (R4) |

Cuando las cuentas están apagadas, cada intento de usarlas deja un evento `accounts_unavailable` de nivel `warning` con `reason` (`database_down` o `migration_pending`), `current_migration`, `expected_migration` y `detail` («Cuentas no disponibles (503) porque la migración 2.1 no se completó; la base de datos está en la 1.9»). Al arrancar, la API registra `migration_applied`, `migration_up_to_date`, `migration_skipped` (la base no responde) o `migration_failed` (nivel `error`, con las dos versiones y la traza).

`GET /api/v1/health` responde siempre `200` mientras la API esté arriba, con `accounts`: `available`, `reason` (`ok`, `database_down` o `migration_pending`), `current_migration` y `expected_migration`.

Nunca se escriben: contraseñas, tokens, cookies, la cabecera `Authorization`, polígonos ni los cuerpos de los endpoints de cálculo (R9). Un procesador de redacción borra esas llaves de cualquier evento. Otro escribe los caracteres de control de cualquier texto como `\x1b`, para que lo que llega de afuera no parta una línea ni cambie lo que muestra la terminal. Las trazas de errores de base de datos no llevan los valores de la consulta.

## Endpoints

| Endpoint | Uso | Prioridad |
|---|---|---|
| `GET /api/v1/catalogs/municipalities` | Municipios habilitados de la región: una lista de `municipality_id`, `name`, `department`, `lat`, `lon`, por departamento y nombre. Sin dataset publicado, `503` `dataset_unavailable` | P0 |
| `GET /api/v1/market/prices?market_id=` (HU-221, **por aprobar**) | El último precio de cada producto en la central (por defecto, la primera de la región), con `week_ago` (el último precio hasta 7 días antes) y `change_pct`, ambos nulos si no hay con qué comparar; `markets`, `date` y `source_id`. Sin precios publicados, `503` `market_unavailable`; una central que no está, `404` `unknown_market` | P1 |
| `GET /api/v1/market/prices/{product_id}?market_id=` (HU-221, **por aprobar**) | Los precios del último año del producto en la central (`days`) y su temporada (`season`, nula sin años completos suficientes). Un producto sin precios en esa central, `404` `unknown_product` | P1 |
| `GET /api/v1/catalogs/crops` | Cultivos habilitados: `crop_id`, `name_es`, `kind`, `archetype` (cómo se dibuja, HU-187), `family`, `cycle_months`. El diagnóstico solo acepta `kind = crop`; las rotaciones aceptan los tres | P0 |
| `GET /api/v1/catalogs/municipalities/{municipality_id}/soil` | Suelo estimado del municipio (`soil_municipality`) con su incertidumbre y `source_id` | P0 |
| `GET /api/v1/trends?municipality_id=&crop_id=&sowing_date=` | Series para las gráficas: agua, área sembrada y verdor (ver «Cuerpos y respuestas») | P0 |
| `POST /api/v1/diagnostics` | Diagnóstico de una ventana de siembra | P0 |
| `POST /api/v1/rotations` | Estrategias de rotación de hasta 3 ciclos, ordenadas según las prioridades, con la salud del suelo y el diagnóstico de cada ciclo | P0 |
| `POST /api/v1/water-plans` | Plan de agua de una finca o de un ciclo de una estrategia | P0 |
| `GET /api/v1/changes?municipality_id=&crop_id=&irrigated=` | «Qué cambió»: el clima de dos periodos y cómo se movieron las mejores ventanas del cultivo (ver «Cuerpos y respuestas») | P0 |
| `POST /api/v1/calendar` | **Pasó a P1 el 11 de octubre de 2026 (HU-179).** Calendario de un cultivo en un municipio. Sin `sowing_date`: las ventanas de siembra de los próximos doce meses, ordenadas primero por el factor que más limita y después por las prioridades, con sus señales; con `month`, las semanas de ese mes. Con `sowing_date`: mes a mes, la etapa del cultivo ya sembrado y cuándo vigilar heladas y calor; también aguaceros (cuándo abonar), ventanas secas (labores y cosecha) y gota (ver «Cuerpos y respuestas») | P1 |
| `GET /api/v1/version` | Versiones del dataset y de las reglas, región y fuentes (HU-122) | P0 |
| `POST /api/v1/scenarios` | Escenario hipotético y diferencias con el caso base | P1 |

Condiciones actuales (decisión 7):

| Endpoint | Uso | Prioridad |
|---|---|---|
| `GET /api/v1/conditions?municipality_id=` | Condición aproximada actual del municipio para la escena, de Open-Meteo: `status`, `precipitation_mm`, `cloud_cover_pct`, `wind_speed_kmh`, `wind_direction_deg`, `temp_c`, `observed_at`, `source_id`. Caché de 15 minutos. Solo el «ahora», sin pronóstico | P1 (HU-175, desde el 11 de octubre de 2026) |

`status` usa los valores de `specs/01-reglas.md`: `available` o `insufficient_data`. Sin datos del proveedor responde `200` con `status = insufficient_data` y valores nulos. Nunca entra al motor. La noche y el día los calcula la web con `lat` y `lon` del catálogo.

Endpoints de cuenta (requieren sesión, salvo `register` y `login`):

| Endpoint | Uso | Prioridad |
|---|---|---|
| `POST /api/v1/auth/register` | Crear cuenta: `username`, `password`, `display_name`, `consent_version` y `consent_accepted`. Sin `consent_accepted = true`, responde 422 | P0 |
| `POST /api/v1/auth/login` | Iniciar sesión con `username` y `password`; deja la cookie de sesión | P0 |
| `POST /api/v1/auth/logout` | Cerrar la sesión actual | P0 |
| `GET /api/v1/me` | Perfil y consentimiento del usuario | P0 |
| `PATCH /api/v1/me` | Editar el perfil: `display_name`, `username` y `priorities` (sus pesos por señal; nulo vuelve a los de AgroSense). Responde el perfil actualizado | P1 (HU-160) |
| `POST /api/v1/me/password` | Cambiar la contraseña con `current_password` y `new_password`. Cierra las demás sesiones del usuario; la actual sigue abierta | P1 (HU-160) |
| `DELETE /api/v1/me` | Borrar la cuenta con sus sesiones, lotes, temporadas, tickets y sus eventos de `activity_log` (las acciones de administradores sobre sus datos quedan anonimizadas). Pide la contraseña en el cuerpo: `{"password": "..."}` (15 de octubre de 2026; aprobado por Felipe). Sin ella, `422`; si no coincide, `403` `wrong_password`, la sesión sigue y cuenta para los topes de intentos | P0 |
| `GET /api/v1/lots` · `POST /api/v1/lots` | Listar y crear lotes. Cada lote de la lista trae `current_crop_ids`: los cultivos en curso, de mayor a menor área, para la fila de Mi finca (agregado el 15 de octubre de 2026; aprobado por Felipe). Con HU-204 (P1), la lista incluye los lotes borrados hace menos de 30 días, con `deleted_at` y `restorable_until` | P0 |
| `GET`, `PATCH`, `DELETE /api/v1/lots/{lot_id}` | Ver, editar y borrar un lote. `GET` trae las temporadas en curso, cada una con su parte del área y su etapa estimada (ver «Cuerpos de cuenta»). `DELETE` es reversible durante 30 días | P0 |
| `POST /api/v1/lots/{lot_id}/restore` | Restaurar un lote borrado hace menos de 30 días. Restaura también las temporadas que se borraron con él. Pasados los 30 días, o si no está borrado, 404 | P1 (HU-204) |
| `GET /api/v1/catalogs/municipalities/{municipality_id}/boundary` | Límite del municipio en GeoJSON, para centrar el mapa y validar el dibujo en la web | P0 |
| `GET /api/v1/me/activity?before=&limit=` | Mi actividad: los eventos de `activity_log` del usuario y las acciones de soporte sobre sus datos, del más reciente al más antiguo, paginados (`limit` hasta 50). Ver «Trazabilidad» | P1 (HU-178) |
| `POST /api/v1/me/tickets` · `GET /api/v1/me/tickets` | Reportar un problema (opcionalmente sobre un lote) y ver sus tickets | P1 |
| `GET /api/v1/lots/{lot_id}/seasons` · `POST /api/v1/lots/{lot_id}/seasons` | Historial del lote y nueva temporada. Con HU-204 (P1), el historial incluye las temporadas borradas hace menos de 30 días, con `deleted_at` y `restorable_until`, para poder restaurarlas | P0 |
| `PATCH`, `DELETE /api/v1/seasons/{season_id}` | Registrar la cosecha, corregir o borrar una temporada. `DELETE` es reversible durante 30 días | P0 |
| `POST /api/v1/seasons/{season_id}/restore` | Restaurar una temporada borrada hace menos de 30 días. Vuelve a validar el área y las temporadas de las que viene: si ya no cabe, 422. Pasados los 30 días, o si no está borrada, 404. Lo borrado no cuenta en el área libre ni en el progreso | P1 (HU-204) |
| `GET /api/v1/lots/{lot_id}/progress` | Progreso derivado del historial | P1 (HU-167) |
| `GET /api/v1/seasons/{season_id}/growth` | Línea de tiempo de un cultivo en curso, de la siembra a la cosecha estimada, para simular el paso del tiempo (ver «Cuerpos de cuenta») | P1 (HU-186) |

**Cómo viaja la credencial:** el usuario y la contraseña solo se envían una vez, en `/auth/register` y `/auth/login`, siempre por HTTPS. La API responde con un token de sesión aleatorio de 256 bits; en la base de datos se guarda solo su hash. De ahí en adelante cada petición lleva únicamente ese token, nunca la contraseña. El token viaja en una cookie `httpOnly` (el JavaScript de la página no lo puede leer), `Secure` (solo por HTTPS) y `SameSite=Lax`; además, la API rechaza las peticiones que cambian datos si su cabecera `Origin` no es la de la web (protección contra CSRF). Como la API y la web comparten origen, no hace falta CORS. Contraseña de al menos 8 caracteres. Los intentos fallidos de entrar, de cambiar la contraseña y de borrar la cuenta cuentan para los topes de abajo. Recuperar la contraseña queda en P1, porque no se guarda correo ni celular. Un usuario solo ve y modifica sus propios lotes: pedir uno ajeno responde 404.

**Límites por conexión y topes de intentos** (15 de octubre de 2026, revisión de seguridad; aprobado por Felipe). Todo lo que verifica una contraseña (entrar, cambiar la contraseña y borrar la cuenta) anota el intento **antes** de verificarla:

| Límite | Cuánto | Dónde vive | Respuesta |
|---|---|---|---|
| Contraseñas que no coinciden para un usuario **desde una misma conexión** | 5 en 15 minutos | Memoria de la API | `429` `too_many_attempts`, solo para esa conexión |
| Intentos fallidos de un usuario **desde cualquier conexión** (ataque repartido) | 20 en 15 minutos | `login_attempts` (sobrevive a un reinicio) | `429` `too_many_attempts` |
| Inicios de sesión desde una misma conexión, salgan bien o mal | 30 en 15 minutos | Memoria de la API | `429` `too_many_requests` |
| Registros desde una misma conexión, salgan bien o mal (también los `409`) | 10 por hora | Memoria de la API | `429` `too_many_requests` |
| Cálculos de contraseña (Argon2, unos 64 MiB cada uno) a la vez | 4; los demás esperan hasta 10 segundos | Memoria de la API | `503` `server_busy` |

- Todo `429` y el `503` llevan `Retry-After` con los segundos que faltan.
- Así, equivocarse a propósito con la contraseña de otra persona solo bloquea la conexión de quien lo hace, no la cuenta; y el `409` del registro no sirve para probar en masa qué usuarios existen.
- **La IP no se guarda** (R9): ni en la base de datos ni en el log. En memoria solo queda su hash con una sal aleatoria que cambia cada vez que arranca la API, y se olvida al pasar la ventana. Un reinicio borra los límites de memoria; el tope general sigue.
- Detrás de un proxy, Uvicorn toma la IP de `X-Forwarded-For` solo si el proxy está en `FORWARDED_ALLOW_IPS`; si no, todas las personas parecerían una sola conexión.

**Cabeceras de seguridad** (14 de octubre de 2026, revisión de seguridad; aprobado por Felipe): toda respuesta lleva `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` y, por HTTPS, `Strict-Transport-Security`. `/api/v1/auth/*` y `/api/v1/me*` van además con `Cache-Control: no-store`. La documentación (`/api/docs` y `/api/openapi.json`) solo existe con `AGROSENSE_API_DOCS=true`, en desarrollo.

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
| `GET /api/v1/admin/metrics` | `admin` | Métricas agregadas: consultas por día, cuentas creadas, municipios y cultivos más consultados (de `usage_daily`), lotes por municipio y siembras por cultivo (de las cuentas). Sin datos personales. Un municipio o cultivo con menos de 5 consultas, o con lotes de menos de 5 cuentas, va en «Otros» |
| `POST /api/v1/dev/fixtures` | `developer` | Cargar datos de prueba en la base de desarrollo |

- Un usuario bloqueado no puede iniciar sesión (`403` con `account_blocked`) y sus sesiones abiertas se cierran.
- En desarrollo, toda respuesta construida con datos simulados lleva `"simulated": true` en la raíz; la web muestra la franja «Modo simulación · datos de ejemplo» (HU-014, R5). En producción ese campo no existe.
- El administrador ve datos personales de los agricultores, así que el texto de consentimiento lo dice («el equipo de soporte puede ver sus lotes para resolver un problema») desde la versión 2 (vigente: 3, HU-163). El agricultor ve en «Mi actividad» (`GET /me/activity`) qué acciones de soporte se hicieron sobre sus datos.
- Por decidir: qué más hace el administrador, y si su panel va en esta web o en una aparte.

### Cómo se conectan cálculo y cuentas

- `/diagnostics`, `/rotations`, `/water-plans`, `/changes`, `/calendar` y `/scenarios` **no guardan los datos de la finca ni quién consultó (R9)**, con o sin cuenta. Desde HU-170 (P1) solo suman 1 al contador anónimo `usage_daily`.
- Con sesión, `/diagnostics` y `/rotations` (y `/calendar`, P1) aceptan `lot_id` solo para leer el lote: usan su suelo, su altitud (para la aptitud) y su verdor (las medianas de las celdas que toca su polígono) y su `irrigated`; el resultado es el mismo que si se enviaran esos datos. `/water-plans` y `/changes` no reciben `lot_id` y usan siempre los datos del municipio, también con cuenta.
- Para las estrategias de un lote, la web envía en `previous_crop_ids` los cultivos de las temporadas de las que viene el terreno que se va a sembrar (`follows_season_ids`). Sin cuenta, el usuario elige a mano el cultivo anterior, o ninguno.
- Para el agua de un ciclo de una estrategia, la web llama a `/water-plans` con el cultivo del ciclo, su `sowing_date`, el área de la entrada como `total_area_ha` y `area_pct` 100 (HU-215).
- Para el plan de agua de una zona (P1, HU-145), la web arma `crops` con las temporadas en curso de los lotes de ese municipio: `total_area_ha` es la suma de las áreas de los lotes y `area_pct` la parte de cada temporada (`seasons.area_ha` / `total_area_ha`).

### Identificador de petición

Toda respuesta lleva la cabecera `X-Request-ID` (UUID). Si la petición trae una válida, se respeta; si no, la API la crea. Ese identificador aparece en cada línea de log de la terminal y en `activity_log.request_id`, y la web lo muestra en los errores («Código para soporte: …») para que un ticket se pueda rastrear.

### Errores

| Situación | Respuesta |
|---|---|
| Entrada inválida (municipio o cultivo fuera del catálogo, diagnóstico de un cultivo con `kind` distinto de `crop`, prioridades fuera de rango o todas en 0, `sowing_date` con formato inválido, anterior a hoy o a más de doce meses (salvo en «Mi cultivo»), `month` fuera de 1 a 12, `cycles` distinto de 2 o 3, más de 3 cultivos en `previous_crop_ids`, `/changes` con un cultivo que no es `kind = crop`, porcentajes de finca que pasan de 100, registro sin consentimiento, temporadas en curso que pasan del área del lote, lote editado más chico que sus temporadas en curso, `follows_season_ids` inválido, nombre vacío, contraseña nueva de menos de 8 caracteres o igual a la actual) | `422` |
| Endpoint de cuenta sin sesión válida, usuario y contraseña incorrectos, o `lot_id` en `/diagnostics`, `/rotations` o `/calendar` sin sesión | `401` |
| Contraseña actual incorrecta al cambiarla, o contraseña incorrecta al borrar la cuenta | `403` `wrong_password` (la sesión sigue abierta) |
| Rol sin permiso para el endpoint, o cuenta bloqueada al iniciar sesión | `403` |
| Nombre de usuario ya registrado, al crear la cuenta o al editar el perfil | `409` |
| Un lote que quedaría más chico que lo sembrado en curso | `422` `area_below_seasons` |
| Demasiados intentos con la contraseña de un usuario (`too_many_attempts`) o demasiadas peticiones de entrar o crear cuenta desde una misma conexión (`too_many_requests`) | `429` con `Retry-After` |
| Todos los cálculos de contraseña ocupados (agregado el 15 de octubre de 2026; aprobado por Felipe) | `503` `server_busy` con `Retry-After` |
| Lote o temporada que no existe o es de otro usuario | `404` |
| Entrada válida sin datos | `200` con `insufficient_data` en la señal |
| Cultivo que no es apto para la zona | `200` con `suitability.level = not_suitable`, luz `red` y acción `rotate`; sin ventanas |
| Las cuentas no se pueden atender (agregado el 12 de octubre de 2026; aprobado por Felipe): la base de datos no responde, o su esquema no está en la última migración que trae el código | `503` en los endpoints de cuenta, con `code = accounts_database_down` o `accounts_migration_pending`. El mensaje para la persona es el mismo en los dos casos («Las cuentas no están disponibles en este momento. Puede seguir consultando sin cuenta.»); el motivo exacto va al log de la terminal. Los endpoints que no usan la base de datos siguen respondiendo |
| El dataset publicado no está o no se puede leer (agregado el 15 de octubre de 2026; aprobado por Felipe) | `503` `dataset_unavailable` en los endpoints que lo leen (catálogos y crear o editar un lote); el motivo va al log. `GET /version` responde igual, con los campos del dataset nulos |
| El dataset publicado no trae precios (HU-221, **por aprobar**) | `503` `market_unavailable` en `/market/*` |
| Fallo interno | `500` con `{"error": {"code": "...", "message": "...", "request_id": "..."}}` |

## Cuerpos y respuestas

Los ejemplos son ilustrativos, no son datos reales. Toda respuesta de cálculo trae `versions` con `dataset` y `rules` (R4).

### Cuerpo de `POST /api/v1/diagnostics`

```json
{ "municipality_id": "MUNICIPIO_ID", "crop_id": "papa", "sowing_date": "2026-08-03", "irrigated": false,
  "priorities": { "water": 5, "frost": 3, "heat": 3, "soil": 3, "supply": 0, "market": 3 }, "lot_id": null }
```

Evalúa **una ventana de siembra**: de `sowing_date` a la cosecha estimada de ese cultivo (ver `specs/01-reglas.md`). Es riesgo histórico de esa época del año, no un pronóstico: la misma fecha en otro año da el mismo resultado de clima.

- `sowing_date` anterior a hoy o a más de doce meses responde 422 (ver «Fechas» en `/calendar`).
- `irrigated`: si hay riego. Con riego, la falta de lluvia no es un riesgo en la señal `water`. Nulo se trata como sin riego y se agrega a las limitaciones.
- `priorities`: el peso de 0 a 5 de cada señal para quien consulta (ver «Las prioridades del agricultor» en `specs/01-reglas.md`). Opcional: sin él se usan los pesos por defecto de `weights.yaml`. Fuera de rango, o todas en 0, responde 422.
- `lot_id` es opcional y exige sesión: con él, la señal de suelo usa el suelo del lote y `irrigated` se toma del lote. Un lote ajeno responde 404.

**No guarda los datos de la finca ni quién consultó (R9).** La respuesta está en «Respuesta de diagnóstico», más abajo.

### Respuesta de `GET /api/v1/trends`

Tres series separadas, cada una con su unidad, para no mezclar unidades en un eje (W3):

- `water`: por año, la lluvia que cayó en los meses de la ventana (`precip_mm`) y lo que el cultivo habría necesitado (`need_mm`), en mm, con el `source_id` de la lluvia (la fuente que calcula la señal).
- `supply`: por año, `planted_ha` (ha) y `preliminary` del semestre en que cae la fecha de siembra.
- `ndvi`: por `period` (1 a 23), `ndvi_normal` del municipio, con `source_id` y `quality` (HU-208). Sirve para ver cuándo suele estar verde el campo junto a la ventana.

Sin datos para una serie, la serie viene vacía con `status = insufficient_data`.

### Respuesta de `GET /api/v1/version`

`dataset_version`, `rules_version`, `created_at`, `region`, `default_weights` (los pesos por defecto de `weights.yaml`, para mostrarlos antes de consultar), `weights_version` (la versión de `weights.yaml`), `weights_reasons` (el porqué de cada peso, como criterio del equipo) y `sources` (lista con `source_id`, `name`, `institution`, `url`, `coverage` y `license`). Es lo que muestra el panel «¿Cómo funciona y de dónde sale esto?».

> **13 de octubre de 2026 (aprobado por Felipe):** el endpoint ya existe con lo único que hay, los pesos por defecto. Mientras no haya dataset ni reglas publicados, `dataset_version`, `rules_version`, `created_at` y `region` vienen nulos y `sources` vacío: no se inventan (R5). `weights_version` y `weights_reasons` son campos nuevos. No usa la base de datos ni guarda nada.

### Cuerpo y respuesta de `POST /api/v1/rotations`

```json
{
  "municipality_id": "MUNICIPIO_ID",
  "sowing_date": "2027-01-04",
  "previous_crop_ids": ["papa"],
  "cycles": 3,
  "priorities": { "water": 3, "soil": 5, "income": 2, "risk": 4 },
  "signal_priorities": null,
  "irrigated": false,
  "lot_id": null
}
```

Responde **estrategias de rotación** de hasta 3 ciclos (ver «Estrategias de rotación» en `specs/01-reglas.md`). No guarda los datos de la finca ni quién consultó (R9).

- `cycles`: 2 o 3; sin él, 3. Otro valor responde 422.
- `sowing_date`: la fecha en que se sembraría el primer ciclo. Anterior a hoy o a más de doce meses responde 422. Los ciclos siguientes pueden caer después de esos doce meses.
- `previous_crop_ids`: de 0 a 3 cultivos del catálogo (de cualquier `kind`), el más reciente primero. Vacía es la primera siembra del terreno.
- `priorities`: las cuatro prioridades de la rotación (`water`, `soil`, `income`, `risk`), un entero de 0 a 5 cada una.
- `signal_priorities`: opcional; los pesos de 0 a 5 por señal para el diagnóstico de cada ciclo, igual que `priorities` de `/diagnostics`. Sin él, los de `weights.yaml`.
- `irrigated`: igual que en el diagnóstico. `lot_id` es opcional y exige sesión: con él, el suelo, la altitud, el verdor e `irrigated` salen del lote.
- Prioridades fuera de rango, o todas en 0, responden 422.

```json
{
  "strategies": [
    {
      "rank": 1,
      "crop_ids": ["avena_vicia", "arveja", "papa"],
      "total_score": 76,
      "scores": { "water": 74, "soil": 88, "income": 60, "risk": 71 },
      "cycles": [
        { "cycle": 1, "crop_id": "avena_vicia", "sowing_date": "2027-01-04", "harvest_estimate": "2027-04-19",
          "harvest_basis": "calendar", "light": "green", "light_default": "green", "limiting_signal": "water", "high_risk": false },
        { "cycle": 2, "crop_id": "arveja", "sowing_date": "2027-04-26", "harvest_estimate": "2027-08-23",
          "harvest_basis": "calendar", "light": "yellow", "light_default": "yellow", "limiting_signal": "frost", "high_risk": false },
        { "cycle": 3, "crop_id": "papa", "sowing_date": "2027-08-30", "harvest_estimate": "2028-01-24",
          "harvest_basis": "calendar", "light": "green", "light_default": "green", "limiting_signal": "frost", "high_risk": false }
      ],
      "soil_health": {
        "nitrogen": { "status": "available", "level": "favorable", "rule_ids": ["REGLA_ID"],
          "reasons": ["Dos de los tres ciclos tienen leguminosas (vicia y arveja), que fijan nitrógeno"] },
        "organic_carbon": { "status": "available", "level": "favorable", "rule_ids": ["REGLA_ID"],
          "reasons": ["El carbono orgánico estimado del suelo es bajo y la estrategia empieza con un abono verde"] },
        "soil_cover": { "status": "available", "level": "moderate", "rule_ids": ["REGLA_ID"],
          "reasons": ["El suelo queda cubierto 11 de los 13 meses de la estrategia"] },
        "pest_break": { "status": "available", "level": "favorable", "rule_ids": ["REGLA_ID"],
          "reasons": ["La papa vuelve al terreno después de dos ciclos de otras familias"] }
      },
      "reasons": ["Empieza con un abono verde y su suelo tiene poco carbono orgánico", "Ningún ciclo tiene un riesgo alto de clima"],
      "limitations": ["Suelo estimado para el municipio, no para su lote"]
    }
  ],
  "excluded": [
    { "crop_ids": ["papa", "arveja", "haba"], "cycle": 1, "kind": "rule", "rule_id": "REGLA_ID",
      "reason": "Repite la familia de la papa, que había antes en el terreno" },
    { "crop_ids": ["arveja", "papa", "maiz"], "cycle": 2, "kind": "high_risk", "signal": "frost",
      "reason": "Alto riesgo en el ciclo 2: heladas frecuentes en el llenado de la papa" }
  ],
  "weights": { "water": 3, "soil": 5, "income": 2, "risk": 4 },
  "soil_basis": "municipality",
  "limitations": ["Compara estrategias según reglas con fuente. No predice cuánto va a mejorar el suelo"],
  "versions": { "dataset": "2026.11.0", "rules": "1.0.0" }
}
```

- `strategies`: hasta 10, en orden (`rank`). `scores` trae el puntaje de 0 a 100 de cada criterio (nulo si no califica) y `total_score` el total ponderado por `weights`.
- Cada ciclo trae además `diagnosis`: el diagnóstico de esa ventana, con la misma forma de «Respuesta de diagnóstico» (sin `request`, `best_windows` ni `alternatives`). El ejemplo lo omite por brevedad. `light` es la luz con los pesos de quien consulta y `light_default` con los de AgroSense. En un ciclo de descanso, `light`, `light_default`, `limiting_signal` y `diagnosis` vienen nulos.
- `soil_health`: los cuatro criterios de salud del suelo, cada uno con `status`, `level` (nulo con `insufficient_data`), `reasons` y `rule_ids` (reglas de `rotation_rules`, con fuente). **No es una predicción de cuánto mejora el suelo.**
- `excluded`: las estrategias descartadas, con el ciclo y el motivo. `kind` es `rule` (viola una regla de filtro; trae `rule_id`), `not_suitable` (un cultivo no se da en la zona), `soil_ph` (el pH queda fuera de todo el intervalo) o `high_risk` (un ciclo con `water`, `frost` o `heat` desfavorable y crítica; trae `signal`).
- La oferta y el mercado no excluyen estrategias: entran solo por `income`.
- `soil_basis`: `lot` o `municipality`.
- Sin estrategias válidas, `strategies` viene vacía y `excluded` dice por qué.

Con cuenta, la web arma `previous_crop_ids` con los cultivos de las temporadas de las que viene el terreno que se va a sembrar (`follows_season_ids`). Con el suelo (del lote o del municipio): un cultivo cuyo rango de pH tolerado queda fuera de **todo** el intervalo `ph_p05`–`ph_p95` excluye la estrategia por regla (R3); el carbono orgánico entra al criterio `organic_carbon` de `soil_health`, con reglas de `rotation_rules` con fuente. Cada estrategia trae de 2 a 4 razones.

Cambió el 11 de octubre de 2026 (decisión 12): antes respondía secuencias de 2 ciclos sin `soil_health`, y `previous_crop_ids` pedía al menos un cultivo.

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

La suma de `area_pct` no puede pasar de 100. Lo que falta es terreno en descanso o sin sembrar. Con cuenta, entran las temporadas en curso de cada lote, cada una con su `area_ha`. La respuesta trae, por cultivo y por finca, el déficit mensual y el volumen en m³ para año normal y año seco, con rangos y el rótulo de estimación (R10). **Este endpoint no guarda los datos de la finca ni quién consultó (R9)**, aunque el usuario tenga cuenta. No recibe `lot_id`: usa siempre el suelo del municipio (`soil_municipality`), también con cuenta.

La lluvia es la de la fuente que define `sources.yaml` y la ET0 es la de `climate_month`; la respuesta dice la fuente de cada una. Trae además `soil_moisture`: por mes, la humedad del suelo normal de la zona según cada fuente (`source_id`, `indicator`, `value`, `unit`), la de POWER y, si existe, la de SMAP. Es contraste: no cambia el déficit.

### Respuesta de `GET /api/v1/changes`

`GET /api/v1/changes?municipality_id=MUNICIPIO_ID&crop_id=papa&irrigated=false`. Compara dos periodos de la misma fuente (ver «Qué cambió en la zona» en `specs/01-reglas.md`). **Es historia comparada, nunca pronóstico.** No guarda nada (R9). `irrigated` es opcional; sin él se compara sin riego y se dice en las limitaciones.

```json
{
  "request": { "municipality_id": "MUNICIPIO_ID", "crop_id": "papa", "irrigated": false },
  "periods": {
    "before": { "period_id": "p1981_2000", "start_year": 1981, "end_year": 2000, "source_id": "nasa_power" },
    "after": { "period_id": "p2005_2024", "start_year": 2005, "end_year": 2024, "source_id": "nasa_power" }
  },
  "suitability": { "level": "suitable", "score": 92, "reasons": ["La altitud del municipio (2.660 m) está dentro del rango de la papa"] },
  "months": [
    { "month": 1,
      "frost_freq_pct": { "status": "available", "before": 30, "after": 18, "change": -12 },
      "precip_normal_mm": { "status": "available", "before": 28, "after": 35, "change": 7 },
      "tmax_p90_c": { "status": "insufficient_data", "before": null, "after": 21.4, "change": null } }
  ],
  "best_windows": {
    "before": [ { "month": 3, "limiting_signal": "frost", "limiting_score": 64, "high_risk": false } ],
    "after": [ { "month": 4, "limiting_signal": "water", "limiting_score": 68, "high_risk": false } ]
  },
  "weights_basis": "default",
  "reasons": ["Entre 1981 y 2000 heló en enero en 30 de cada 100 años; entre 2005 y 2024, en 18"],
  "limitations": ["NASA POWER es un reanálisis, no una observación directa", "La oferta, el mercado y el suelo son los mismos en los dos periodos"],
  "versions": { "dataset": "2026.11.0", "rules": "1.0.0" }
}
```

- `months` trae los doce meses; el ejemplo muestra uno. `change` es después menos antes. Si un periodo no tiene datos suficientes, el valor de ese periodo y `change` son nulos y `status` es `insufficient_data`.
- `best_windows`: de 0 a 3 meses de siembra por periodo, con el orden de las ventanas y los pesos por defecto; nunca uno de alto riesgo.
- Si `sources.yaml` da la lluvia a GPM IMERG, la respuesta trae también `precip_periods` (los dos periodos de IMERG, desde 2001) y `precip_normal_mm` sale de esos periodos; las heladas y el calor siguen saliendo de los de NASA POWER. Nunca se compara un periodo de una fuente con uno de otra.
- Si el cultivo no es apto para la zona, `best_windows` viene vacío y `suitability` dice por qué; `months` viene igual.

### Cuerpo y respuesta de `POST /api/v1/calendar`

```json
{ "municipality_id": "MUNICIPIO_ID", "crop_id": "papa", "sowing_date": null, "month": null,
  "priorities": null, "irrigated": false, "lot_id": null }
```

Tiene dos lecturas, según venga o no `sowing_date`. No guarda los datos de la finca ni quién consultó (R9) y trae `versions` y `reference_date` (el día desde el que se cuentan los doce meses), para que el mismo resultado se pueda reproducir (R4).

Fechas: la ventana de un mes empieza el día 1 y la de una semana, su lunes. `month` se refiere a la próxima vez que llega ese mes desde `reference_date`. En `/diagnostics` y en «Planear una siembra» de `/calendar`, una fecha de siembra anterior a hoy o a más de doce meses responde 422; el mes en curso se acepta aunque su día 1 ya haya pasado. En «Mi cultivo» (`/calendar` con `sowing_date`), la fecha puede ser pasada.

**Planear una siembra (sin `sowing_date`).** Responde `suitability` y `windows`:

- Sin `month`: doce ventanas, una por cada mes de siembra de los próximos doce meses (`granularity = month`). Con `month` (1 a 12): las semanas de ese mes (`granularity = week`).
- Cada ventana trae `sowing_start`, `harvest_estimate`, `signals` (las mismas del diagnóstico, cada una con `status`, `level`, `critical`, `reasons`, `score` de 0 a 100 —nulo si no califica— y `counts`), `limiting_signal` (la señal que más limita), `limiting_score`, `weighted_score` (promedio ponderado por los pesos), `high_risk` y `rank`. La respuesta trae también `weights` y `weights_basis`.
- `priorities`: un entero de 0 a 5 por señal (`water`, `frost`, `heat`, `soil`, `supply`, `market`), igual que en el diagnóstico. Sin él, se usan los pesos por defecto de `weights.yaml`. Fuera de rango, o todas en 0, responde 422.
- `best_windows`: de 0 a 3 ventanas, las primeras del orden que no son de alto riesgo. Puede venir vacío: no siempre hay un buen mes.
- Si el cultivo no es apto para la zona, `windows` viene vacío y `suitability` dice por qué.

**Mi cultivo (con `sowing_date`).** Sirve para seguir un cultivo ya sembrado. Responde `months`: cada mes entre la siembra y la cosecha estimada, con `month`, `year`, `stage` (la etapa que ocupa la mayor parte del mes), `basis` (`observed` hasta el último dato de temperatura y `normal_year` después, con el mismo cálculo de la línea de tiempo) y estos bloques, con `status`, `level` y `reasons` como las señales (R1):

- `frost`: `frost_freq_pct` del mes, `sensitive` (alguna etapa de ese mes es sensible a la helada) y `watch` (es sensible y el nivel no es `favorable`).
- `heat`: `tmax_p90_c` del mes frente a `heat_max_c` del cultivo, con `sensitive` y `watch` igual que la helada.
- P1: `fertilizing` (días de aguacero), `field_work` (ventanas secas para labores y cosecha), `blight` (días favorables a la gota, solo para cultivos con esa regla) y `selling` (índice estacional de precio del mes; nunca precio futuro).

Más `harvest_estimate` y `harvest_basis`. El cruce entre el riesgo y la etapa lo hace el motor, no la web (R5). La vista del lote combina esta lectura con el plan de agua: el calendario no repite el riego.

`irrigated` se comporta igual que en el diagnóstico; con `lot_id`, el suelo y `irrigated` salen del lote. El diagnóstico de una ventana y el orden de las ventanas salen del mismo cálculo: una ventana del calendario y el diagnóstico de esa fecha dan las mismas señales.

### Cuerpos de cuenta

- `PATCH /api/v1/me`: `priorities` (opcional: un entero de 0 a 5 por señal; nulo vuelve a los de AgroSense; fuera de rango o todas en 0, 422), `display_name` (1 a 40 caracteres) y `username` (3 a 30 caracteres: letras minúsculas sin tilde, números, punto y guion bajo), ambos opcionales. Cambiar el usuario no cierra la sesión. El consentimiento no se edita aquí: para retirarlo se borra la cuenta.
- `POST /api/v1/me/password`: `current_password` y `new_password` (al menos 8 caracteres y distinta de la actual). Responde `204`.
- `POST /api/v1/lots` y `PATCH /api/v1/lots/{lot_id}`: `name`, `municipality_id`, `irrigated` (opcional: si el lote tiene riego) y `geometry` (polígono GeoJSON). Sin `geometry`, `area_ha` (mayor que cero) es obligatoria; con `geometry`, `area_ha` la calcula la API y se ignora la enviada.
- Mientras no exista el mapa (HU-164, entrega 2; anotado el 15 de octubre de 2026), un `geometry` en `POST` o `PATCH` responde `422` `geometry_not_available` y el lote se guarda solo con el área escrita.
- Respuesta de `GET /api/v1/lots/{lot_id}`: el lote, `soil` (las propiedades de `soil_grid` como mediana del polígono, con `basis`: `lot` o `municipality`, y `cells`; nulo mientras no esté publicado el suelo, HU-181) y `current_seasons` (lista, vacía si no hay temporadas en curso; de mayor a menor área) con `season_id`, `crop_id`, `area_ha`, `follows_season_ids`, `sowing_date`, `days_since_sowing`, `stage`, `stage_progress_pct`, `stage_method` (`thermal_time` si se usó la temperatura acumulada del municipio, `calendar` si se usó la duración por días porque faltan datos de temperatura o grados-día con fuente), `thermal_data_until` (fecha del último dato de temperatura usado; nula con `calendar`) y `versions`. Es una estimación con el clima del municipio, no una observación del lote (HU-150).
- Respuesta de `GET /api/v1/seasons/{season_id}/growth`: `points` (uno por semana, de la siembra a la cosecha estimada) con `date`, `stage`, `stage_progress_pct`, `gdd_accumulated` y `basis`: `observed` mientras hay temperatura real (`climate_day`, hasta `thermal_data_until`) y `normal_year` después (`climate_normal_doy`). Más `today`, `harvest_estimate` (fecha, siempre con `harvest_basis`) y `versions`. Lo `normal_year` es una estimación con un año normal, **no un pronóstico**: la web lo rotula así. Sin temperatura con fuente o sin grados-día del cultivo, se usa la duración por calendario y se dice (R1). No guarda nada.
- `POST /api/v1/lots/{lot_id}/seasons`: `crop_id`, `sowing_date`, `area_ha` (opcional: sin ella ocupa lo que queda libre del lote), `follows_season_ids` (opcional: qué había antes en ese terreno) y el diagnóstico que vio el usuario al sembrar (`diagnosis_light`, `diagnosis_light_default`, `diagnosis_action`, `diagnosis_weights`, `diagnosis_irrigated`, `dataset_version`, `rules_version`), que la web toma de la respuesta de `/diagnostics`. Si no consultó el diagnóstico, esos campos van nulos.
- `PATCH /api/v1/seasons/{season_id}`: `harvest_date` o correcciones de `crop_id`, `sowing_date`, `area_ha` y `follows_season_ids`, con las mismas validaciones.
- Respuesta de `GET /api/v1/lots/{lot_id}/progress`: `seasons_count`, `valid_rotations_count`, `rotations` (una por cada relación entre una temporada y una de sus sucesoras, con `from_season_id`, `to_season_id`, `valid` y `violated_rule_ids`, la lista de reglas de `rotation_rules` que viola; vacía si cumple) y `milestones` (cada uno con `milestone_id`, `achieved_at` y `basis`: la regla de `rotation_rules` o el hecho registrado que lo produce), más `versions`.

### Respuesta de diagnóstico

```json
{
  "request": {
    "municipality_id": "MUNICIPIO_ID",
    "crop_id": "papa",
    "sowing_date": "2026-08-03",
    "irrigated": false,
    "lot_id": null
  },
  "suitability": {
    "level": "suitable",
    "score": 92,
    "reasons": ["La altitud del municipio (2.660 m) está dentro del rango de la papa (2.000 a 3.500 m)"]
  },
  "window": {
    "sowing_start": "2026-08-03",
    "harvest_estimate": "2026-12-28",
    "harvest_basis": "calendar",
    "supply_semester": { "year": 2025, "semester": "B", "preliminary": true }
  },
  "overall": {
    "light": "green",
    "action": "sow",
    "high_risk": false,
    "weights_basis": "farmer",
    "limiting_signal": "frost",
    "reasons": ["Con sus prioridades, la oferta no cuenta para la luz y ninguna otra señal es desfavorable"]
  },
  "overall_default": {
    "light": "yellow",
    "action": "rotate",
    "high_risk": false,
    "weights_basis": "default",
    "limiting_signal": "supply",
    "reasons": ["Con el criterio de AgroSense, la oferta desfavorable pone la luz en amarillo"]
  },
  "weights": { "water": 5, "frost": 3, "heat": 3, "soil": 3, "supply": 0, "market": 3 },
  "signals": {
    "water": {
      "status": "available",
      "level": "favorable",
      "critical": false,
      "score": 86,
      "counts": true,
      "indicators": ["water_deficit_mm"],
      "reasons": ["En 7 de los últimos 10 años, la lluvia de agosto a diciembre cubrió lo que necesita la papa"]
    },
    "frost": {
      "status": "available",
      "level": "moderate",
      "critical": false,
      "score": 58,
      "counts": true,
      "indicators": ["frost_freq_pct"],
      "reasons": ["Sembrando en agosto, heló en el llenado (diciembre) 12 de cada 100 años"]
    },
    "heat": {
      "status": "available",
      "level": "favorable",
      "critical": false,
      "score": 94,
      "counts": true,
      "indicators": ["tmax_p90_c"],
      "reasons": ["De agosto a diciembre, la máxima rara vez pasa de 22 °C; la papa aguanta hasta 28 °C"]
    },
    "soil": {
      "status": "available",
      "level": "favorable",
      "critical": false,
      "score": 80,
      "counts": true,
      "indicators": ["ph"],
      "reasons": ["pH estimado de 5,2 a 5,8, dentro del rango de la papa. Estimación de 250 m: confírmelo con un análisis de suelo"]
    },
    "supply": {
      "status": "available",
      "level": "unfavorable",
      "critical": false,
      "score": 30,
      "counts": false,
      "indicators": ["planted_change_pct"],
      "sources": [
        { "source_id": "eva", "indicator": "planted_change_pct", "value": 35, "unit": "%", "period": "2025-B", "preliminary": true, "used": true },
        { "source_id": "agrosense", "indicator": "active_plantings_ha", "value": 38, "unit": "ha", "period": "2026-10-11", "accounts": 14, "used": false }
      ],
      "reasons": ["En 2025 B (último dato, preliminar) se sembró 35 % más papa que en los tres semestres B anteriores"]
    },
    "market": {
      "status": "insufficient_data",
      "level": null,
      "critical": false,
      "score": null,
      "counts": true,
      "indicators": [],
      "reasons": ["Sin datos de mercado para la zona"]
    }
  },
  "alternatives": [
    { "crop_id": "haba", "reasons": ["Sale bien en clima en esta ventana", "En 2025 B se sembró menos haba que en los tres semestres B anteriores"] }
  ],
  "limitations": ["Datos EVA del último año son preliminares", "Suelo estimado para el municipio, no para su lote"],
  "versions": { "dataset": "2026.11.0", "rules": "1.0.0" }
}
```

- `overall` usa los pesos de quien consulta y `overall_default` los de AgroSense; la web muestra las dos luces cuando difieren. `counts` dice si la señal cuenta para la luz con los pesos de quien consulta, `score` es su calificación de 0 a 100 y cada luz trae su `limiting_signal`, la señal que más limita con esos pesos.
- `sources` aparece en una señal cuando hay más de una fuente: todas se muestran para contrastar y `used` dice cuál calculó la señal. En `water` trae la lluvia de GPM IMERG y la de NASA POWER (una con `used = true`) y, con `used = false`, la humedad del suelo de la zona: `soil_wetness_root` de POWER y, si existe, `sm_rootzone_m3_m3` de SMAP, cada una en su unidad. El ejemplo no lo muestra.
- Con `lot_id`, la aptitud usa la altitud del lote (NASADEM) y la razón lo dice.
- `alternatives` es P1 (HU-197): en el MVP no viene. Cuando exista, viene cuando la acción, con alguno de los dos juegos de pesos, es `rotate`: hasta tres cultivos aptos para la zona que en esta ventana salen bien en clima y tienen mejor oferta. Nunca uno no apto ni uno que sale mal en clima. Se ordenan igual que las ventanas (factor limitante y después prioridades). Un candidato con aptitud `insufficient_data` puede aparecer, con esa limitación. También vienen cuando el cultivo consultado no es apto.
- `best_windows` viene cuando la acción de `overall` o de `overall_default` es `other_window`: hasta tres ventanas de los próximos doce meses, sin las de alto riesgo, cada una con `sowing_start`, `harvest_estimate`, `limiting_signal`, `limiting_score`, `weighted_score` y `high_risk`. Puede venir vacío. En el ejemplo no viene, porque sus acciones son `sow` y `rotate`.
- `harvest_estimate` es siempre una fecha y su base va al lado, en `harvest_basis`: `calendar` cuando sale de la duración de la ficha (el MVP, HU-220) y `normal_year` cuando sale del clima de un año normal (P1, HU-150 y HU-186). Así en `window`, en los ciclos de `/rotations` y, en P1, en «Mi cultivo» de `/calendar` y en `/growth`.- `suitability.score` es una nota informativa de 0 a 100 de la aptitud (la curva de altitud de la ficha: 100 dentro del rango óptimo, 0 fuera del absoluto); la web la muestra con su nota y en la escala de cinco semillas. No es una señal: no entra al semáforo ni al orden. La aptitud se decide solo por la altitud: solo fuera del rango absoluto es `not_suitable`. Si el cultivo no es apto para la zona, `suitability.level` es `not_suitable`, `window` y `signals` vienen nulos, la luz es `red` y la acción `rotate`.
- Las señales del P1 (`excess_rain`, `disease`, `harvest_weather`) aparecen solo cuando existen.

## Valores permitidos y semáforo

Ver `specs/01-reglas.md` (valores permitidos y agregación del semáforo).
