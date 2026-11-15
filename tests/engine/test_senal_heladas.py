"""Señal de heladas (HU-077; specs/02-contratos.md, «Heladas de una ventana»; specs/01-reglas.md, «Cómo se califica
cada señal»). Los umbrales son los reales de `thresholds.yaml`; las ventanas y las filas de heladas son casos armados a
mano (R5: cifras de prueba, no observadas). Es historia de la zona, nunca un pronóstico (decisión 4)."""

import re
from datetime import date

import pytest

from backend.config.thresholds import load_thresholds
from backend.engine.frost_signal import FrostMonth, frost_signal
from backend.engine.sensitive_signal import ClimateNormal, ClimateSignalResult
from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA, UNFAVORABLE
from backend.engine.stages import NOT_APPLICABLE, StageSpan, crop_window

FORECAST_WORDS = re.compile(r"\b(va a|irá|helará|estará|será|pronostic\w*|predic\w*|futur\w*)\b", re.IGNORECASE)
CAVEAT = "Aviso de prueba de la fuente de heladas"
CROP = "la papa"
NORMAL = ClimateNormal(first_year=2001, last_year=2010, min_years=5)

# Sembrando el 1 de noviembre: la etapa inicial (noviembre) no es sensible; la media (diciembre y enero del año
# siguiente) sí; la final (febrero) no lo dice con fuente: va a las limitaciones y no se evalúa.
STAGES = [
    StageSpan("initial", 30, frost_sensitive=False),
    StageSpan("mid", 62, frost_sensitive=True),
    StageSpan("late", 28, frost_sensitive=None),
]
WINDOW = crop_window(STAGES, date(2026, 11, 1))


@pytest.fixture(scope="module")
def thresholds():
    return load_thresholds()


def rows(**changes: FrostMonth | None) -> dict[tuple[int, int], FrostMonth]:
    """Todos los meses de 2001 a 2011 completos y sin helada, con los cambios (`y2003_12=None` quita la fila)."""
    table = {(year, month): FrostMonth(0, "ok") for year in range(2001, 2012) for month in range(1, 13)}
    for key, row in changes.items():
        year, month = (int(part) for part in key[1:].split("_"))
        if row is None:
            del table[(year, month)]
        else:
            table[(year, month)] = row
    return table


# El caso de referencia, a mano. Cada año Y cuenta diciembre de Y y enero de Y + 1:
# - 2001: heló en diciembre → con helada.
# - 2002: heló en enero de 2003 → con helada.
# - 2003: falta diciembre, pero heló en enero de 2004 → con helada (la helada está confirmada).
# - 2004: diciembre `partial` con 0 → no cuenta (falta dato y no heló).
# - 2005: falta enero de 2006 y diciembre tuvo 0 → no cuenta.
# - 2006: diciembre `partial` con 1 → con helada.
# - 2007 a 2010: completos y en 0 → sin helada.
# Además hiela en noviembre (no sensible) y en febrero (sin dato de sensibilidad) de todos los años: no cambia nada.
# Años que cuentan: 4 con helada + 4 sin helada = 8. frost_freq_pct = 100 · 4 / 8 = 50 %.
# Curva de heladas (0→100, 20→70, 40→40, 100→0): en 50, 40 − 10 · 40 / 60 = 33,3 → 33: desfavorable y crítica (< 40).
CASE = rows(
    y2001_12=FrostMonth(2, "ok"),
    y2003_1=FrostMonth(1, "ok"),
    y2003_12=None,
    y2004_1=FrostMonth(3, "ok"),
    y2004_12=FrostMonth(0, "partial"),
    y2006_1=None,
    y2006_12=FrostMonth(1, "partial"),
    **{f"y{year}_{month}": FrostMonth(5, "ok") for year in range(2001, 2012) for month in (2, 11)},
)


def test_cuenta_los_anos_con_helada_en_cualquiera_de_los_meses_sensibles(thresholds):
    result = frost_signal(WINDOW, CASE, NORMAL, thresholds, CROP)
    assert (result.status, result.score, result.level, result.critical) == (AVAILABLE, 33, UNFAVORABLE, True)
    assert result.indicators == ("frost_freq_pct",)
    assert result.reasons == (
        "Sembrando en noviembre, heló en la etapa media (de diciembre a enero) 50 de cada 100 años: "
        "en 4 de los 8 años con dato, sembrando de 2001 a 2010",
    )
    assert not FORECAST_WORDS.search(result.reasons[0])


def test_los_meses_sin_dato_de_sensibilidad_van_a_las_limitaciones_y_no_cambian_el_resultado(thresholds):
    result = frost_signal(WINDOW, CASE, NORMAL, thresholds, CROP)
    assert result.limitations == (
        "La ficha de la papa no dice con fuente si es sensible a la helada en la etapa final (febrero): ese mes no se evaluó",
    )
    without_february_frost = {key: FrostMonth(0, "ok") if key[1] == 2 else row for key, row in CASE.items()}
    assert frost_signal(WINDOW, without_february_frost, NORMAL, thresholds, CROP) == result


def test_sin_heladas_es_favorable_y_lo_dice(thresholds):
    result = frost_signal(WINDOW, rows(), NORMAL, thresholds, CROP)
    assert (result.status, result.score, result.level, result.critical) == (AVAILABLE, 100, "favorable", False)
    assert result.reasons == (
        "Sembrando en noviembre, no heló ningún año en la etapa media (de diciembre a enero), "
        "entre los 10 años con dato, sembrando de 2001 a 2010",
    )


def test_con_menos_anos_que_cuentan_que_los_que_pide_el_periodo_es_sin_datos(thresholds):
    """El caso de referencia tiene 8 años que cuentan: con un periodo que pide 9 no se califica (R1)."""
    result = frost_signal(WINDOW, CASE, ClimateNormal(2001, 2010, 9), thresholds, CROP)
    assert (result.status, result.level, result.score, result.critical, result.indicators) == (INSUFFICIENT_DATA, None, None, False, ())
    reason = (
        "Sin datos suficientes de heladas en la etapa media (de diciembre a enero): "
        "solo 8 de los 10 años, sembrando de 2001 a 2010, se pudieron contar y hacen falta 9"
    )
    assert result.reasons == (reason,)
    assert result.limitations[0] == reason


def test_sin_filas_es_sin_datos_y_no_divide_por_cero(thresholds):
    """Sin ningún año que cuente, aunque el periodo pida 1 (`min_years` mínimo): sin datos, nunca 0 / 0."""
    for normal in (NORMAL, ClimateNormal(2001, 2010, 1)):
        result = frost_signal(WINDOW, {}, normal, thresholds, CROP)
        assert (result.status, result.level, result.score) == (INSUFFICIENT_DATA, None, None)
        assert result.reasons == ("Sin datos de heladas del municipio en la etapa media (de diciembre a enero), sembrando de 2001 a 2010",)


def test_si_helo_todos_los_anos_lo_dice_sin_porcentaje(thresholds):
    all_frost = rows(**{f"y{year}_12": FrostMonth(1, "ok") for year in range(2001, 2011)})
    result = frost_signal(WINDOW, all_frost, NORMAL, thresholds, CROP)
    assert result.reasons == (
        "Sembrando en noviembre, heló todos los años en la etapa media (de diciembre a enero), "
        "entre los 10 años con dato, sembrando de 2001 a 2010",
    )


def test_sensible_en_todas_las_etapas_dice_todo_el_cultivo(thresholds):
    """Sembrando el 1 de diciembre con las dos etapas sensibles: «todo el cultivo», no la lista de etapas."""
    window = crop_window(
        [StageSpan("initial", 31, frost_sensitive=True), StageSpan("development", 31, frost_sensitive=True)], date(2026, 12, 1)
    )
    result = frost_signal(window, CASE, NORMAL, thresholds, CROP)
    assert result.reasons[0].startswith("Sembrando en diciembre, heló en todo el cultivo (de diciembre a enero) ")
    partly = crop_window(
        [StageSpan("initial", 31, frost_sensitive=False), StageSpan("development", 31, frost_sensitive=True)], date(2026, 12, 1)
    )
    assert "heló en la etapa de desarrollo (enero) " in frost_signal(partly, CASE, NORMAL, thresholds, CROP).reasons[0]


def test_una_ventana_que_empieza_en_enero_cuenta_los_meses_del_mismo_ano(thresholds):
    """Sembrando el 1 de enero, todo sensible (de enero a marzo): todo desfase es 0. Heló en enero de 2001, en marzo de
    2002 y en febrero de 2003 (`partial`, pero la helada está confirmada): 3 de 10 años, 30 %. Curva: 70 − 30 · 10 / 20
    = 55, moderada. La helada de enero de 2011 es del año 2011, fuera del periodo: no cuenta."""
    window = crop_window([StageSpan("initial", 31, frost_sensitive=True), StageSpan("mid", 59, frost_sensitive=True)], date(2026, 1, 1))
    table = rows(y2001_1=FrostMonth(1, "ok"), y2002_3=FrostMonth(2, "ok"), y2003_2=FrostMonth(1, "partial"), y2011_1=FrostMonth(4, "ok"))
    result = frost_signal(window, table, NORMAL, thresholds, CROP)
    assert (result.status, result.score, result.level, result.critical) == (AVAILABLE, 55, "moderate", False)
    assert result.reasons == (
        "Sembrando en enero, heló en todo el cultivo (de enero a marzo) 30 de cada 100 años: "
        "en 3 de los 10 años con dato, sembrando de 2001 a 2010",
    )


def test_con_la_tabla_terminando_en_el_ultimo_ano_ese_ano_solo_cuenta_si_helo(thresholds):
    """Sesgo conservador conocido (docs/registro-de-decisiones.md, «Años de una ventana»): la ventana de diciembre a
    enero del año 2010 lee enero de 2011. Si la tabla termina en 2010 (pasa con los datos de ejemplo), a ese año le
    falta enero: no cuenta si no heló en diciembre, y cuenta como año con helada si heló. El método no cambia."""
    until_last_year = {key: row for key, row in rows().items() if key[0] <= NORMAL.last_year}
    without_frost = frost_signal(WINDOW, until_last_year, NORMAL, thresholds, CROP)
    assert (without_frost.score, without_frost.level) == (100, "favorable")
    assert without_frost.reasons == (
        "Sembrando en noviembre, no heló ningún año en la etapa media (de diciembre a enero), "
        "entre los 9 años con dato, sembrando de 2001 a 2010",
    )
    with_frost = frost_signal(WINDOW, {**until_last_year, (2010, 12): FrostMonth(1, "ok")}, NORMAL, thresholds, CROP)
    assert with_frost.reasons == (
        "Sembrando en noviembre, heló en la etapa media (de diciembre a enero) 10 de cada 100 años: "
        "en 1 de los 10 años con dato, sembrando de 2001 a 2010",
    )


def test_sin_ventana_es_sin_datos_con_el_aviso(thresholds):
    """Un cultivo sin etapas (el descanso) no tiene ventana (`crop_window` da None): sin datos, nunca un error (R1)."""
    assert crop_window([], date(2026, 11, 1)) is None
    result = frost_signal(None, CASE, NORMAL, thresholds, CROP, CAVEAT)
    assert (result.status, result.level, result.score, result.critical) == (INSUFFICIENT_DATA, None, None, False)
    assert result.reasons == ("Sin las etapas de la papa: la señal no se evalúa",)
    assert result.limitations == (result.reasons[0], CAVEAT)


def test_sin_periodo_normal_es_sin_datos(thresholds):
    result = frost_signal(WINDOW, CASE, None, thresholds, CROP, CAVEAT)
    assert (result.status, result.level, result.score) == (INSUFFICIENT_DATA, None, None)
    assert CAVEAT in result.limitations


def test_no_aplica_si_ninguna_etapa_es_sensible(thresholds):
    window = crop_window([StageSpan("initial", 30, frost_sensitive=False), StageSpan("late", 30, frost_sensitive=False)], date(2026, 11, 1))
    result = frost_signal(window, CASE, NORMAL, thresholds, CROP, CAVEAT)
    assert result == ClimateSignalResult(
        NOT_APPLICABLE, None, False, None, (), ("Según su ficha, ninguna etapa de la papa es sensible a la helada",), (CAVEAT,)
    )


def test_sin_datos_si_ninguna_es_sensible_y_alguna_no_lo_dice(thresholds):
    """Nunca `not_applicable` si alguna etapa no lo dice con fuente (R1; Felipe, PR #69)."""
    window = crop_window([StageSpan("initial", 30, frost_sensitive=False), StageSpan("late", 30, frost_sensitive=None)], date(2026, 11, 1))
    result = frost_signal(window, CASE, NORMAL, thresholds, CROP)
    assert (result.status, result.level, result.score) == (INSUFFICIENT_DATA, None, None)
    assert result.reasons == ("La ficha de la papa no dice con fuente si alguna etapa es sensible a la helada: la señal no se evalúa",)


@pytest.mark.parametrize("normal", [NORMAL, ClimateNormal(2001, 2010, 9), None])
def test_el_aviso_de_la_fuente_va_en_toda_respuesta(thresholds, normal):
    assert CAVEAT in frost_signal(WINDOW, CASE, normal, thresholds, CROP, CAVEAT).limitations


def test_frecuencia_alta_es_critica_con_los_umbrales_reales(thresholds):
    """Más del 40 % de los años con helada queda fuera de lo que recomienda el ZARC: crítica (`critical_below` 40)."""
    all_frost = rows(**{f"y{year}_12": FrostMonth(1, "ok") for year in range(2001, 2011)})
    result = frost_signal(WINDOW, all_frost, NORMAL, thresholds, CROP)
    assert (result.score, result.level, result.critical) == (0, UNFAVORABLE, True)


def test_es_determinista(thresholds):
    """R4: mismos datos, misma salida."""
    first = frost_signal(WINDOW, CASE, NORMAL, thresholds, CROP, CAVEAT)
    assert first == frost_signal(WINDOW, dict(CASE), NORMAL, thresholds, CROP, CAVEAT)
