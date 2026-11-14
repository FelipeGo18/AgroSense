"""Señal de calor (HU-190; specs/01-reglas.md, «Cómo se califica cada señal»). Los umbrales y las fichas del maíz son
los reales (`thresholds.yaml`, `catalog/crops.yaml`); las máximas por mes son de prueba (R5). Es historia de la zona,
nunca un pronóstico (decisión 4)."""

from datetime import date

import polars as pl
import pytest

from backend.config.thresholds import load_thresholds
from backend.engine.heat_signal import HeatMonth, heat_signal
from backend.engine.sensitive_signal import ClimateNormal, ClimateSignalResult, months_phrase
from backend.engine.signal_score import AVAILABLE, FAVORABLE, INSUFFICIENT_DATA, MODERATE, UNFAVORABLE
from backend.engine.stages import NOT_APPLICABLE, StageSpan, WindowMonth, crop_window
from pipeline import catalog

CROP = "la papa"
LIMITS = {"temp_opt_max_c": 25.0, "heat_max_c": 30.0}
NORMAL = ClimateNormal(1991, 2020, 24)

# Sembrando el 3 de agosto: agosto no es sensible; septiembre, octubre (etapa media) y noviembre (final) sí.
STAGES = [
    StageSpan("initial", 29, heat_sensitive=False),
    StageSpan("mid", 61, heat_sensitive=True),
    StageSpan("late", 30, heat_sensitive=True),
]
WINDOW = crop_window(STAGES, date(2026, 8, 3))


def months(**values: float | None) -> dict[int, HeatMonth]:
    """Filas `ok` por mes: `m9=22.0` es septiembre con 22 °C."""
    return {int(key[1:]): HeatMonth(value, "ok") for key, value in values.items()}


# Agosto (no sensible) es el más caliente: no cuenta.
TMAX = months(m8=40.0, m9=22.0, m10=27.5, m11=24.0)


@pytest.fixture(scope="module")
def thresholds():
    return load_thresholds()


def test_manda_el_mes_sensible_mas_caliente(thresholds):
    """Octubre, 27,5 °C: 100 · (30 − 27,5) / (30 − 25) = 50, moderada."""
    result = heat_signal(WINDOW, TMAX, LIMITS, NORMAL, thresholds, CROP)
    assert (result.status, result.score, result.level, result.critical) == (AVAILABLE, 50, MODERATE, False)
    assert result.indicators == ("tmax_p90_c",)
    assert result.reasons == (
        "De 1991 a 2020, de septiembre a noviembre (la etapa media y la etapa final), la máxima rara vez pasó de 27,5 °C "
        "(el mes más caluroso, octubre); la papa aguanta hasta 30 °C",
    )
    assert result.limitations == ()


def test_un_mes_sin_dato_no_cuenta_va_a_las_limitaciones_y_la_razon_no_lo_nombra(thresholds):
    """R5: la razón nombra solo los meses que se evaluaron (septiembre y noviembre), no el rango de la ventana."""
    without_october = {month: row for month, row in TMAX.items() if month != 10}
    result = heat_signal(WINDOW, without_october, LIMITS, NORMAL, thresholds, CROP)
    assert (result.score, result.level) == (100, FAVORABLE)
    assert result.limitations == ("Sin temperatura máxima de la zona en octubre: ese mes no se evaluó para el calor",)
    assert result.reasons == (
        "De 1991 a 2020, en septiembre y noviembre (la etapa media y la etapa final), la máxima rara vez pasó de 24 °C "
        "(el mes más caluroso, noviembre); la papa aguanta hasta 30 °C",
    )


@pytest.mark.parametrize("row", [HeatMonth(None, "ok"), HeatMonth(float("nan"), "ok"), HeatMonth(float("nan"), "partial")])
def test_un_mes_nulo_o_nan_es_sin_dato(thresholds, row):
    """El motor decide qué fila sirve: la API pasa las filas como están (R1)."""
    result = heat_signal(WINDOW, {**TMAX, 10: row}, LIMITS, NORMAL, thresholds, CROP)
    assert (result.score, result.level) == (100, FAVORABLE)
    assert result.limitations == ("Sin temperatura máxima de la zona en octubre: ese mes no se evaluó para el calor",)


def test_un_mes_partial_no_cuenta_aunque_sea_el_mas_caliente(thresholds):
    result = heat_signal(WINDOW, {**TMAX, 10: HeatMonth(29.9, "partial")}, LIMITS, NORMAL, thresholds, CROP)
    assert (result.score, result.level) == (100, FAVORABLE)
    assert result.limitations == (
        "La temperatura máxima de la zona en octubre tiene menos años que los que pide el periodo: ese mes no se evaluó para el calor",
    )
    assert "octubre" not in result.reasons[0]


def test_sin_ventana_es_sin_datos(thresholds):
    """Un cultivo sin etapas (el descanso) no tiene ventana: sin datos, nunca un error (R1)."""
    result = heat_signal(None, TMAX, LIMITS, NORMAL, thresholds, CROP)
    assert (result.status, result.level, result.score, result.critical) == (INSUFFICIENT_DATA, None, None, False)
    assert result.reasons == ("Sin las etapas de la papa: la señal no se evalúa",)


def test_sensible_en_todas_las_etapas_dice_todo_el_cultivo(thresholds):
    window = crop_window([StageSpan("initial", 29, heat_sensitive=True), StageSpan("mid", 61, heat_sensitive=True)], date(2026, 8, 3))
    result = heat_signal(window, TMAX, LIMITS, NORMAL, thresholds, CROP)
    assert result.reasons[0].startswith("De 1991 a 2020, en todo el cultivo (de agosto a octubre), la máxima rara vez pasó de 40 °C ")


def test_una_ventana_de_mas_de_doce_meses_no_repite_meses(thresholds):
    """La tabla es climatológica: octubre sin dato se dice una vez, aunque la ventana pase dos veces por él."""
    window = crop_window([StageSpan("mid", 450, heat_sensitive=True)], date(2026, 8, 3))
    rows = {month: HeatMonth(20.0, "ok") for month in range(1, 13) if month != 10}
    result = heat_signal(window, rows, LIMITS, NORMAL, thresholds, CROP)
    assert result.limitations == ("Sin temperatura máxima de la zona en octubre: ese mes no se evaluó para el calor",)
    assert "(el mes más caluroso, agosto)" in result.reasons[0]


def test_una_ventana_de_mas_de_doce_meses_dice_hasta_donde_llega(thresholds):
    """Del 3 de agosto de 2026 a octubre de 2027, todo sensible y con dato: la frase dice el mes final con su año
    (no «de agosto a julio», que sale de los meses sin repetir), y el máximo no cuenta dos veces un mes (R5)."""
    window = crop_window([StageSpan("mid", 450, heat_sensitive=True)], date(2026, 8, 3))
    rows = {month: HeatMonth(26.0 if month == 3 else 20.0, "ok") for month in range(1, 13)}
    result = heat_signal(window, rows, LIMITS, NORMAL, thresholds, CROP)
    assert result.reasons == (
        "De 1991 a 2020, en todo el cultivo (de agosto a octubre del año siguiente), la máxima rara vez pasó de 26 °C "
        "(el mes más caluroso, marzo); la papa aguanta hasta 30 °C",
    )
    assert result.limitations == ()


def test_una_ventana_que_empieza_en_enero(thresholds):
    """Sembrando el 5 de enero: la etapa inicial (enero y febrero) y la media (febrero a abril) son sensibles; la final
    (abril y mayo) no. Ningún mes pasa de diciembre: mayo, el más caluroso, no cuenta."""
    stages = [
        StageSpan("initial", 29, heat_sensitive=True),
        StageSpan("mid", 61, heat_sensitive=True),
        StageSpan("late", 30, heat_sensitive=False),
    ]
    window = crop_window(stages, date(2026, 1, 5))
    assert [(month.year, month.month) for month in window.sensitive_months("heat").months] == [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]
    result = heat_signal(window, months(m1=22.0, m2=24.0, m3=27.5, m4=23.0, m5=40.0), LIMITS, NORMAL, thresholds, CROP)
    assert (result.score, result.level, result.critical) == (50, MODERATE, False)
    assert result.reasons == (
        "De 1991 a 2020, de enero a abril (la etapa inicial y la etapa media), la máxima rara vez pasó de 27,5 °C "
        "(el mes más caluroso, marzo); la papa aguanta hasta 30 °C",
    )


def test_meses_sensibles_no_seguidos_se_nombran_uno_por_uno(thresholds):
    """Sembrando el 1 de octubre: octubre (etapa inicial) y diciembre (etapa media) son sensibles; noviembre (desarrollo)
    no. La frase no dice «de octubre a diciembre», que incluiría un mes que no se evaluó (R5)."""
    stages = [
        StageSpan("initial", 31, heat_sensitive=True),
        StageSpan("development", 30, heat_sensitive=False),
        StageSpan("mid", 31, heat_sensitive=True),
    ]
    window = crop_window(stages, date(2026, 10, 1))
    result = heat_signal(window, months(m10=24.0, m11=40.0, m12=26.0), LIMITS, NORMAL, thresholds, CROP)
    assert (result.score, result.level) == (80, FAVORABLE)
    assert result.reasons == (
        "De 1991 a 2020, en octubre y diciembre (la etapa inicial y la etapa media), la máxima rara vez pasó de 26 °C "
        "(el mes más caluroso, diciembre); la papa aguanta hasta 30 °C",
    )


def test_sin_ningun_mes_con_dato_es_sin_datos(thresholds):
    result = heat_signal(WINDOW, months(m8=40.0), LIMITS, NORMAL, thresholds, CROP)
    assert (result.status, result.level, result.score, result.critical) == (INSUFFICIENT_DATA, None, None, False)
    assert result.reasons[0] in result.limitations


@pytest.mark.parametrize(
    "limits",
    [
        {"temp_opt_max_c": 25.0, "heat_max_c": None},
        {"temp_opt_max_c": 25.0},
        {"heat_max_c": 30.0},
        {"temp_opt_max_c": None, "heat_max_c": 30.0},
        {"temp_opt_max_c": float("nan"), "heat_max_c": 30.0},
    ],
)
def test_sin_los_limites_de_la_ficha_es_sin_datos(thresholds, limits):
    """No culpa solo a `heat_max_c`: puede faltar cualquiera de los dos límites (R1, R8)."""
    result = heat_signal(WINDOW, TMAX, limits, NORMAL, thresholds, CROP)
    assert (result.status, result.level, result.score) == (INSUFFICIENT_DATA, None, None)
    assert result.reasons == (
        "Los límites de temperatura de la ficha de la papa (temp_opt_max_c y heat_max_c) no están completos "
        "con fuente: el calor no se califica",
    )
    assert result.reasons[0] in result.limitations


def test_en_el_maximo_que_aguanta_es_critica(thresholds):
    result = heat_signal(WINDOW, months(m9=30.0), LIMITS, NORMAL, thresholds, CROP)
    assert (result.score, result.level, result.critical) == (0, UNFAVORABLE, True)


def test_no_aplica_y_sin_datos_por_la_sensibilidad(thresholds):
    not_sensitive = crop_window([StageSpan("initial", 30, heat_sensitive=False)], date(2026, 8, 3))
    assert heat_signal(not_sensitive, TMAX, LIMITS, NORMAL, thresholds, CROP) == ClimateSignalResult(
        NOT_APPLICABLE, None, False, None, (), ("Según su ficha, ninguna etapa de la papa es sensible al calor",)
    )
    unknown = crop_window([StageSpan("initial", 30, heat_sensitive=False), StageSpan("mid", 30)], date(2026, 8, 3))
    assert heat_signal(unknown, TMAX, LIMITS, NORMAL, thresholds, CROP).status == INSUFFICIENT_DATA


def test_los_meses_sin_dato_de_sensibilidad_no_se_evaluan(thresholds):
    """Septiembre sin sensibilidad con fuente: su máxima, por alta que sea, no cambia el resultado."""
    stages = [StageSpan("initial", 29, heat_sensitive=False), StageSpan("development", 30), StageSpan("mid", 30, heat_sensitive=True)]
    window = crop_window(stages, date(2026, 8, 3))
    hot_september = heat_signal(window, {**TMAX, 9: HeatMonth(45.0, "ok")}, LIMITS, NORMAL, thresholds, CROP)
    assert hot_september == heat_signal(window, TMAX, LIMITS, NORMAL, thresholds, CROP)


def test_maiz_con_el_limite_del_catalogo_real(thresholds):
    """El `heat_max_c` del maíz es 35 °C (daño del polen, Purdue) y `temp_opt_max_c` 33: con 34 °C en la floración, 50."""
    crops, stages, _ = catalog.build(catalog.load())
    maize = crops.filter(pl.col("crop_id") == "maiz").row(0, named=True)
    assert (maize["temp_opt_max_c"], maize["heat_max_c"]) == (33, 35)
    spans = [
        StageSpan(row["stage"], row["days"], heat_sensitive=row["heat_sensitive"])
        for row in stages.filter(pl.col("crop_id") == "maiz").iter_rows(named=True)
    ]
    window = crop_window(spans, date(2026, 8, 3))
    sensitive = window.sensitive_months("heat").months
    result = heat_signal(window, {month.month: HeatMonth(34.0, "ok") for month in sensitive}, maize, NORMAL, thresholds, "el maíz")
    assert (result.score, result.level, result.critical) == (50, MODERATE, False)
    assert result.reasons[0].endswith("el maíz aguanta hasta 35 °C")


def test_es_determinista(thresholds):
    first = heat_signal(WINDOW, TMAX, LIMITS, NORMAL, thresholds, CROP)
    assert first == heat_signal(WINDOW, dict(TMAX), dict(LIMITS), NORMAL, thresholds, CROP)


def _months(*year_months: tuple[int, int]) -> list[WindowMonth]:
    return [WindowMonth(year, month, 30, (), ()) for year, month in year_months]


@pytest.mark.parametrize(
    ("year_months", "phrase"),
    [
        ([(2026, 12)], "diciembre"),
        ([(2026, 11), (2026, 12), (2027, 1)], "de noviembre a enero"),
        ([(2026, 10), (2026, 12)], "octubre y diciembre"),
        # Once meses: ningún nombre se repite, no hace falta el año.
        ([(2026, 8 + i) if i < 5 else (2027, i - 4) for i in range(11)], "de agosto a junio"),
        # Quince meses seguidos: el mes final se dice con su año.
        ([(2026, 8 + i) if i < 5 else (2027, i - 4) for i in range(15)], "de agosto a octubre del año siguiente"),
        # De noviembre de 2026 a febrero de 2028.
        (
            [(2026, 11), (2026, 12)] + [(2027, m) for m in range(1, 13)] + [(2028, 1), (2028, 2)],
            "de noviembre a febrero de dos años después",
        ),
        # No seguidos y de más de doce meses: cada mes que repetiría un nombre lleva su año.
        (
            [(2026, 8), (2026, 10), (2027, 3), (2027, 8), (2027, 9)],
            "agosto, octubre, marzo, agosto del año siguiente y septiembre del año siguiente",
        ),
    ],
)
def test_la_frase_de_meses_va_en_orden_cronologico_con_su_ano(year_months, phrase):
    """`months_phrase` es la de heladas y calor: una ventana de más de un año no se dice como si cupiera en uno (R5)."""
    assert months_phrase(_months(*year_months)) == phrase
