"""El diagnóstico de una ventana en el motor (HU-076, `backend/engine/diagnosis.py`): las dos luces, las limitaciones y
con qué pesos se buscan las mejores ventanas. Las señales son DE PRUEBA (R5): solo su estado, nivel y razones."""

from dataclasses import dataclass

from backend.engine.diagnosis import IRRIGATION_UNKNOWN, diagnose, evaluates_windows, irrigation_used
from backend.engine.signal_score import AVAILABLE, FAVORABLE, INSUFFICIENT_DATA, UNFAVORABLE
from backend.engine.suitability import INSUFFICIENT_DATA as SUITABILITY_UNKNOWN
from backend.engine.suitability import NOT_SUITABLE, SUITABLE
from backend.engine.traffic_light import DEFAULT, FARMER, OTHER_WINDOW

WEIGHTS = {"water": 3, "frost": 3, "heat": 3, "soil": 2, "supply": 2, "market": 2}


@dataclass(frozen=True)
class FakeSignal:
    status: str
    score: int | None
    level: str | None
    critical: bool = False
    reasons: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


GOOD = FakeSignal(AVAILABLE, 90, FAVORABLE, reasons=("bien",))
NO_DATA = FakeSignal(INSUFFICIENT_DATA, None, None)


def signals(**changed: FakeSignal) -> dict[str, FakeSignal]:
    return {name: changed.get(name, GOOD) for name in WEIGHTS}


def run(signals_=None, *, level=SUITABLE, reasons=(), zone=None, irrigated=False, weights=WEIGHTS):
    return diagnose(level, reasons, zone, irrigated, signals_, weights, FARMER if weights is not WEIGHTS else DEFAULT, WEIGHTS)


def test_las_limitaciones_van_en_orden_fijo_y_sin_repetir():
    frost = FakeSignal(AVAILABLE, 90, FAVORABLE, reasons=("bien",), limitations=("Aviso de heladas", "Aviso común"))
    heat = FakeSignal(AVAILABLE, 90, FAVORABLE, reasons=("bien",), limitations=("Aviso común",))
    result = run(signals(frost=frost, heat=heat), zone="Temperatura del municipio", irrigated=None)
    assert result.limitations == ("Temperatura del municipio", IRRIGATION_UNKNOWN, "Aviso de heladas", "Aviso común")


def test_la_aptitud_sin_datos_va_a_las_limitaciones():
    result = run(signals(), level=SUITABILITY_UNKNOWN, reasons=("Sin la temperatura del municipio",))
    assert result.limitations[0] == "Sin la temperatura del municipio"


def test_el_riego_sin_dato_no_se_dice_si_el_cultivo_no_es_apto():
    """Sin ventana no se evaluó nada sin riego (regla 0)."""
    assert IRRIGATION_UNKNOWN not in run(None, level=NOT_SUITABLE, irrigated=None).limitations
    assert IRRIGATION_UNKNOWN in run(signals(), irrigated=None).limitations


def test_el_agua_el_suelo_y_la_oferta_sin_datos_dicen_su_propia_razon():
    """Su razón ya dice por qué no hay dato: no se agrega «Sin datos para la zona» (R5). Las demás sí lo llevan."""
    water = FakeSignal(INSUFFICIENT_DATA, None, None, reasons=("Sin la lluvia de la fuente",))
    soil = FakeSignal(INSUFFICIENT_DATA, None, None, reasons=("Sin pH para la zona",))
    supply = FakeSignal(INSUFFICIENT_DATA, None, None, reasons=("Esta versión todavía no evalúa la oferta.",))
    result = run(signals(water=water, soil=soil, supply=supply, frost=NO_DATA))
    assert "Sin la lluvia de la fuente" in result.limitations
    assert "Sin pH para la zona" in result.limitations
    assert "Esta versión todavía no evalúa la oferta." in result.limitations
    assert "Sin datos para la zona: la helada no se evaluó." in result.limitations
    assert not any(text.startswith("Sin datos para la zona: el agua") for text in result.limitations)


def test_sin_otra_ventana_en_ninguna_luz_no_se_buscan_mejores_ventanas():
    assert run(signals()).best_windows_weights is None


def test_las_mejores_ventanas_usan_los_pesos_de_la_luz_que_pide_otra_ventana():
    """Una helada crítica da `other_window` con cualquier peso: se usan los pesos de quien consulta. Si solo la luz de
    AgroSense lo pide, los de AgroSense."""
    frost = FakeSignal(AVAILABLE, 10, UNFAVORABLE, critical=True, reasons=("helada",))
    farmer = {**WEIGHTS, "water": 5}
    both = run(signals(frost=frost), weights=farmer)
    assert (both.overall.action, both.overall_default.action) == (OTHER_WINDOW, OTHER_WINDOW)
    assert both.best_windows_weights == farmer


def test_si_solo_la_luz_de_agrosense_pide_otra_ventana_se_usan_sus_pesos():
    """Con los pesos de AgroSense, agua y calor desfavorables (no críticos) dan rojo y `other_window`; quien consulta
    les pone 0 y su luz es verde: las mejores ventanas se buscan con los pesos de AgroSense."""
    water = FakeSignal(AVAILABLE, 30, UNFAVORABLE, reasons=("agua",))
    heat = FakeSignal(AVAILABLE, 30, UNFAVORABLE, reasons=("calor",))
    farmer = {**WEIGHTS, "water": 0, "heat": 0}
    result = run(signals(water=water, heat=heat), weights=farmer)
    assert result.overall.action != OTHER_WINDOW
    assert result.overall_default.action == OTHER_WINDOW
    assert result.best_windows_weights == WEIGHTS


def test_sin_senales_el_cultivo_no_apto_da_las_dos_luces_de_la_regla_0():
    result = run(None, level=NOT_SUITABLE)
    assert result.overall.action == result.overall_default.action == "rotate"
    assert result.best_windows_weights is None


def test_con_lote_el_riego_es_el_del_lote_aunque_no_lo_diga():
    """Contrato y EP-16: con lote, el del lote (nulo se evalúa como sin riego); sin lote, el de la consulta."""
    assert irrigation_used(True, True, False) is True
    assert irrigation_used(True, None, True) is None
    assert irrigation_used(False, None, True) is True


def test_la_ventana_no_se_evalua_con_un_cultivo_no_apto():
    assert evaluates_windows(SUITABLE) and evaluates_windows(SUITABILITY_UNKNOWN)
    assert not evaluates_windows(NOT_SUITABLE)
