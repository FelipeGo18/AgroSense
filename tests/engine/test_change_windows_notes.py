"""Revisión del PR #142: avisos juntados por meses y la razón de un periodo sin ventanas buenas. Cifras de ejemplo."""

from datetime import date

from backend.engine.change_windows import _no_best_windows_reason, merge_month_notes
from backend.engine.changes import Period
from backend.engine.signal_score import SignalScore
from backend.engine.window_order import WindowSignals, order_windows

WEIGHTS = {"water": 3, "frost": 3, "heat": 3, "soil": 3, "supply": 3, "market": 3}
POWER = Period("p2", 2005, 2024, "nasa_power")
IMERG = Period("p2", 2013, 2024, "imerg")


def test_junta_los_avisos_que_solo_cambian_en_los_meses():
    notes = [
        "2005–2024: Sin dato del calor (marzo y agosto): no se evaluaron",
        "Otro aviso",
        "2005–2024: Sin dato del calor (febrero y julio): no se evaluaron",
        "1981–2000: Sin dato del calor (marzo y agosto): no se evaluaron",
        "Otro aviso",
        "Un aviso (con paréntesis que no son meses)",
    ]
    assert merge_month_notes(notes) == [
        "2005–2024: Sin dato del calor (febrero, marzo, julio y agosto): no se evaluaron",
        "Otro aviso",
        "1981–2000: Sin dato del calor (marzo y agosto): no se evaluaron",
        "Un aviso (con paréntesis que no son meses)",
    ]


def _window(month, **signals):
    return WindowSignals(date(2005, month, 1), date(2005, month, 28), signals)


def _grave():
    return SignalScore("available", 0, "unfavorable", True)


def _ok():
    return SignalScore("available", 90, "favorable", False)


def test_razon_con_todas_las_ventanas_de_alto_riesgo():
    candidates = [_window(m, water=_ok(), heat=_grave(), frost=_grave() if m <= 3 else _ok()) for m in range(1, 13)]
    ranked = order_windows(candidates, WEIGHTS)
    assert _no_best_windows_reason(ranked, candidates, WEIGHTS, POWER, IMERG) == (
        "En 2005–2024 los 12 meses de siembra son de alto riesgo: el calor es crítico en todos y la helada en 3. "
        "El calor de NASA POWER puede salir más alto que el real en tierra caliente: vea las limitaciones."
    )


def test_razon_solo_por_agua_usa_el_periodo_de_la_lluvia():
    candidates = [_window(m, water=_grave()) for m in range(1, 7)] + [_window(m) for m in range(7, 13)]
    ranked = order_windows(candidates, WEIGHTS)
    assert _no_best_windows_reason(ranked, candidates, WEIGHTS, POWER, IMERG) == (
        "En 2013–2024 ninguna ventana queda entre las mejores: 6 de los 12 meses de siembra son de alto riesgo "
        "(el agua es crítica en 6) y 6 no tienen señales con datos para calificar."
    )
