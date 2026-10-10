# Contratos de datos y de API

Los identificadores del código van en inglés y en `snake_case` para evitar tildes; los textos de la interfaz van en español. En lugar de una tabla larga de indicadores, se usan pocas tablas por granularidad: así cada fila tiene una llave clara y cada columna una unidad fija.

> **Estado:** propuesta congelable. Se congela en HU-011 y HU-012. Después de eso, un cambio necesita acuerdo del equipo porque rompe el trabajo en paralelo.

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

## Endpoints

| Endpoint | Uso | Prioridad |
|---|---|---|
| `GET /api/v1/catalogs/municipalities` | Municipios habilitados de la región | P0 |
| `GET /api/v1/catalogs/crops` | Cultivos habilitados y sus semestres | P0 |
| `GET /api/v1/trends` | Series para las gráficas de un municipio y cultivo | P0 |
| `POST /api/v1/diagnostics` | Diagnóstico de una ventana de siembra | P0 |
| `POST /api/v1/rotations` | Ranking de rotaciones según prioridades | P0 |
| `POST /api/v1/water-plans` | Plan de agua de una finca | P0 |
| `GET /api/v1/version` | Versión del dataset y de las reglas | P0 |
| `POST /api/v1/scenarios` | Escenario hipotético y diferencias con el caso base | P1 |

### Errores

| Situación | Respuesta |
|---|---|
| Entrada inválida (municipio o cultivo fuera del catálogo, prioridades fuera de rango, porcentajes de finca que pasan de 100) | `422` |
| Entrada válida sin datos | `200` con `insufficient_data` en la señal |
| Fallo interno | `500` con `{"error": {"code": "...", "message": "..."}}` |

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

La suma de `area_pct` no puede pasar de 100. Lo que falta es terreno en descanso o sin sembrar. La respuesta trae, por cultivo y por finca, el déficit mensual y el volumen en m³ para año normal y año seco, con rangos y el rótulo de estimación (R10). **Estos datos no se persisten (R9).**

## Respuesta de diagnóstico (ilustrativa, no son datos reales)

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
    "reasons": ["Oferta alta frente a semestres anteriores"]
  },
  "signals": {
    "climate": {
      "status": "available",
      "level": "favorable",
      "indicators": ["precip_anomaly_pct"],
      "reasons": []
    },
    "supply": {
      "status": "available",
      "level": "unfavorable",
      "indicators": ["planted_change_pct"],
      "reasons": []
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
