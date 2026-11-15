"""Señal de agua (HU-071; specs/01-reglas.md, «Cómo se califica cada señal», «Agregación del semáforo», R1, R2, R5, R10).

Casos de referencia escritos antes del código (HU-121): fijan la interfaz de `backend/engine/water_signal.py`. Los
umbrales son los reales (`thresholds.yaml`, curva del WRSI de FEWS NET: [[0, 0], [50, 20], [60, 40], [80, 70],
[100, 100]], crítica por debajo de 20). Los balances (`WaterBalanceSummary`) y la fuente de lluvia de estas pruebas son
**de ejemplo**, elegidos para caer en cada tramo de la curva: no son datos de ninguna zona (R5).

La señal califica el porcentaje de lo que pide el cultivo que cubre la lluvia del **año seco** (`precip_dry_mm`, la que
se supera en 4 de cada 5 años), con el agua que guarda el suelo, y toma el extremo **bajo** del rango de cobertura: la
decisión prudente. Con riego, la falta de lluvia no es un riesgo: es `favorable` y la razón dice cuánto regar (R10).
Es historia de la zona, nunca un pronóstico (decisión 4).

R6: `tests/engine/test_r6.py` ya recorre todos los módulos de `backend/engine/` (por AST y en un intérprete limpio), así
que `water_signal.py` queda cubierto sin una prueba aparte.
"""

from datetime import date

import pytest

from backend.config.thresholds import load_thresholds
from backend.engine.sensitive_signal import ClimateSignalResult
from backend.engine.signal_score import AVAILABLE, FAVORABLE, INSUFFICIENT_DATA, MODERATE, UNFAVORABLE
from backend.engine.stages import StageSpan, crop_window
from backend.engine.water_notes import NO_RETENTION, RainSource, missing_data
from backend.engine.water_signal import INDICATOR, WaterBalanceSummary, water_signal

CROP = "la papa"
# Ejemplo (R5): el aviso de la fuente es una frase de prueba, no el `rain_caveat` real de `catalog/sources.yaml`.
EXAMPLE_CAVEAT = "AVISO DE EJEMPLO: esta lluvia de prueba sobrestima la de las estaciones."
EXAMPLE_RAIN = RainSource("GPM IMERG", 2001, 2024, EXAMPLE_CAVEAT)
EXAMPLE_RAIN_NO_CAVEAT = RainSource("GPM IMERG", 2001, 2024, None)

# Sembrando el 3 de agosto de 2026: 29 + 61 + 30 = 120 días, cosecha estimada el 1 de diciembre. La ventana toca de
# agosto a noviembre; diciembre no (el día de la cosecha no es de la ventana).
STAGES = [StageSpan("initial", 29, kc=0.5), StageSpan("mid", 61, kc=1.15), StageSpan("late", 30, kc=0.75)]
WINDOW = crop_window(STAGES, date(2026, 8, 3))

# Lo que pide el cultivo en la ventana, de ejemplo: con 400 mm, cada 4 mm de déficit es un punto de cobertura.
NEED = 400.0


def example_balance(deficit_min: float, deficit_max: float, need: float | None = NEED, retention: bool = True) -> WaterBalanceSummary:
    """Un balance de ejemplo (R5) con el déficit del año seco como rango [mín, máx]."""
    return WaterBalanceSummary(need_mm=need, dry_deficit_mm=(deficit_min, deficit_max), retention=retention)


def flat(coverage_pct: float) -> WaterBalanceSummary:
    """Un balance de ejemplo cuya cobertura es `coverage_pct` en los dos extremos."""
    deficit = NEED * (1 - coverage_pct / 100)
    return example_balance(deficit, deficit)


@pytest.fixture(scope="module")
def thresholds():
    return load_thresholds()


def signal(thresholds, balance, irrigated=False, rain=EXAMPLE_RAIN) -> ClimateSignalResult:
    return water_signal(balance, irrigated, rain, WINDOW, thresholds, CROP)


def test_la_ventana_de_las_pruebas_va_de_agosto_a_noviembre():
    """La premisa de las razones: los meses de la ventana son de agosto a noviembre de 2026."""
    assert [(month.year, month.month) for month in WINDOW.months()] == [(2026, 8), (2026, 9), (2026, 10), (2026, 11)]


# ---------- la cobertura del balance (la misma fórmula que `WaterBalance.covered_pct` de HU-144) ----------


@pytest.mark.parametrize(
    ("need", "deficit", "expected"),
    [
        (400.0, (80.0, 160.0), (60.0, 80.0)),
        (400.0, (0.0, 0.0), (100.0, 100.0)),
        # Un tercio de déficit: se redondea a un decimal.
        (300.0, (100.0, 100.0), (66.7, 66.7)),
        (300.0, (100.0, 150.0), (50.0, 66.7)),
        # Un déficit mayor que lo que pide el cultivo no da cobertura negativa: se queda en 0.
        (100.0, (50.0, 150.0), (0.0, 50.0)),
        (100.0, (120.0, 150.0), (0.0, 0.0)),
        # El cultivo no pide agua en la ventana: cubierto del todo, sin dividir por cero.
        (0.0, (0.0, 0.0), (100.0, 100.0)),
    ],
)
def test_la_cobertura_va_del_deficit_maximo_al_minimo(need, deficit, expected):
    """`low` sale del déficit máximo y `high` del mínimo: más déficit, menos cobertura."""
    assert WaterBalanceSummary(need, deficit, True).covered_pct() == expected


@pytest.mark.parametrize(
    "balance",
    [WaterBalanceSummary(None, (10.0, 20.0), True), WaterBalanceSummary(400.0, None, True), WaterBalanceSummary(None, None, False)],
)
def test_sin_lo_que_pide_el_cultivo_o_sin_deficit_no_hay_cobertura(balance):
    """R1: sin uno de los dos no se puede decir cuánto cubre la lluvia; nunca se supone 0 ni 100."""
    assert balance.covered_pct() is None


# ---------- sin datos (R1) ----------

NO_BALANCE = [
    pytest.param(None, id="sin_balance"),
    pytest.param(WaterBalanceSummary(None, (10.0, 20.0), True), id="sin_lo_que_pide_el_cultivo"),
    pytest.param(WaterBalanceSummary(NEED, None, True), id="sin_deficit"),
]


@pytest.mark.parametrize("balance", NO_BALANCE)
@pytest.mark.parametrize("irrigated", [False, None, True])
def test_sin_balance_el_agua_es_sin_datos_con_o_sin_riego(thresholds, balance, irrigated):
    """R1: sin balance no hay nivel ni calificación, y no es crítica. Con riego tampoco: sin balance no se puede decir
    cuánto regar. La razón dice que no hay con qué calcular el agua y va también a las limitaciones."""
    result = signal(thresholds, balance, irrigated)
    assert isinstance(result, ClimateSignalResult)
    assert (result.status, result.level, result.score, result.critical, result.indicators) == (INSUFFICIENT_DATA, None, None, False, ())
    assert len(result.reasons) == 1
    assert "agua" in result.reasons[0].lower()
    assert result.reasons[0] in result.limitations


def test_sin_balance_y_con_todos_los_datos_la_razon_dice_que_falta_el_balance(thresholds):
    """«Sin el balance hídrico…» es solo para cuando los datos están y falta el balance (R5)."""
    reason = signal(thresholds, None).reasons[0]
    assert reason.startswith("Sin el balance hídrico de la papa")
    assert "lluvia de" not in reason and "evapotranspiración" not in reason


# ---------- sin los datos del balance: la razón dice la causa real (R1, R5) ----------

AUGUST, SEPTEMBER, OCTOBER, NOVEMBER = WINDOW.months()


def test_missing_data_dice_los_meses_sin_lluvia_de_la_fuente_y_sin_et0():
    assert missing_data(EXAMPLE_RAIN, [], []) == ()
    assert missing_data(EXAMPLE_RAIN, [SEPTEMBER], [NOVEMBER]) == (
        "Sin la lluvia de GPM IMERG para la zona en septiembre: el agua no se evalúa, y no se usa otra fuente en su lugar",
        "Sin la evapotranspiración de referencia de la zona en noviembre: el agua no se evalúa",
    )
    # Un tramo de meses seguidos no lleva «en» delante.
    assert missing_data(EXAMPLE_RAIN, WINDOW.months(), [])[0].startswith("Sin la lluvia de GPM IMERG para la zona de agosto a noviembre:")


@pytest.mark.parametrize("irrigated", [False, None, True])
@pytest.mark.parametrize("balance", [None, flat(100)])
def test_sin_la_lluvia_de_la_fuente_la_razon_lo_dice_y_no_el_balance(thresholds, balance, irrigated):
    """Con datos faltantes, la señal es sin datos aunque llegue un balance (no se pudo pedir), y su razón es la primera
    causa; las demás y el aviso de la fuente van a las limitaciones."""
    missing = missing_data(EXAMPLE_RAIN, [SEPTEMBER], [NOVEMBER])
    result = water_signal(balance, irrigated, EXAMPLE_RAIN, WINDOW, thresholds, CROP, missing)
    assert (result.status, result.level, result.score, result.critical, result.indicators) == (INSUFFICIENT_DATA, None, None, False, ())
    assert result.reasons == (missing[0],)
    assert "balance hídrico" not in result.reasons[0]
    assert result.limitations == (missing[0], missing[1], EXAMPLE_CAVEAT)


def test_sin_la_et0_sola_la_razon_es_la_de_la_et0(thresholds):
    missing = missing_data(EXAMPLE_RAIN, [], [OCTOBER])
    result = water_signal(None, False, EXAMPLE_RAIN, WINDOW, thresholds, CROP, missing)
    assert result.reasons == ("Sin la evapotranspiración de referencia de la zona en octubre: el agua no se evalúa",)


def test_sin_faltantes_el_resultado_no_cambia(thresholds):
    assert water_signal(flat(70), False, EXAMPLE_RAIN, WINDOW, thresholds, CROP, ()) == signal(thresholds, flat(70))


# ---------- el aviso de la fuente de lluvia (rain_caveat) ----------


@pytest.mark.parametrize(
    ("balance", "irrigated"),
    [
        pytest.param(flat(80), False, id="calificada"),
        pytest.param(flat(40), True, id="con_riego"),
        pytest.param(None, False, id="sin_datos"),
        pytest.param(None, True, id="sin_datos_con_riego"),
    ],
)
def test_el_aviso_de_la_lluvia_va_siempre_en_las_limitaciones(thresholds, balance, irrigated):
    """HU-071: si `sources.yaml` trae `rain_caveat` para la región, la señal lo lleva en cada respuesta, se califique o
    no (como el `frost_caveat` de HU-077)."""
    assert EXAMPLE_CAVEAT in signal(thresholds, balance, irrigated).limitations


@pytest.mark.parametrize("irrigated", [False, True])
@pytest.mark.parametrize("balance", [flat(80), None])
def test_sin_aviso_de_la_fuente_no_hay_limitacion_de_aviso(thresholds, balance, irrigated):
    """Lo único que cambia entre una fuente con aviso y una sin él es el aviso: no se inventa otro."""
    with_caveat = signal(thresholds, balance, irrigated)
    without = signal(thresholds, balance, irrigated, rain=EXAMPLE_RAIN_NO_CAVEAT)
    assert EXAMPLE_CAVEAT not in without.limitations
    assert set(with_caveat.limitations) - set(without.limitations) == {EXAMPLE_CAVEAT}
    assert (without.status, without.level, without.score, without.critical) == (
        with_caveat.status, with_caveat.level, with_caveat.score, with_caveat.critical
    )  # fmt: skip


# ---------- sin riego: la curva del WRSI sobre el extremo bajo de la cobertura ----------


@pytest.mark.parametrize(
    ("coverage", "score", "level", "critical"),
    [
        (100, 100, FAVORABLE, False),
        (80, 70, FAVORABLE, False),
        (70, 55, MODERATE, False),
        (60, 40, MODERATE, False),
        (55, 30, UNFAVORABLE, False),
        # 20 no es crítica: crítica es por debajo de 20 (`critical_below`, estricto).
        (50, 20, UNFAVORABLE, False),
        (40, 16, UNFAVORABLE, True),
        (0, 0, UNFAVORABLE, True),
    ],
)
@pytest.mark.parametrize("irrigated", [False, None])
def test_sin_riego_la_calificacion_sale_de_la_curva(thresholds, coverage, score, level, critical, irrigated):
    """`irrigated` nulo se evalúa igual que sin riego (la limitación de riego la pone `/diagnostics`, no la señal)."""
    result = signal(thresholds, flat(coverage), irrigated)
    assert (result.status, result.score, result.level, result.critical) == (AVAILABLE, score, level, critical)
    assert result.indicators == (INDICATOR,) == ("water_deficit_mm",)
    assert len(result.reasons) == 1


def test_sin_riego_manda_el_extremo_bajo_de_la_cobertura(thresholds):
    """Cobertura de 60 a 80 %: la calificación es la de 60 (40, moderada), no la de 80 (70, favorable). Es la decisión
    prudente: el rango no compensa su peor caso (R2)."""
    balance = example_balance(80.0, 160.0)
    assert balance.covered_pct() == (60.0, 80.0)
    result = signal(thresholds, balance)
    assert (result.score, result.level) == (40, MODERATE)


def test_riego_nulo_no_agrega_una_limitacion_propia(thresholds):
    """La señal no duplica «Sin dato de riego»: la pone `/diagnostics` (HU-076). Nulo y falso dan lo mismo."""
    assert signal(thresholds, flat(70), None) == signal(thresholds, flat(70), False)


# ---------- con riego (R10) ----------


@pytest.mark.parametrize("coverage", [0, 40, 55, 80, 100])
def test_con_riego_el_agua_es_favorable_y_nunca_critica(thresholds, coverage):
    """Con riego, la falta de lluvia no es un riesgo: `favorable`, 100 y no crítica, por grande que sea el déficit."""
    result = signal(thresholds, flat(coverage), True)
    assert (result.status, result.level, result.score, result.critical) == (AVAILABLE, FAVORABLE, 100, False)
    assert result.indicators == (INDICATOR,)
    assert len(result.reasons) == 1


def test_caso_de_referencia_mismo_deficit_alto_sin_riego_desfavorable_y_con_riego_no(thresholds):
    """Caso de referencia de HU-071: la misma ventana con déficit alto da `unfavorable` sin riego y no da `unfavorable`
    con riego."""
    high_deficit = example_balance(300.0, 340.0)  # cobertura de 15 a 25 %
    dry = signal(thresholds, high_deficit, False)
    watered = signal(thresholds, high_deficit, True)
    assert (dry.level, dry.critical) == (UNFAVORABLE, True)
    assert watered.level != UNFAVORABLE
    assert (watered.level, watered.critical) == (FAVORABLE, False)


def test_con_riego_la_razon_dice_cuanto_regar_como_rango_y_que_es_una_estimacion(thresholds):
    """R10: el riego se dice como rango en milímetros enteros, con el rótulo de estimación y el periodo (R5)."""
    reason = signal(thresholds, example_balance(180.4, 219.6), True).reasons[0]
    assert "180" in reason and "220" in reason and "mm" in reason
    assert "180,4" not in reason and "219,6" not in reason
    assert "regar" in reason.lower() or "riego" in reason.lower()
    assert "estimación" in reason.lower()
    assert "2001" in reason and "2024" in reason


def test_con_riego_y_sin_deficit_dice_que_no_haria_falta_regar(thresholds):
    reason = signal(thresholds, example_balance(0.0, 0.0), True).reasons[0]
    assert "regar" in reason.lower() or "riego" in reason.lower()
    assert "no " in reason.lower()
    assert "de 0 a 0" not in reason


# ---------- la retención del suelo ----------


@pytest.mark.parametrize("irrigated", [False, True])
def test_sin_retencion_se_califica_igual_y_lo_dicen_las_limitaciones(thresholds, irrigated):
    """Sin la textura del suelo, el balance va sin retención y se dice; la señal no queda sin datos por eso."""
    result = signal(thresholds, example_balance(80.0, 80.0, retention=False), irrigated)
    assert result.status == AVAILABLE and result.score is not None
    assert NO_RETENTION in result.limitations
    assert isinstance(NO_RETENTION, str) and NO_RETENTION.strip()


def test_con_retencion_no_hay_limitacion_de_retencion(thresholds):
    assert NO_RETENTION not in signal(thresholds, example_balance(80.0, 80.0, retention=True)).limitations


# ---------- la razón (R5, R10, decisión 4) ----------


def test_la_razon_dice_ano_seco_fuente_periodo_cultivo_meses_cobertura_y_que_es_una_estimacion(thresholds):
    """Una sola razón con lo que se evaluó: el año seco (4 de cada 5), la fuente de la lluvia y su periodo, el cultivo,
    los meses de la ventana (sin nombrar un mes que no es de ella), el rango de cobertura en % enteros, y el rótulo de
    R10 (estimación; verificar la humedad del suelo en campo). No se fija la frase exacta."""
    balance = example_balance(100.0, 150.0, need=300.0)  # cobertura de 50 a 66,7 %
    result = signal(thresholds, balance)
    assert len(result.reasons) == 1
    reason = result.reasons[0]
    lower = reason.lower()
    assert "año seco" in lower
    assert "4 de cada 5" in reason
    assert "GPM IMERG" in reason
    assert "2001" in reason and "2024" in reason
    assert CROP in reason
    assert "agosto" in lower and "noviembre" in lower
    assert "diciembre" not in lower
    assert "50" in reason and "67" in reason and "%" in reason
    assert "66,7" not in reason
    assert "estimación" in lower
    assert "humedad del suelo" in lower


def test_la_razon_no_es_un_pronostico(thresholds):
    """Decisión 4: es historia de la zona."""
    for irrigated in (False, True):
        lower = signal(thresholds, flat(70), irrigated).reasons[0].lower()
        assert "pronóstico" not in lower and "lloverá" not in lower


# ---------- determinismo (R4) ----------


@pytest.mark.parametrize("irrigated", [False, None, True])
@pytest.mark.parametrize("balance", [None, flat(55), example_balance(80.0, 160.0, retention=False)])
def test_dos_llamadas_iguales_dan_lo_mismo(thresholds, balance, irrigated):
    assert signal(thresholds, balance, irrigated) == signal(thresholds, balance, irrigated)
