import json
import shutil
from pathlib import Path

from backend.api.calculations import _compare_changes
from backend.dataset import load
from backend.engine.changes import Period, PeriodPair

EXAMPLES = Path(__file__).resolve().parents[1] / "data" / "examples"


def test_load_reads_historical_climate_and_manifest_periods():
    dataset = load(EXAMPLES)

    manifest = json.loads((EXAMPLES / "manifest.json").read_text(encoding="utf-8"))

    assert dataset.climate_change_month is not None
    assert dataset.climate_change_month.height > 0
    assert dataset.periods == tuple(manifest["periods"])

    assert {
        "municipality_id",
        "period_id",
        "month",
        "source_id",
        "frost_freq_pct",
        "precip_normal_mm",
        "tmax_p90_c",
    }.issubset(set(dataset.climate_change_month.columns))


def test_load_accepts_dataset_without_historical_climate(tmp_path):
    folder = tmp_path / "dataset"
    shutil.copytree(EXAMPLES, folder)

    # Solo se elimina de la copia temporal creada para esta prueba.
    (folder / "climate_change_month.parquet").unlink()

    dataset = load(folder)

    assert dataset.climate_change_month is None
    assert dataset.periods


def test_load_accepts_manifest_without_periods(tmp_path):
    folder = tmp_path / "dataset"
    shutil.copytree(EXAMPLES, folder)

    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("periods", None)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )

    dataset = load(folder)

    assert dataset.periods == ()


def test_loaded_dataset_connects_to_changes_engine():
    dataset = load(EXAMPLES)

    configured_periods = sorted(
        (Period(**item) for item in dataset.periods),
        key=lambda period: period.start_year,
    )
    assert len(configured_periods) == 2

    periods = PeriodPair(
        before=configured_periods[0],
        after=configured_periods[1],
    )

    result = _compare_changes(
        dataset=dataset,
        municipality_id="15001",  # Tunja, presente en el ejemplo.
        periods=periods,
    )

    january = result["months"][0]["frost_freq_pct"]

    # Valores del Parquet de ejemplo, no observaciones reales.
    assert january["before"] == 60.0
    assert january["status"] == "available"
    assert january["change"] == january["after"] - january["before"]
    assert len(result["months"]) == 12
