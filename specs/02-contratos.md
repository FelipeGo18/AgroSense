# Contratos de datos y de API

Los identificadores del código van en inglés y en `snake_case` para evitar tildes; los textos de la interfaz van en español. En lugar de una tabla larga de indicadores, se usan pocas tablas por granularidad: así cada fila tiene una llave clara y cada columna una unidad fija.

> **Estado:** propuesta congelable. Se congela en HU-011 y HU-012. **Responsable: Haider.** Después de congelado, cualquier cambio lo hace o lo aprueba Haider, porque rompe el trabajo en paralelo.

## Tablas publicadas (Parquet)

| Tabla | Llave primaria | Columnas principales | Origen |
|---|---|---|---|
| `municipalities` | `municipality_id` (DIVIPOLA, 5 dígitos) | `name`, `department_id`, `department`, `lat`, `lon`, `altitude_m` (P1) | DANE |
| `crops` | `crop_id` | `name_es`, `family`, `cycle_months`, `sowing_semesters`, `water_need`, `root_type`, `fixes_nitrogen`, `altitude_min_m`, `altitude_max_m`, `source_ids` | Catálogo |
| `rotation_rules` | `rule_id` | `kind` (`filter`, `bonus`, `penalty`), `condition`, `effect`, `criterion`, `source_id` | Catálogo |
| `climate_semester` | `municipality_id`, `year`, `semester` | `precip_mm`, `precip_normal_mm`, `precip_anomaly_pct`, `temp_mean_c`, `temp_anomaly_c`, `valid_days`, `quality`, `source_id` | NASA |
| `climate_month` | `municipality_id`, `year`, `month` | `precip_mm`, `precip_normal_mm`, `precip_dry_mm` (año seco), `et0_mm`, `et0_normal_mm`, `quality`, `source_id` | NASA |
| `crop_stages` | `crop_id`, `stage` | `days`, `kc`, `source_id` | Catálogo (FAO-56 o fuente local) |
| `supply_semester` | `municipality_id`, `crop_id`, `year`, `semester` | `planted_ha`, `harvested_ha`, `production_t`, `yield_t_ha`, `planted_change_pct`, `dept_share_pct`, `preliminary`, `quality`, `source_id` | EVA |
| `market_month` (P1) | `crop_id`, `market_id`, `month` | `price_cop_kg`, `volume_t`, `seasonal_index`, `quality`, `source_id` | SIPSA |
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
| `users` | `user_id` (UUID) | `username` (único), `password_hash`, `display_name`, `consent_version`, `consent_at`, `created_at` | Sin correo, celular, documento de identidad ni dirección. La contraseña se guarda solo como hash Argon2 |
| `sessions` | `session_id` (UUID) | `user_id`, `token_hash`, `created_at`, `expires_at` | Una fila por sesión abierta. Se guarda el hash del token, nunca el token. Vence a los 30 días |
| `lots` | `lot_id` (UUID) | `user_id`, `municipality_id`, `name`, `area_ha`, `created_at`, `updated_at` | Un usuario tiene uno o varios lotes; la «zona» es el municipio (R7). La ubicación exacta del lote queda fuera del P0 |
| `seasons` | `season_id` (UUID) | `lot_id`, `crop_id`, `sowing_date`, `harvest_date` (nula si sigue en curso), `diagnosis_light`, `diagnosis_action`, `dataset_version`, `rules_version`, `created_at` | Una temporada por cultivo y ciclo en el lote. Guarda el diagnóstico que se vio al sembrar, con sus versiones (R4) |

- Borrar un usuario borra en cascada sus sesiones, lotes y temporadas.
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
| `DELETE /api/v1/me` | Borrar la cuenta con sus sesiones, lotes y temporadas | P0 |
| `GET /api/v1/lots` · `POST /api/v1/lots` | Listar y crear lotes | P0 |
| `GET`, `PATCH`, `DELETE /api/v1/lots/{lot_id}` | Ver, editar y borrar un lote | P0 |
| `GET /api/v1/lots/{lot_id}/seasons` · `POST /api/v1/lots/{lot_id}/seasons` | Historial del lote y nueva temporada | P0 |
| `PATCH /api/v1/seasons/{season_id}` | Registrar la cosecha o corregir una temporada | P0 |
| `GET /api/v1/lots/{lot_id}/progress` | Progreso derivado del historial | P0 |

La sesión viaja en una cookie `httpOnly`, `Secure` y `SameSite=Lax`; como la API y la web comparten origen, no hace falta CORS. Contraseña de al menos 8 caracteres. Tras 5 intentos fallidos de inicio de sesión en 15 minutos, responde 429. Recuperar la contraseña queda en P1, porque no se guarda correo ni celular. Un usuario solo ve y modifica sus propios lotes: pedir uno ajeno responde 404.

### Cómo se conectan cálculo y cuentas

- `/diagnostics`, `/rotations` y `/water-plans` son iguales con o sin cuenta y **no guardan nada**.
- Para las rotaciones de un lote, la web envía los cultivos de sus temporadas anteriores en `previous_crop_ids`. Sin cuenta, el usuario elige a mano el cultivo anterior.
- Para el plan de agua de una zona, la web arma `crops` con los lotes de ese municipio: `total_area_ha` es la suma de sus áreas y `area_pct` la parte de cada lote.

### Errores

| Situación | Respuesta |
|---|---|
| Entrada inválida (municipio o cultivo fuera del catálogo, prioridades fuera de rango, porcentajes de finca que pasan de 100, registro sin consentimiento, temporada en curso duplicada) | `422` |
| Endpoint de cuenta sin sesión válida, o usuario y contraseña incorrectos | `401` |
| Nombre de usuario ya registrado | `409` |
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

- `POST /api/v1/lots` y `PATCH /api/v1/lots/{lot_id}`: `name`, `municipality_id`, `area_ha` (mayor que cero).
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
