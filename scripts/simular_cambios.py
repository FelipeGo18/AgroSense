"""Simulación de la comparación mensual de HU-217 con el dataset de ejemplo."""

import json
from pathlib import Path

import polars as pl

from backend.api.calc_models import MonthChange
from backend.engine.changes import (
    MONTH_NAMES,
    Period,
    PeriodPair,
    compare_climate_months,
)


def main() -> None:
    # Este script carga archivos. La función del motor sigue siendo pura.
    data_dir = Path("data/examples")

    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    table = pl.read_parquet(data_dir / "climate_change_month.parquet")

    # Los periodos salen del manifiesto, no se escriben manualmente.
    configured_periods = sorted(
        (Period(**item) for item in manifest["periods"]),
        key=lambda period: period.start_year,
    )
    if len(configured_periods) != 2:
        raise ValueError("Esta simulación necesita exactamente dos periodos")

    periods = PeriodPair(
        before=configured_periods[0],
        after=configured_periods[1],
    )

    # Tunja: municipio presente en el Parquet de ejemplo.
    municipality_id = "15001"
    rows = table.filter(pl.col("municipality_id") == municipality_id).to_dicts()

    if not rows:
        raise ValueError("El municipio no tiene filas en el archivo de ejemplo")

    result = compare_climate_months(
        municipality_id=municipality_id,
        rows=rows,
        periods=periods,
    )

    for month in result["months"]:
        MonthChange.model_validate(month)

    print("SIMULACIÓN CON DATOS DE EJEMPLO — NO SON OBSERVACIONES REALES")
    print("Municipio: Tunja (15001)")
    print(f"Versión del dataset: {manifest['dataset_version']}")
    print(f"Versión de reglas: {manifest['rules_version']}")
    print(f"Fuente: {periods.before.source_id}")
    print(f"Antes: {periods.before.start_year}–{periods.before.end_year} | Después: {periods.after.start_year}–{periods.after.end_year}")
    print("Historia comparada. No es un pronóstico.")

    indicators = (
        ("frost_freq_pct", "Heladas", "%", "puntos porcentuales"),
        ("precip_normal_mm", "Lluvia normal", "mm", "mm"),
        ("tmax_p90_c", "Temperatura máxima p90", "°C", "°C"),
    )

    for month in result["months"]:
        print(f"\n{MONTH_NAMES[month['month'] - 1].upper()}")

        for field, label, unit, difference_unit in indicators:
            comparison = month[field]
            before = comparison["before"]
            after = comparison["after"]

            before_text = "Sin datos" if before is None else f"{before:g} {unit}"
            after_text = "Sin datos" if after is None else f"{after:g} {unit}"

            print(f"  {label}: {before_text} → {after_text}")

            if comparison["status"] == "available":
                print(f"    Diferencia: {comparison['change']:+g} {difference_unit}")
            else:
                print("    Diferencia: Sin datos suficientes")

    print("\nEXPLICACIONES DE ENERO")
    for reason in result["reasons"][:3]:
        print(f"  {reason}")

    incomplete_rows = [
        row
        for row in rows
        if not (row["period_id"] == periods.before.period_id and row["source_id"] == periods.before.source_id and row["month"] == 1)
    ]

    incomplete_result = compare_climate_months(
        municipality_id=municipality_id,
        rows=incomplete_rows,
        periods=periods,
    )

    print("\nESCENARIO: FALTA ENERO DEL PERIODO ANTERIOR")
    print(
        json.dumps(
            incomplete_result["months"][0],
            ensure_ascii=False,
            indent=2,
        )
    )
    print("Se conservan los valores posteriores; las diferencias quedan en insufficient_data.")

    print("\nValidación del formato mensual: correcta.")
    print("Esta simulación todavía no calcula aptitud ni mejores ventanas.")


if __name__ == "__main__":
    main()
