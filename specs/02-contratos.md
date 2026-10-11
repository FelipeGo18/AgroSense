# Contratos de datos y de API

Los identificadores del código van en inglés y en `snake_case` para evitar tildes; los textos de la interfaz van en español. En lugar de una tabla larga de indicadores, se usan pocas tablas por granularidad: así cada fila tiene una llave clara y cada columna una unidad fija.

> **Estado:** propuesta congelable. Se congela en HU-011 y HU-012. **Responsables: Haider y Felipe.** Después de congelado, cualquier cambio lo hace o lo aprueba uno de los dos, porque rompe el trabajo en paralelo.

## Tablas publicadas (Parquet)

| Tabla | Llave primaria | Columnas principales | Origen |
|---|---|---|---|
| `municipalities` | `municipality_id` (DIVIPOLA, 5 dígitos) | `name`, `department_id`, `department`, `lat`, `lon`, `altitude_m` (P1) | DANE |
| `crops` | `crop_id` | `name_es`, `family`, `cycle_months`, `sowing_semesters`, `water_need`, `root_type`, `fixes_nitrogen`, `altitude_min_m`, `altitude_max_m`, `base_temp_c` (nula si no hay fuente), `source_ids` | Catálogo |
| `rotation_rules` | `rule_id` | `kind` (`filter`, `bonus`, `penalty`), `condition`, `effect`, `criterion`, `source_id` | Catálogo |
| `climate_semester` | `municipality_id`, `year`, `semester` | `precip_mm`, `precip_normal_mm`, `precip_anomaly_pct`, `temp_mean_c`, `temp_anomaly_c`, `valid_days`, `quality`, `source_id` | NASA |
| `climate_day` | `municipality_id`, `date` | `temp_min_c`, `temp_max_c`, `quality`, `source_id` | NASA (para la etapa del cultivo, HU-150) |
| `climate_month` | `municipality_id`, `year`, `month` | `precip_mm`, `precip_normal_mm`, `precip_dry_mm` (año seco), `et0_mm`, `et0_normal_mm`, `quality`, `source_id` | NASA |
| `crop_stages` | `crop_id`, `stage` | `days`, `kc`, `gdd` (grados-día que cierran la etapa; nulo si no hay fuente), `source_id` | Catálogo (FAO-56 o fuente local) |
| `supply_semester` | `municipality_id`, `crop_id`, `year`, `semester` | `planted_ha`, `harvested_ha`, `production_t`, `yield_t_ha`, `planted_change_pct`, `dept_share_pct`, `preliminary`, `quality`, `source_id` | EVA |
| `market_month` (P1) | `crop_id`, `market_id`, `month` | `price_cop_kg`, `volume_t`, `seasonal_index`, `quality`, `source_id` | SIPSA |
| `municipality_boundaries` | `municipality_id` | `geometry` (polígono WGS84 simplificado), `source_id` | DANE (Marco Geoestadístico Nacional) |
| `sources` | `source_id` | `name`, `institution`, `url`, `downloaded_at`, `period_covered`, `license`, `notes` | Todas |
| `manifest.json` | — | `dataset_version`, `rules_version`, `created_at`, `region`, filas y cobertura por tabla | Pipeline |

### Supuestos por confirmar en la fase 0

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
- `admin_actions` (P1): `action_id`, `admin_id`, `target_user_id`, `action` (`view`, `delete`, `restore`, `block`, `unblock`, `create_user`), `object` (lote, temporada o usuario), `ticket_id`, `reason`, `created_at`. Toda acción de un administrador sobre datos de un agricultor queda registrada.
- `support_tickets` (P1): `ticket_id`, `user_id`, `lot_id` (opcional), `message`, `status` (`open`, `in_progress`, `closed`), `created_at`, `closed_at`.
- `crop_id` y `municipality_id` deben existir en el catálogo publicado; si no, 422.
- Un lote tiene como máximo una temporada en curso (`harvest_date` nula). Crear otra sin cerrar la anterior, o con `sowing_date` anterior a la cosecha previa, responde 422.
- El **progreso** no se guarda: la API lee las temporadas del lote y le pide al motor que evalúe las reglas de filtro sobre ese historial (temporadas registradas, rotaciones que cumplen las reglas, hitos).

## Endpoints

| Endpoint | Uso | Prioridad |
|---|---|---|
| `GET /api/v1/catalogs/municipalities` | Municipios habilitados de la región: `municipality_id`, `name`, `department`, `lat`, `lon` | P0 |
| `GET /api/v1/catalogs/crops` | Cultivos habilitados: `crop_id`, `name_es`, `family`, `sowing_semesters` | P0 |
| `GET /api/v1/trends?municipality_id=&crop_id=` | Series para las gráficas (ver «Cuerpos y respuestas») | P0 |
| `POST /api/v1/diagnostics` | Diagnóstico de una ventana de siembra | P0 |
| `POST /api/v1/rotations` | Ranking de rotaciones según prioridades | P0 |
| `POST /api/v1/water-plans` | Plan de agua de una finca | P0 |
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
| `POST /api/v1/me/tickets` · `GET /api/v1/me/tickets` | Reportar un problema (opcionalmente sobre un lote) y ver sus tickets | P1 |
| `GET /api/v1/lots/{lot_id}/seasons` · `POST /api/v1/lots/{lot_id}/seasons` | Historial del lote y nueva temporada | P0 |
| `PATCH /api/v1/seasons/{season_id}` | Registrar la cosecha o corregir una temporada | P0 |
| `GET /api/v1/lots/{lot_id}/progress` | Progreso derivado del historial | P0 |

**Cómo viaja la credencial:** el usuario y la contraseña solo se envían una vez, en `/auth/register` y `/auth/login`, siempre por HTTPS. La API responde con un token de sesión aleatorio de 256 bits; en la base de datos se guarda solo su hash. De ahí en adelante cada petición lleva únicamente ese token, nunca la contraseña. El token viaja en una cookie `httpOnly` (el JavaScript de la página no lo puede leer), `Secure` (solo por HTTPS) y `SameSite=Lax`; además, la API rechaza las peticiones que cambian datos si su cabecera `Origin` no es la de la web (protección contra CSRF). Como la API y la web comparten origen, no hace falta CORS. Contraseña de al menos 8 caracteres. Tras 5 intentos fallidos de inicio de sesión en 15 minutos, responde 429; los intentos fallidos de cambiar la contraseña cuentan igual. Recuperar la contraseña queda en P1, porque no se guarda correo ni celular. Un usuario solo ve y modifica sus propios lotes: pedir uno ajeno responde 404.

### Roles (documentado; se implementa en HU-170)

Cada usuario tiene un `role`. Hoy solo existe `farmer`; los otros dos quedan definidos para no rehacer el esquema después.

| Rol | Valor | Quién es | Qué puede hacer | Dónde existe |
|---|---|---|---|---|
| Agricultor | `farmer` | El usuario final | Consultar, sus lotes, sus temporadas y su cuenta. **Nunca ve datos inventados**: solo el dataset publicado y lo que él registró (R5) | Producción y desarrollo. Es el rol por defecto al registrarse |
| Administrador web | `admin` | Quien opera la web y da soporte | Lo del agricultor, más: ver a los agricultores con sus lotes, temporadas y tickets; borrar y restaurar lotes y temporadas para resolver un ticket; crear, bloquear y desbloquear usuarios; ver métricas de uso agregadas. Toda acción queda en `admin_actions` | Producción y desarrollo. Solo lo asigna otro administrador o la configuración inicial |
| Desarrollador | `developer` | El equipo, con la app en modo desarrollo | Lo del administrador, más: simulaciones con datos inventados (HU-014), crear datos de prueba y saltarse los topes y límites (intentos, ritmo, velocidad del recorrido) | **Solo en desarrollo** (`AGROSENSE_SIMULATION=true`). La API se niega a arrancar en producción si existe un usuario `developer` o si la simulación está activa |

Endpoints previstos (P1, sin implementar; requieren sesión y el rol indicado, si no `403`):

| Endpoint | Rol | Uso |
|---|---|---|
| `GET /api/v1/admin/users` | `admin` | Lista de usuarios: `user_id`, `username`, `display_name`, `role`, `created_at`, `blocked_at`, número de lotes y de tickets abiertos |
| `GET /api/v1/admin/users/{user_id}` | `admin` | Ficha de un agricultor: perfil, lotes (también los borrados hace menos de 30 días), temporadas y tickets. Se registra en `admin_actions` como `view` |
| `DELETE` y `POST …/restore` en `/api/v1/admin/lots/{lot_id}` y `/api/v1/admin/seasons/{season_id}` | `admin` | Borrar o restaurar un lote o una temporada de un agricultor. Exige `reason` y, si viene de un ticket, `ticket_id` |
| `GET /api/v1/admin/tickets` · `PATCH /api/v1/admin/tickets/{ticket_id}` | `admin` | Bandeja de tickets y cambio de estado |
| `POST /api/v1/admin/users` | `admin` | Crear un usuario con `username`, `display_name` y una contraseña temporal |
| `PATCH /api/v1/admin/users/{user_id}` | `admin` | Bloquear o desbloquear (`blocked`), y cambiar el rol entre `farmer` y `admin` |
| `GET /api/v1/admin/metrics` | `admin` | Métricas agregadas: consultas por día, cuentas creadas, municipios y cultivos más consultados. Sin datos personales |
| `POST /api/v1/dev/fixtures` | `developer` | Cargar datos de prueba en la base de desarrollo |

- Un usuario bloqueado no puede iniciar sesión (`403` con `account_blocked`) y sus sesiones abiertas se cierran.
- En desarrollo, toda respuesta construida con datos simulados lleva `"simulated": true` en la raíz; la web muestra la franja «Modo simulación · datos de ejemplo» (HU-014, R5). En producción ese campo no existe.
- El administrador ve datos personales de los agricultores, así que el texto de consentimiento lo dice («el equipo de soporte puede ver sus lotes para resolver un problema») y sube a `consent_version` 2 (HU-163). El agricultor ve en Mi cuenta qué acciones de soporte se hicieron sobre sus datos.
- Por decidir: qué más hace el administrador, y si su panel va en esta web o en una aparte.

### Cómo se conectan cálculo y cuentas

- `/diagnostics`, `/rotations` y `/water-plans` son iguales con o sin cuenta y **no guardan nada**.
- Para las rotaciones de un lote, la web envía los cultivos de sus temporadas anteriores en `previous_crop_ids`. Sin cuenta, el usuario elige a mano el cultivo anterior.
- Para el plan de agua de una zona, la web arma `crops` con los lotes de ese municipio: `total_area_ha` es la suma de sus áreas y `area_pct` la parte de cada lote.

### Errores

| Situación | Respuesta |
|---|---|
| Entrada inválida (municipio o cultivo fuera del catálogo, prioridades fuera de rango, porcentajes de finca que pasan de 100, registro sin consentimiento, temporada en curso duplicada, nombre vacío, contraseña nueva de menos de 8 caracteres o igual a la actual) | `422` |
| Endpoint de cuenta sin sesión válida, o usuario y contraseña incorrectos | `401` |
| Contraseña actual incorrecta al cambiarla | `403` (la sesión sigue abierta) |
| Rol sin permiso para el endpoint, o cuenta bloqueada al iniciar sesión | `403` |
| Nombre de usuario ya registrado, al crear la cuenta o al editar el perfil | `409` |
| Demasiados intentos de inicio de sesión | `429` |
| Lote o temporada que no existe o es de otro usuario | `404` |
| Entrada válida sin datos | `200` con `insufficient_data` en la señal |
| Fallo interno | `500` con `{"error": {"code": "...", "message": "..."}}` |

## Cuerpos y respuestas

Los ejemplos son ilustrativos, no son datos reales. Toda respuesta de cálculo trae `versions` con `dataset` y `rules` (R4).

### Cuerpo de `POST /api/v1/diagnostics`

```json
{ "municipality_id": "MUNICIPIO_ID", "crop_id": "papa", "year": 2026, "semester": "B" }
```

La respuesta está en «Respuesta de diagnóstico», más abajo.

### Respuesta de `GET /api/v1/trends`

Dos series separadas, cada una con su unidad, para no mezclar unidades en un eje (W3):

- `climate`: por año y semestre, `precip_mm` y `precip_normal_mm` (mm).
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
  "priorities": { "water": 3, "soil": 5, "income": 2, "risk": 4 }
}
```

`previous_crop_ids` lleva de 1 a 3 cultivos del catálogo, el más reciente primero. Cada prioridad es un entero de 0 a 5; fuera de rango, o todas en 0, responde 422. La respuesta trae el ranking con el puntaje de 0 a 100 por criterio, el total ponderado, de 2 a 4 razones por opción, las opciones excluidas con la regla que las excluyó, y `versions`.

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

### Cuerpos de cuenta

- `PATCH /api/v1/me`: `display_name` (1 a 40 caracteres) y `username` (3 a 30 caracteres: letras minúsculas sin tilde, números, punto y guion bajo), ambos opcionales. Cambiar el usuario no cierra la sesión. El consentimiento no se edita aquí: para retirarlo se borra la cuenta.
- `POST /api/v1/me/password`: `current_password` y `new_password` (al menos 8 caracteres y distinta de la actual). Responde `204`.
- `POST /api/v1/lots` y `PATCH /api/v1/lots/{lot_id}`: `name`, `municipality_id` y `geometry` (polígono GeoJSON). Sin `geometry`, `area_ha` (mayor que cero) es obligatoria; con `geometry`, `area_ha` la calcula la API y se ignora la enviada.
- Respuesta de `GET /api/v1/lots/{lot_id}`: el lote y `current_season` (nula si no hay temporada en curso) con `crop_id`, `sowing_date`, `days_since_sowing`, `stage`, `stage_progress_pct`, `stage_method` (`thermal_time` si se usó la temperatura acumulada del municipio, `calendar` si se usó la duración por días porque faltan datos de temperatura o grados-día con fuente), `thermal_data_until` (fecha del último dato de temperatura usado; nula con `calendar`) y `versions`. Es una estimación con el clima del municipio, no una observación del lote (HU-150).
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
    "reasons": ["Una señal desfavorable no crítica con clima favorable: esperar otro semestre"]
  },
  "signals": {
    "climate": {
      "status": "available",
      "level": "favorable",
      "indicators": ["precip_anomaly_pct"],
      "reasons": ["Lluvia del semestre dentro del rango favorable"]
    },
    "supply": {
      "status": "available",
      "level": "unfavorable",
      "indicators": ["planted_change_pct"],
      "reasons": ["Área sembrada mayor que el promedio de los tres semestres B anteriores"]
    },
    "market": {
      "status": "insufficient_data",
      "level": null,
      "indicators": [],
      "reasons": ["Sin datos de mercado para la zona"]
    }
  },
  "limitations": ["Datos EVA del último año son preliminares"],
  "versions": { "dataset": "2026.11.0", "rules": "1.0.0" }
}
```

## Valores permitidos y semáforo

Ver `specs/01-reglas.md` (valores permitidos y agregación inicial del semáforo).
