"""Los umbrales de las señales (`thresholds.yaml`, HU-075): su forma, sus fuentes y lo que la API no deja pasar."""

import pytest

from backend.config.thresholds import FROM_CROP, ThresholdsError, get_thresholds, load_thresholds
from backend.config.weights import P0_SIGNALS
from pipeline import catalog

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


def test_cada_fuente_de_los_umbrales_esta_en_sources(tmp_path):
    """R8: lo que cita `thresholds.yaml` está en las fuentes que publica el catálogo."""
    _, _, sources = catalog.build(catalog.load())
    assert get_thresholds().source_ids() <= set(sources["source_id"].to_list())


def test_el_suelo_nunca_es_critico_y_lo_que_no_tiene_fuente_no_se_califica():
    signals = get_thresholds().signals
    assert signals["soil"].critical_below is None  # R10
    assert signals["heat"].curve == FROM_CROP and signals["soil"].curve == FROM_CROP
    # Oferta y mercado: ninguna fuente dice sus cortes, así que no hay curva ni umbral (R1, R8).
    for signal in ("supply", "market"):
        assert not signals[signal].available
        assert (signals[signal].critical_below, signals[signal].source_id) == (None, None)
    assert all(signals[s].available and signals[s].source_id for s in ("water", "frost", "heat", "soil"))


def test_el_umbral_critico_cae_en_la_curva_donde_dice_la_fuente():
    """Agua: menos de 50 % es pérdida (WRSI) y es crítica. Heladas: más de 40 % de los años es crítica (ZARC)."""
    signals = get_thresholds().signals
    assert dict(signals["water"].curve)[50] == signals["water"].critical_below == 20
    assert dict(signals["frost"].curve)[40] == signals["frost"].critical_below == 40


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
