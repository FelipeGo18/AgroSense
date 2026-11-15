"""Oferta: Evaluaciones Agropecuarias Municipales (EVA) de la UPRA (HU-031; specs/02-contratos.md, tabla `supply_semester`).

Fuente: «Evaluaciones Agropecuarias Municipales – EVA. 2019 - 2025. Base Agrícola», publicada por la UPRA en
datos.gov.co (`uejq-wxrr`), licencia CC BY-SA 4.0. Una fila por municipio (código DIVIPOLA de 5 dígitos), cultivo
(código de la clasificación EVA) y periodo, con el área sembrada y cosechada (ha), la producción (t) y el rendimiento
(t/ha).

**Los periodos.** El metadato de la columna `periodo` dice «Periodo de siembra (Año y semestre para transitorios) y
solo año para los cultivos permanentes»: `2024A` y `2024B` son las siembras del primero y del segundo semestre de 2024.
Se toma A = enero a junio y B = julio a diciembre, el supuesto del contrato que confirma HU-001. Los cultivos del MVP
son transitorios: una fila de un cultivo del MVP sin semestre se descarta con su motivo.

**Lo que cambió en 2022.** La nota del conjunto de datos dice que, desde 2022, el área cosechada, la producción y el
rendimiento de los transitorios son las cosechas efectivas de cada periodo; antes eran las de las siembras de ese
periodo. Por eso desde 2022 el área cosechada de un semestre puede pasar a la sembrada (se cosecha lo sembrado en el
anterior): no es un error y no se descarta. El área sembrada sí significa lo mismo en todos los años, y es la que
usa la oferta (HU-032).

**Preliminares.** La misma nota dice que «las cifras de los dos últimos años son susceptibles de modificación»: las
filas de los dos últimos años que trae la descarga van con `preliminary` verdadero.

**Cultivos.** `pipeline/eva_crops.yaml` dice qué códigos de EVA son cada cultivo del catálogo. Si un cultivo tiene
varios códigos (por ejemplo, el maíz amarillo y el blanco), sus áreas y su producción se suman, que es lo que mide la
oferta: cuánto se sembró de ese cultivo. Si alguna de las filas sumadas no trae un valor, el total de ese valor queda
nulo: no se suma una parte como si fuera el todo (R1).

**Indicadores (HU-032).** `planted_change_pct` y `dept_share_pct` salen del área sembrada ya sumada; la definición
está en `indicators()` y en EP-03.

Lo propio de Colombia (DIVIPOLA y su departamento, la clasificación EVA, los semestres) vive solo en este adaptador
(R7).
"""

import csv
import io
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from pipeline.sources.fetch import fetch

SOURCE_ID = "eva"
DATASET = "uejq-wxrr"
ROWS_URL = f"https://www.datos.gov.co/resource/{DATASET}.csv"
META_URL = f"https://www.datos.gov.co/api/views/{DATASET}.json"
PAGE_URL = f"https://www.datos.gov.co/d/{DATASET}"
LICENSE = "CC BY-SA 4.0"

CACHE = Path("data/raw/eva")
ROWS_FILE = "eva.csv"
META_FILE = "eva.meta.json"

# Filas por página de la API de datos.gov.co. La región piloto trae unas 33 000: dos páginas.
PAGE_ROWS = 20_000
PAGE_TIMEOUT_S = 300
PAGE_MAX_BYTES = 200 * 2**20
# Los metadatos del conjunto (nombre, licencia, fecha de actualización): hoy pesan unos 30 KB.
META_TIMEOUT_S = 60
META_MAX_BYTES = 2 * 2**20

# Las columnas de la descarga que se leen (el nombre de campo de datos.gov.co).
COLUMNS = {
    "department_id": "c_digo_dane_departamento",
    "municipality_id": "c_digo_dane_municipio",
    "eva_code": "c_digo_del_cultivo",
    "period": "periodo",
    "planted_ha": "rea_sembrada",
    "harvested_ha": "rea_cosechada",
    "production_t": "producci_n",
    "yield_t_ha": "rendimiento",
}
VALUES = ("planted_ha", "harvested_ha", "production_t", "yield_t_ha")
SEMESTER = re.compile(r"^(\d{4})([AB])$")
DIVIPOLA = re.compile(r"^\d{5}$")
PRELIMINARY_YEARS = 2
# La variación del área sembrada compara contra el promedio del mismo semestre de estos años anteriores
# (specs/02-contratos.md, «Lo que depende de verificar una fuente»; HU-032).
CHANGE_YEARS = 3

# Los motivos para descartar una fila de un cultivo del MVP (HU-031: «filas rechazadas reportadas con motivo»).
REASONS = ("outside_region", "unknown_municipality", "no_semester", "bad_value", "negative_value", "no_data", "duplicate")

OUTPUT_SCHEMA = {
    "municipality_id": pl.String,
    "crop_id": pl.String,
    "year": pl.Int16,
    "semester": pl.String,
    "source_id": pl.String,
    "planted_ha": pl.Float64,
    "harvested_ha": pl.Float64,
    "production_t": pl.Float64,
    "yield_t_ha": pl.Float64,
    "planted_change_pct": pl.Float64,
    "dept_share_pct": pl.Float64,
    "preliminary": pl.Boolean,
    "quality": pl.String,
}


class EvaError(ValueError):
    """La descarga o el mapeo de cultivos no sirven. El mensaje dice qué falla."""


def _query(departments: list[str], offset: int) -> str:
    where = "c_digo_dane_departamento in(" + ",".join(f"'{d}'" for d in departments) + ")"
    params = {"$where": where, "$order": ":id", "$limit": str(PAGE_ROWS), "$offset": str(offset)}
    return f"{ROWS_URL}?{urllib.parse.urlencode(params)}"


def download(departments: list[str], cache: Path = CACHE) -> Path:
    """Baja las filas de los departamentos de la región, todas las de sus cultivos, y los metadatos. Es lo único que usa
    la red; lo demás lee de la caché. Se guardan todos los cultivos: cambiar `eva_crops.yaml` no obliga a bajar otra vez."""
    cache.mkdir(parents=True, exist_ok=True)
    header: list[str] | None = None
    rows: list[list[str]] = []
    offset = 0
    while True:
        request = urllib.request.Request(_query(departments, offset))  # noqa: S310 - dirección fija de datos.gov.co
        page = fetch(request, cache / "eva.page.csv", PAGE_TIMEOUT_S, PAGE_MAX_BYTES)
        reader = csv.reader(io.StringIO(page.read_text(encoding="utf-8")))
        page_header = next(reader, None)
        page_rows = list(reader)
        page.unlink()
        if page_header is None:
            break
        if header is not None and page_header != header:
            raise EvaError("Las páginas de EVA llegaron con columnas distintas: vuelva a bajar.")
        header = page_header
        rows.extend(page_rows)
        if len(page_rows) < PAGE_ROWS:
            break
        offset += PAGE_ROWS
    if header is None or not rows:
        raise EvaError(f"datos.gov.co no devolvió filas de EVA para los departamentos {departments}.")
    # Los metadatos pasan por `fetch`, con su tope de tiempo y tamaño, como las páginas (revisión de Haider del PR #117).
    meta_request = urllib.request.Request(META_URL)  # noqa: S310 - dirección fija de datos.gov.co
    meta_file = fetch(meta_request, cache / "eva.meta.download.json", META_TIMEOUT_S, META_MAX_BYTES)
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    meta_file.unlink()
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    (cache / ROWS_FILE).write_text(out.getvalue(), encoding="utf-8", newline="\n")
    keep = {
        "name": meta.get("name"),
        "attribution": meta.get("attribution"),
        "license": (meta.get("license") or {}).get("name"),
        "rows_updated_at": meta.get("rowsUpdatedAt"),
        "departments": departments,
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (cache / META_FILE).write_text(json.dumps(keep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return cache / ROWS_FILE


def read_cache(cache: Path = CACHE) -> tuple[pl.DataFrame, dict[str, Any]]:
    """Las filas crudas, todas como texto (así un valor raro se ve y se descarta con su motivo), y los metadatos."""
    rows_path, meta_path = cache / ROWS_FILE, cache / META_FILE
    if not rows_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"No está la caché de EVA en {cache}. Bájela con: uv run python -m pipeline.build --descargar")
    raw = pl.read_csv(rows_path, infer_schema=False)
    missing = [col for col in COLUMNS.values() if col not in raw.columns]
    if missing:
        raise EvaError(f"A la caché de EVA le faltan columnas: {missing}. Vuelva a bajarla.")
    return raw, json.loads(meta_path.read_text(encoding="utf-8"))


def crop_codes(mapping: dict[str, Any], catalog_ids: set[str] | None = None) -> dict[int, str]:
    """El código de EVA de cada cultivo de `eva_crops.yaml`, como {código: crop_id}. Falla si un cultivo no está en el
    catálogo, si un código está en dos cultivos o si un cultivo sin códigos no dice por qué."""
    crops = mapping.get("crops") or {}
    if not crops:
        raise EvaError("`eva_crops.yaml` no trae cultivos en `crops`.")
    if catalog_ids is not None and (unknown := sorted(set(crops) - catalog_ids)):
        raise EvaError(f"Cultivos de `eva_crops.yaml` que no están en `catalog/crops.yaml`: {unknown}.")
    codes: dict[int, str] = {}
    for crop_id, entry in crops.items():
        entry = entry or {}
        if unknown_fields := sorted(set(entry) - {"eva_codes", "notes", "reason"}):
            raise EvaError(f"{crop_id}: campos que no se conocen en `eva_crops.yaml`: {unknown_fields}.")
        if "eva_codes" not in entry:
            raise EvaError(f"{crop_id}: falta `eva_codes` en `eva_crops.yaml` (nulo si EVA no tiene el cultivo).")
        if not entry["eva_codes"]:
            if not entry.get("reason"):
                raise EvaError(f"{crop_id}: sin códigos de EVA, `eva_crops.yaml` tiene que decir por qué (`reason`).")
            continue
        for code in entry["eva_codes"]:
            if not isinstance(code, int):
                raise EvaError(f"{crop_id}: el código de EVA {code!r} no es un número.")
            if code in codes:
                raise EvaError(f"El código de EVA {code} está en dos cultivos: {codes[code]} y {crop_id}.")
            codes[code] = crop_id
    return codes


def _number(col: str) -> pl.Expr:
    """El texto como número. Vacío es nulo (sin dato, R1); un texto que no es número también, y se marca aparte."""
    return pl.col(col).str.strip_chars().replace("", None).cast(pl.Float64, strict=False)


def normalize(
    raw: pl.DataFrame, codes: dict[int, str], departments: list[str], municipality_ids: set[str], counts: Counter[str]
) -> pl.DataFrame:
    """Las filas de los cultivos del MVP, una por municipio, cultivo y semestre, con su motivo para cada descartada.

    `counts` cuenta las leídas (`read`), las de otros cultivos (`other_crop`, que no son un error: no son del MVP) y las
    descartadas por cada motivo de `REASONS`. Sale ordenada por su llave (R4)."""
    counts["read"] += raw.height
    rows = raw.select(**{name: pl.col(col).str.strip_chars() for name, col in COLUMNS.items()})
    rows = rows.with_columns(
        # Un código de 4 cifras es uno de 5 sin el cero de adelante (los de Antioquia, 05xxx).
        municipality_id=pl.when(pl.col("municipality_id").str.contains(r"^\d{4}$"))
        .then("0" + pl.col("municipality_id"))
        .otherwise(pl.col("municipality_id")),
        eva_code=pl.col("eva_code").cast(pl.Int64, strict=False),
    )
    crop_map = pl.DataFrame({"eva_code": list(codes), "crop_id": list(codes.values())}, schema={"eva_code": pl.Int64, "crop_id": pl.String})
    rows = rows.join(crop_map, on="eva_code", how="left")
    counts["other_crop"] += rows.filter(pl.col("crop_id").is_null()).height
    rows = rows.filter(pl.col("crop_id").is_not_null())

    def drop(frame: pl.DataFrame, bad: pl.Expr, reason: str) -> pl.DataFrame:
        # Una comparación con un nulo da nulo, y `filter` saca esa fila de los dos lados: se perdería sin motivo.
        bad = bad.fill_null(False)
        counts[reason] += frame.filter(bad).height
        return frame.filter(~bad)

    outside = ~pl.col("department_id").is_in(departments) | ~pl.col("municipality_id").str.contains(DIVIPOLA.pattern)
    rows = drop(rows, outside, "outside_region")
    rows = drop(rows, ~pl.col("municipality_id").is_in(sorted(municipality_ids)), "unknown_municipality")
    rows = drop(rows, ~pl.col("period").str.contains(SEMESTER.pattern), "no_semester")
    rows = rows.with_columns(
        year=pl.col("period").str.slice(0, 4).cast(pl.Int16),
        semester=pl.col("period").str.slice(4, 1),
        **{f"{col}_num": _number(col) for col in VALUES},
    )
    bad = pl.any_horizontal(pl.col(col).is_not_null() & (pl.col(col) != "") & pl.col(f"{col}_num").is_null() for col in VALUES)
    rows = drop(rows, bad, "bad_value")
    rows = rows.with_columns(**{col: pl.col(f"{col}_num") for col in VALUES}).drop(f"{col}_num" for col in VALUES)
    rows = drop(rows, pl.any_horizontal(pl.col(col) < 0 for col in VALUES), "negative_value")
    rows = drop(rows, pl.all_horizontal(pl.col(col).is_null() for col in VALUES), "no_data")
    rows = drop(rows, pl.struct("municipality_id", "eva_code", "year", "semester").is_duplicated(), "duplicate")
    if rows.is_empty():
        return pl.DataFrame(schema=OUTPUT_SCHEMA)
    years = sorted(set(rows["year"].to_list()))
    preliminary_from = years[-1] - PRELIMINARY_YEARS + 1
    key = ["municipality_id", "crop_id", "year", "semester"]
    # Un cultivo con varios códigos suma sus filas; si alguna no trae el valor, el total queda nulo (R1).
    summed = rows.group_by(key).agg(
        parts=pl.len(),
        yield_single=pl.col("yield_t_ha").first(),
        **{col: pl.when(pl.col(col).null_count() == 0).then(pl.col(col).sum()) for col in ("planted_ha", "harvested_ha", "production_t")},
    )
    summed = summed.with_columns(
        # Un solo código: el rendimiento que publica EVA. Varios: producción / área cosechada, como lo define EVA; sin
        # área cosechada, 0, como publica EVA con un solo código (revisión de Haider del PR #117: antes quedaba nulo y la
        # fila salía partial aunque EVA trae los cuatro valores).
        yield_t_ha=pl.when(pl.col("parts") == 1)
        .then(pl.col("yield_single"))
        .when(pl.col("harvested_ha") == 0)
        .then(0.0)
        .when(pl.col("harvested_ha") > 0)
        .then((pl.col("production_t") / pl.col("harvested_ha")).round(2)),
        **{col: pl.col(col).round(2) for col in ("planted_ha", "harvested_ha", "production_t")},
    )
    complete = pl.all_horizontal(pl.col(col).is_not_null() for col in VALUES)
    summed = indicators(summed)
    return (
        summed.with_columns(
            source_id=pl.lit(SOURCE_ID),
            preliminary=pl.col("year") >= preliminary_from,
            # `partial` si EVA no trae alguno de los cuatro valores (contrato, «Valores de `quality`») o si la variación
            # tuvo menos de tres semestres anteriores con dato (contrato, HU-032).
            quality=pl.when(complete & (pl.col("prior_semesters") >= CHANGE_YEARS)).then(pl.lit("ok")).otherwise(pl.lit("partial")),
        )
        .select(list(OUTPUT_SCHEMA))
        .cast(OUTPUT_SCHEMA)
        .sort(key)
    )


def indicators(table: pl.DataFrame) -> pl.DataFrame:
    """Los dos indicadores de HU-032 sobre las filas ya sumadas por municipio, cultivo, año y semestre.

    - **`planted_change_pct`:** cuánto cambió el área sembrada frente al promedio del mismo semestre de los tres años
      anteriores (para 2025B, 2022B, 2023B y 2024B), en %: (sembrada − promedio) / promedio × 100, con un decimal. Solo
      cuentan los semestres con dato: un año sin fila es sin dato (R1), no 0 ha. Sin ninguno, o con un promedio de 0 ha
      (no se puede dividir), es nulo. `prior_semesters` dice cuántos hubo: con menos de tres la fila es `partial`.
    - **`dept_share_pct`:** qué parte del área sembrada del departamento en ese cultivo y semestre es del municipio, en %,
      con dos decimales. El departamento son los dos primeros dígitos del DIVIPOLA. El total suma los municipios con
      fila: es la parte entre los que reportan. Si uno de ellos no trae el área, o el total es 0, es nulo (R1).
    """
    crop = ["municipality_id", "crop_id", "semester"]
    planted = table.select(*crop, prior_year="year", prior_ha="planted_ha").drop_nulls("prior_ha")
    window = (
        table.select(*crop, "year")
        .join(planted, on=crop)
        .filter((pl.col("prior_year") < pl.col("year")) & (pl.col("prior_year") >= pl.col("year") - CHANGE_YEARS))
        .group_by(*crop, "year")
        .agg(prior_semesters=pl.len(), prior_avg=pl.col("prior_ha").mean())
    )
    table = table.join(window, on=[*crop, "year"], how="left").with_columns(prior_semesters=pl.col("prior_semesters").fill_null(0))
    department = ["department", "crop_id", "year", "semester"]
    table = table.with_columns(department=pl.col("municipality_id").str.slice(0, 2))
    totals = table.group_by(department).agg(dept_ha=pl.when(pl.col("planted_ha").null_count() == 0).then(pl.col("planted_ha").sum()))
    table = table.join(totals, on=department, how="left")
    return table.with_columns(
        planted_change_pct=pl.when(pl.col("prior_avg") > 0).then(
            ((pl.col("planted_ha") - pl.col("prior_avg")) / pl.col("prior_avg") * 100).round(1)
        ),
        dept_share_pct=pl.when(pl.col("dept_ha") > 0).then((pl.col("planted_ha") / pl.col("dept_ha") * 100).round(2)),
    ).drop("prior_avg", "department", "dept_ha")


def source(meta: dict[str, Any], table: pl.DataFrame) -> dict[str, Any]:
    """La fila de `sources` de esta fuente (R8), con lo que cubre en la región."""
    updated = meta.get("rows_updated_at")
    updated_text = f"; actualizada por la UPRA el {datetime.fromtimestamp(updated, UTC):%Y-%m-%d}" if updated else ""
    if table.is_empty():
        period = None
    else:
        first = table.sort("year", "semester").row(0, named=True)
        last = table.sort("year", "semester").row(-1, named=True)
        period = f"Siembras de {first['year']}{first['semester']} a {last['year']}{last['semester']}{updated_text}"
    towns = table["municipality_id"].n_unique() if not table.is_empty() else 0
    crops = ", ".join(sorted(set(table["crop_id"].to_list()))) if not table.is_empty() else "ningún cultivo"
    return {
        "source_id": SOURCE_ID,
        "name": meta.get("name") or "Evaluaciones Agropecuarias Municipales – EVA. 2019 - 2025. Base Agrícola",
        "institution": "Unidad de Planificación de Tierras Rurales, Adecuación de Tierras y Usos Agropecuarios (UPRA)",
        "url": PAGE_URL,
        "downloaded_at": meta.get("downloaded_at"),
        "period_covered": period,
        "coverage": (
            f"Colombia: 1.103 municipios según la UPRA. En la región, {towns} municipios con algún cultivo del MVP ({crops}); "
            "un municipio sin fila de un cultivo en un semestre es sin dato: EVA no dice si no se sembró o no se reportó"
        ),
        "license": LICENSE,
        "citation": None,
        "notes": (
            "Área sembrada y cosechada, producción y rendimiento por municipio (DIVIPOLA), cultivo y semestre de siembra "
            "(A = enero a junio, B = julio a diciembre; supuesto por confirmar en HU-001). Desde 2022 el área cosechada, la "
            "producción y el rendimiento son las cosechas efectivas de cada semestre; antes, las de sus siembras. Las cifras "
            "de los dos últimos años son preliminares. Los cultivos salen de pipeline/eva_crops.yaml (HU-031). La variación "
            "del área sembrada es contra el promedio del mismo semestre de los tres años anteriores con dato (nula sin "
            "ninguno o con promedio 0; partial con menos de tres) y la participación es la del municipio entre los que "
            "reportan en su departamento (HU-032). En muchas filas EVA repite el área del mismo semestre del año anterior."
        ),
    }
