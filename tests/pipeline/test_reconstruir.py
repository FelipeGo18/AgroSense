"""Reconstruir el dataset con un comando (HU-123) y los logs del pipeline (HU-177).

Lo publicado se revisa contra su manifiesto; cada paso del pipeline deja una línea con la fuente, las filas leídas y las
descartadas con su motivo. Sin red: usan la caché de ejemplo.
"""

import json
import sys

import polars as pl
import pytest
from structlog.testing import capture_logs

from pipeline import build
from pipeline.sources import dane, dane_mgn, sipsa
from tests.conftest import SAMPLE_MARKETS, SAMPLE_META, SAMPLE_MUNICIPALITIES, SAMPLE_REGION, SAMPLE_SIPSA_ROWS, sipsa_xml
from tests.pipeline.test_municipios import feature_collection

REGION = {**SAMPLE_REGION, "region": {**SAMPLE_REGION["region"], "markets": SAMPLE_MARKETS}}
CROPS = {"papa": {"product_id": "papa-negra"}, "haba": {"product_id": None, "reason": "Ejemplo: sin producto en SIPSA."}}


@pytest.fixture
def caches(tmp_path, monkeypatch):
    """Las cachés de ejemplo de DIVIPOLA, los límites del MGN y SIPSA, y la región y el mapeo de ejemplo en lugar de los del
    repositorio. El catálogo de cultivos es el real (`catalog/crops.yaml`)."""
    cache, market_cache = tmp_path / "raw", tmp_path / "raw-sipsa"
    cache.mkdir()
    market_cache.mkdir()
    (cache / dane.ROWS_FILE).write_text(json.dumps(SAMPLE_MUNICIPALITIES), encoding="utf-8")
    (cache / dane.META_FILE).write_text(json.dumps(SAMPLE_META), encoding="utf-8")
    for department, ids in (("15", ["15407", "15646"]), ("25", ["25899"])):
        (cache / dane_mgn._file(department)).write_text(json.dumps(feature_collection(ids)), encoding="utf-8")
    (market_cache / sipsa.ROWS_FILE).write_text(sipsa_xml(SAMPLE_SIPSA_ROWS), encoding="utf-8")
    (market_cache / sipsa.META_FILE).write_text("2026-10-20T15:34:00+00:00", encoding="utf-8")
    monkeypatch.setattr(build, "load_region", lambda: REGION)
    monkeypatch.setattr(build, "load_crops", lambda: CROPS)
    return cache, market_cache


def rebuild(tmp_path, caches):
    cache, market_cache = caches
    folder = tmp_path / "published"
    build.build(folder=folder, cache=cache, market_cache=market_cache)
    return folder


# HU-123 · Lo publicado coincide con su manifiesto


def test_lo_que_se_acaba_de_publicar_coincide_con_su_manifiesto(tmp_path, caches):
    folder = rebuild(tmp_path, caches)
    manifest = build.verify(folder, REGION["dataset_version"])
    expected = {"municipalities", "municipality_boundaries", "crops", "crop_stages", "sources"}
    assert set(manifest["tables"]) == expected | {"market_price_day", "market_price_season", "market_month"}


def test_reconstruir_dos_veces_da_las_mismas_tablas(tmp_path, caches):
    cache, market_cache = caches
    build.build(folder=tmp_path / "a", cache=cache, market_cache=market_cache)
    build.build(folder=tmp_path / "b", cache=cache, market_cache=market_cache)
    for table in sorted(path.name for path in (tmp_path / "a").glob("*.parquet")):
        assert (tmp_path / "a" / table).read_bytes() == (tmp_path / "b" / table).read_bytes(), table


def test_si_falta_una_tabla_no_coincide(tmp_path, caches):
    folder = rebuild(tmp_path, caches)
    (folder / "market_month.parquet").unlink()
    with pytest.raises(build.ValidationError, match="falta `market_month.parquet`"):
        build.verify(folder)


def test_si_una_tabla_no_tiene_las_filas_del_manifiesto_no_coincide(tmp_path, caches):
    folder = rebuild(tmp_path, caches)
    pl.read_parquet(folder / "municipalities.parquet").head(1).write_parquet(folder / "municipalities.parquet")
    with pytest.raises(build.ValidationError, match="`municipalities` tiene 1 filas y el manifiesto dice 3"):
        build.verify(folder)


def test_una_tabla_que_el_manifiesto_no_nombra_no_coincide(tmp_path, caches):
    folder = rebuild(tmp_path, caches)
    pl.DataFrame({"x": [1]}).write_parquet(folder / "climate_month.parquet")
    with pytest.raises(build.ValidationError, match="no nombra"):
        build.verify(folder)


def test_otra_version_no_coincide(tmp_path, caches):
    folder = rebuild(tmp_path, caches)
    with pytest.raises(build.ValidationError, match="versión 0.0.0-pruebas"):
        build.verify(folder, "2026.11.2")


def test_sin_manifiesto_dice_como_publicar(tmp_path):
    with pytest.raises(build.ValidationError, match="pipeline.build"):
        build.verify(tmp_path)


def test_lo_publicado_en_el_repositorio_coincide_con_su_manifiesto():
    """El dataset de la demo es el que dice su manifiesto, con la versión de `region.yaml`."""
    if not (build.PUBLISHED / "manifest.json").exists():
        pytest.skip("data/published no está en esta imagen")
    build.verify(build.PUBLISHED, build.load_region()["dataset_version"])


def run_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["pipeline.build", *args])
    # `main` configura los logs de todo el proceso: en las pruebas no, para que `capture_logs` vea las líneas.
    monkeypatch.setattr(build, "configure", lambda *_args, **_kwargs: None)
    build.main()


def use_example_caches(monkeypatch, folder, caches):
    """`main` publica en `folder` con las cachés de ejemplo, en lugar de data/published y data/raw."""
    cache, market_cache = caches
    real_build = build.build
    monkeypatch.setattr(build, "PUBLISHED", folder)
    monkeypatch.setattr(build, "build", lambda download=False: real_build(folder=folder, cache=cache, market_cache=market_cache))


def test_el_comando_publica_y_revisa(tmp_path, caches, monkeypatch):
    folder = tmp_path / "published"
    use_example_caches(monkeypatch, folder, caches)
    with capture_logs() as logs:
        run_main(monkeypatch)
    assert (folder / "manifest.json").exists()
    assert logs[-1]["event"] == "dataset_published" and logs[-1]["log_level"] == "info"


def test_verificar_no_publica_y_falla_si_no_coincide(tmp_path, caches, monkeypatch):
    folder = rebuild(tmp_path, caches)
    monkeypatch.setattr(build, "PUBLISHED", folder)
    with capture_logs() as logs:
        run_main(monkeypatch, "--verificar")
    assert logs[-1]["event"] == "dataset_verified"
    (folder / "sources.parquet").unlink()
    with capture_logs() as logs, pytest.raises(SystemExit) as exit_info:
        run_main(monkeypatch, "--verificar")
    assert exit_info.value.code == 1
    assert logs[-1]["event"] == "dataset_mismatch" and logs[-1]["log_level"] == "error"
    assert "falta `sources.parquet`" in logs[-1]["detail"]


# HU-177 · Cada paso del pipeline deja su línea


def test_cada_fuente_dice_cuantas_filas_leyo_y_por_que_descarto_las_demas(tmp_path, caches):
    with capture_logs() as logs:
        rebuild(tmp_path, caches)
    read = {line["source"]: line for line in logs if line["event"] == "source_read"}
    # DIVIPOLA de ejemplo: 4 municipios, 3 de la región; Medellín es de Antioquia.
    assert (read["dane_divipola"]["rows_read"], read["dane_divipola"]["rows_kept"]) == (4, 3)
    assert read["dane_divipola"]["reasons"] == {"outside_region": 1}
    # SIPSA de ejemplo: 9 filas, 7 publicadas; una de Medellín y una zanahoria sin precio medio.
    assert (read["dane_sipsa"]["rows_read"], read["dane_sipsa"]["rows_kept"], read["dane_sipsa"]["rows_rejected"]) == (9, 7, 2)
    assert read["dane_sipsa"]["reasons"] == {"other_market": 1, "no_average": 1}
    assert all(line["detail"] for line in read.values())


def test_cada_tabla_escrita_deja_su_linea(tmp_path, caches):
    with capture_logs() as logs:
        rebuild(tmp_path, caches)
    written = {line["table"]: line["rows"] for line in logs if line["event"] == "table_written"}
    assert written["municipalities"] == 3 and written["market_price_day"] == 7
    expected = {"municipalities", "municipality_boundaries", "crops", "crop_stages", "sources"}
    assert set(written) == expected | {"market_price_day", "market_price_season", "market_month"}


def test_si_no_se_publica_el_log_dice_por_que(tmp_path, caches, monkeypatch):
    # Un mapeo con un producto que los precios de ejemplo no traen: la validación no deja publicar.
    monkeypatch.setattr(build, "load_crops", lambda: {"arveja": {"product_id": "arveja-verde-en-vaina"}})
    use_example_caches(monkeypatch, tmp_path / "published", caches)
    with capture_logs() as logs, pytest.raises(SystemExit):
        run_main(monkeypatch)
    assert logs[-1]["event"] == "dataset_not_published" and logs[-1]["log_level"] == "error"
    assert "arveja" in logs[-1]["detail"]
    assert not (tmp_path / "published").exists()


def test_sin_la_cache_de_sipsa_se_publica_lo_demas_y_el_log_dice_por_que(tmp_path, caches):
    """Reconstruir los municipios no obliga a bajar los 300 MB de SIPSA: las tablas de precios no se publican (R1)."""
    cache, _ = caches
    folder = tmp_path / "published"
    with capture_logs() as logs:
        manifest = build.build(folder=folder, cache=cache, market_cache=tmp_path / "sin-sipsa")
    assert set(manifest["tables"]) == {"municipalities", "municipality_boundaries", "crops", "crop_stages", "sources"}
    assert "dane_sipsa" not in pl.read_parquet(folder / "sources.parquet")["source_id"].to_list()
    missing = [line for line in logs if line["event"] == "source_missing"]
    assert missing and missing[0]["source"] == "dane_sipsa" and missing[0]["log_level"] == "warning"
    build.verify(folder, REGION["dataset_version"])
