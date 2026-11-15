"""El precio de la cosecha en el orden de las ventanas (HU-240, decisión 17; specs/01-reglas.md, «Orden de las
ventanas»).

Con peso 4 o 5 en `market`, dentro de la decena del factor limitante va primero la ventana cuyo mes de cosecha estuvo
más años por encima del promedio de su año; en empate, la de mayor índice; las que no tienen historia, al final de su
decena. Con peso de 0 a 3 el orden es el de HU-192. El precio nunca saca a una ventana de su decena, nunca sube una de
alto riesgo y nunca cambia la luz (R2).
"""

from dataclasses import replace
from datetime import date, timedelta

import pytest

from backend.engine.market_signal import CROP_OVERRIDE, PriceHistory
from backend.engine.signal_score import SignalScore
from backend.engine.traffic_light import traffic_light
from backend.engine.window_order import WindowSignals, best_windows, order_windows, price_order_limitation
from tests.engine.test_orden_ventanas import SIGNALS, sig

# El mercado sin calificar (decisión 17): disponible, sin calificación. No cuenta para el factor limitante.
UNRATED = SignalScore("available", None, None, False)
WEIGHTS_3 = {**dict.fromkeys(SIGNALS, 3), "market": 3}
WEIGHTS_4 = {**WEIGHTS_3, "market": 4}

# Diciembre en Corabastos (2021–2025): 3 de 5 años por encima, índice 1,07.
DECEMBER = PriceHistory(
    market_id="1",
    market="Corabastos (Bogotá)",
    market_basis=CROP_OVERRIDE,
    product_id="papa-negra",
    month=12,
    seasonal_index=1.07,
    years=5,
    years_above=3,
    years_below=2,
    first_year=2021,
    last_year=2025,
    source_id="dane_sipsa",
)
# Septiembre: 0 de 5 por encima, índice 0,774.
SEPTEMBER = replace(DECEMBER, month=9, seasonal_index=0.774, years_above=0, years_below=5)


def window(month: int, score: int, price: PriceHistory | None, *, critical_frost: bool = False, weighted_bonus: int = 0) -> WindowSignals:
    """Una ventana con todas las señales de clima y suelo en `score` (la helada, crítica si se pide) y el mercado sin
    calificar con la historia `price`. `weighted_bonus` sube el agua para dar un promedio ponderado más alto sin cambiar
    el factor limitante."""
    start = date(2027, month, 1)
    signals = {
        "water": sig(min(score + weighted_bonus, 100)),
        "frost": sig(25, critical=True) if critical_frost else sig(score),
        "heat": sig(score),
        "soil": sig(score),
        "supply": SignalScore("insufficient_data", None, None, False),
        "market": UNRATED,
    }
    return WindowSignals(start, start + timedelta(days=150), signals, price)


def starts(ranked) -> list[date]:
    return [w.sowing_start for w in ranked]


def test_dos_ventanas_de_la_misma_decena_se_invierten_al_pasar_el_peso_de_3_a_4():
    # Septiembre tiene mejor promedio ponderado; diciembre, mejor precio.
    by_average = window(1, 72, SEPTEMBER, weighted_bonus=20)
    by_price = window(2, 72, DECEMBER)

    assert starts(order_windows([by_average, by_price], WEIGHTS_3)) == [by_average.sowing_start, by_price.sowing_start]
    assert starts(order_windows([by_average, by_price], WEIGHTS_4)) == [by_price.sowing_start, by_average.sowing_start]
    assert starts(order_windows([by_average, by_price], {**WEIGHTS_3, "market": 5})) == [by_price.sowing_start, by_average.sowing_start]


@pytest.mark.parametrize("weight", [0, 1, 2, 3])
def test_con_peso_de_0_a_3_el_orden_es_el_de_hoy(weight):
    windows = [window(1, 72, SEPTEMBER, weighted_bonus=20), window(2, 72, DECEMBER), window(3, 72, None, weighted_bonus=10)]
    weights = {**WEIGHTS_3, "market": weight}
    without_price = [replace(w, harvest_price=None) for w in windows]
    assert order_windows(windows, weights) == order_windows(without_price, weights)


def test_el_peso_por_defecto_de_agrosense_no_ordena_por_precio():
    windows = [window(1, 72, SEPTEMBER, weighted_bonus=20), window(2, 72, DECEMBER)]
    weights = {**WEIGHTS_3, "market": 1}
    assert starts(order_windows(windows, weights))[0] == date(2027, 1, 1)


def test_en_empate_de_anos_gana_el_mayor_indice_y_despues_el_promedio():
    lower_index = window(1, 72, replace(DECEMBER, seasonal_index=1.02), weighted_bonus=20)
    higher_index = window(2, 72, DECEMBER)
    same_price = window(3, 72, DECEMBER, weighted_bonus=10)

    ranked = order_windows([lower_index, higher_index, same_price], WEIGHTS_4)

    # Mismo 3 de 5: gana el índice 1,07 sobre 1,02; entre las dos con 1,07, el promedio ponderado.
    assert starts(ranked) == [same_price.sowing_start, higher_index.sowing_start, lower_index.sowing_start]


def test_cuenta_anos_como_fraccion_no_promedia_el_indice():
    """3 de 5 (60 %) va antes que 2 de 4 (50 %), aunque el índice de la segunda sea más alto."""
    three_of_five = window(1, 72, replace(DECEMBER, seasonal_index=1.01))
    two_of_four = window(2, 72, replace(DECEMBER, seasonal_index=1.12, years=4, years_above=2, years_below=2))
    assert starts(order_windows([two_of_four, three_of_five], WEIGHTS_4)) == [three_of_five.sowing_start, two_of_four.sowing_start]


def test_sin_historia_va_despues_de_las_que_la_tienen_en_su_decena():
    no_history = window(1, 72, None, weighted_bonus=20)
    no_counts = window(2, 72, replace(DECEMBER, years_above=None, years_below=None), weighted_bonus=20)
    worst_price = window(3, 72, SEPTEMBER)

    ranked = order_windows([no_history, no_counts, worst_price], WEIGHTS_4)

    assert starts(ranked) == [worst_price.sowing_start, no_history.sowing_start, no_counts.sowing_start]


def test_el_precio_no_saca_a_una_ventana_de_su_decena():
    upper = window(1, 85, SEPTEMBER)
    lower = window(2, 72, DECEMBER)
    assert starts(order_windows([lower, upper], WEIGHTS_4)) == [upper.sowing_start, lower.sowing_start]


def test_una_de_alto_riesgo_con_el_mejor_precio_sigue_al_final_y_no_entra_en_las_mejores():
    risky = window(1, 90, replace(DECEMBER, years_above=5, years_below=0), critical_frost=True)
    plain = window(2, 45, SEPTEMBER)

    ranked = order_windows([risky, plain], WEIGHTS_4)

    assert starts(ranked) == [plain.sowing_start, risky.sowing_start]
    assert ranked[-1].high_risk
    assert starts(best_windows(ranked)) == [plain.sowing_start]


def test_el_precio_no_cambia_el_factor_limitante_ni_el_promedio():
    price, no_price = window(1, 72, DECEMBER), window(1, 72, None)
    ranked_price, ranked_none = order_windows([price], WEIGHTS_4)[0], order_windows([no_price], WEIGHTS_4)[0]
    assert ranked_price == ranked_none


def test_el_precio_no_cambia_la_luz():
    """La luz no recibe la historia del precio: con el mercado sin calificar, la misma ventana da la misma luz con
    cualquier peso en `market` (R2)."""
    signals = window(1, 72, DECEMBER).signals
    lights = {traffic_light("suitable", signals, {**WEIGHTS_3, "market": weight}, "farmer").light for weight in range(6)}
    assert len(lights) == 1


def test_mismo_dato_mismo_orden_sin_importar_la_entrada():
    """R4."""
    windows = [window(1, 72, SEPTEMBER, weighted_bonus=20), window(2, 72, DECEMBER), window(3, 72, None), window(4, 85, None)]
    assert order_windows(windows, WEIGHTS_4) == order_windows(list(reversed(windows)), WEIGHTS_4)


@pytest.mark.parametrize("weight", [0, 1, 2, 3])
def test_sin_peso_alto_no_hay_limitacion_del_precio(weight):
    assert price_order_limitation({**WEIGHTS_3, "market": weight}) is None


@pytest.mark.parametrize("weight", [4, 5])
def test_con_peso_alto_la_limitacion_dice_por_que_cambia_el_orden(weight):
    """Una ventana con menos calificación puede ir primero: la respuesta lo dice (R5; revisión del PR #176)."""
    text = price_order_limitation({**WEIGHTS_3, "market": weight})
    assert text.startswith(f"Con el mercado en {weight}, ")
    assert "menos calificación puede ir antes" in text and "alto riesgo" in text
