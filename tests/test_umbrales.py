"""Los umbrales de las señales (`thresholds.yaml`, HU-075): su forma, sus fuentes y lo que la API no deja pasar."""

import polars as pl
import pytest

from backend.config.thresholds import FROM_CROP, ThresholdsError, get_thresholds, load_thresholds
from backend.config.weights import P0_SIGNALS
from pipeline import build, catalog

GOOD = """
version: "9.9.9"
levels: {favorable: 70, moderate: 40, source_id: s}
signals:
  water:  {variable: coverage_pct, unit: "%", curve: [[0, 0], [100, 100]], critical_below: 20, source_id: s}
  frost:  {variable: frost_freq_pct, unit: "%", curve: [[0, 100], [40, 0]], critical_below: 40, source_id: s}
  heat:   {variable: tmax_p90_c, unit: "°C", curve: crop, critical_below: 1, source_id: s}
  soil:   {variable: ph, unit: "pH", curve: crop, critical_below: null, source_id: s}
  supply: {variable: planted_change_pct, unit: "%", curve: null, critical_below: null, source_id: null}
  market: {variable: seasonal_index, unit: "", curve: null, critical_below: null, source_id: null}
"""


MARKET = '  market: {variable: seasonal_index, unit: "", curve: null, critical_below: null, source_id: null}\n'
SUPPLY_NULL = 'unit: "%", curve: null, critical_below: null, source_id: null}'


def write(tmp_path, text):
    path = tmp_path / "thresholds.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_el_archivo_del_repositorio_tiene_las_seis_senales_con_version():
    thresholds = get_thresholds()
    assert thresholds.version
    assert tuple(thresholds.signals) == P0_SIGNALS
    assert (thresholds.favorable, thresholds.moderate) == (70, 40)


def test_cada_fuente_de_los_umbrales_esta_en_sources():
    """R8: lo que cita `thresholds.yaml` está en las fuentes que publica el catálogo o, la del mercado, cuyos cortes
    salen de los datos de SIPSA (HU-073), en las que publica su adaptador en el dataset del repositorio."""
    _, _, sources = catalog.build(catalog.load())
    from_catalog = set(sources["source_id"].to_list())
    published = set(pl.read_parquet(build.PUBLISHED / "sources.parquet")["source_id"].to_list())
    assert get_thresholds().source_ids() <= from_catalog | {"dane_sipsa"}
    assert "dane_sipsa" in published


def test_el_suelo_nunca_es_critico_y_lo_que_no_tiene_fuente_no_se_califica():
    signals = get_thresholds().signals
    assert signals["soil"].critical_below is None  # R10
    assert signals["heat"].curve == FROM_CROP and signals["soil"].curve == FROM_CROP
    # Oferta: ninguna fuente dice sus cortes, así que no hay curva ni umbral (R1, R8).
    assert not signals["supply"].available
    assert (signals["supply"].critical_below, signals["supply"].source_id) == (None, None)
    assert all(signals[s].available and signals[s].source_id for s in ("water", "frost", "heat", "soil", "market"))


def test_el_umbral_critico_cae_en_la_curva_donde_dice_la_fuente():
    """Agua: menos de 50 % es pérdida (WRSI) y es crítica. Heladas: más de 40 % de los años es crítica (ZARC)."""
    signals = get_thresholds().signals
    assert dict(signals["water"].curve)[50] == signals["water"].critical_below == 20
    assert dict(signals["frost"].curve)[40] == signals["frost"].critical_below == 40


def test_la_curva_de_mercado_se_ancla_a_cuantiles_de_sipsa_y_solo_el_extremo_es_critico():
    """Mercado (HU-073): 0 en 0,85 (crítica), 40 en 0,91 (P25), 70 en 1,0 (el precio promedio, P50) y 100 en 1,15.
    Crítica solo con calificación 0, como el calor: un precio bajo fuerza el rojo solo en el extremo de la historia."""
    market = get_thresholds().signals["market"]
    assert market.curve == ((0.85, 0.0), (0.91, 40.0), (1.0, 70.0), (1.15, 100.0))
    assert market.critical_below == 1
    assert market.source_id == "dane_sipsa"


def test_los_cortes_de_mercado_siguen_siendo_coherentes_con_el_indice_publicado():
    """R8: los cortes se recalculan desde `market_price_season` publicado: P10 <= 0,85 <= P50; 0,91 a +-0,01 de P25;
    1,0 a +-0,02 de P50 (el índice está normalizado al promedio del producto); P50 <= 1,15 <= P90. Si el dataset
    cambia y dejan de cumplirse, hay que revisar la curva de `market` en `thresholds.yaml` (y su nota)."""
    index = pl.read_parquet(build.PUBLISHED / "market_price_season.parquet")["seasonal_index"].drop_nulls()
    p10, p25, p50, p90 = (index.quantile(q, "linear") for q in (0.1, 0.25, 0.5, 0.9))
    curve = dict((score, value) for value, score in get_thresholds().signals["market"].curve)
    where = f"P10={p10:.4f}, P25={p25:.4f}, P50={p50:.4f}, P90={p90:.4f}: revisar la curva de `market` en thresholds.yaml"
    assert p10 <= curve[0.0] <= p50, where
    assert abs(curve[40.0] - p25) <= 0.01, where
    assert abs(curve[70.0] - p50) <= 0.02, where
    assert p50 <= curve[100.0] <= p90, where


def test_un_archivo_bien_formado_se_lee(tmp_path):
    thresholds = load_thresholds(write(tmp_path, GOOD))
    assert thresholds.version == "9.9.9"
    assert thresholds.signals["water"].curve == ((0.0, 0.0), (100.0, 100.0))
    assert thresholds.source_ids() == {"s"}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ((MARKET, MARKET + "  otra: {variable: x, unit: x, curve: null}\n"), "no son del P0"),
        ((MARKET, ""), "faltan"),
        (("curve: [[0, 0], [100, 100]]", "curve: [[100, 0], [0, 100]]"), "orden creciente"),
        (("curve: [[0, 0], [100, 100]]", "curve: [[0, 0], [100, 120]]"), "0 a 100"),
        (("curve: [[0, 0], [100, 100]]", "curve: [[0, 0]]"), "dos puntos"),
        (("critical_below: 20, source_id: s}", "critical_below: 20, source_id: null}"), "no cita su fuente"),
        (("critical_below: 20, source_id: s}", "critical_below: null, source_id: s}"), "le falta `critical_below`"),
        (("curve: crop, critical_below: null", "curve: crop, critical_below: 5"), "R10"),
        (('unit: "%", curve: [[0, 0], [100, 100]]', 'unit: "%", curve: crop'), "solo heat, soil"),
        ((SUPPLY_NULL, SUPPLY_NULL.replace("critical_below: null", "critical_below: 30")), "deben ser nulos"),
        (("moderate: 40", "moderate: 80"), "menor que `levels.favorable`"),
        (('version: "9.9.9"', "version: 1"), "version"),
    ],
)
def test_un_archivo_que_no_cumple_su_forma_no_se_lee(tmp_path, change, message):
    old, new = change
    assert GOOD.count(old) >= 1
    with pytest.raises(ThresholdsError, match=message):
        load_thresholds(write(tmp_path, GOOD.replace(old, new, 1)))


def test_sin_el_archivo_dice_que_falta(tmp_path):
    with pytest.raises(ThresholdsError, match="No existe"):
        load_thresholds(tmp_path / "thresholds.yaml")
