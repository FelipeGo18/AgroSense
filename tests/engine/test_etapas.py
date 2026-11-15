"""La etapa por calendario (HU-220)."""

from datetime import date, timedelta

from backend.engine.stages import StageSpan, stage_today

# Papa: FAO-56, fila «Idaho, USA» (catalog/crops.yaml).
PAPA = [StageSpan("initial", 45), StageSpan("development", 30), StageSpan("mid", 70), StageSpan("late", 20)]
SOWN = date(2026, 8, 2)


def test_el_dia_de_la_siembra_es_el_comienzo_de_la_etapa_inicial():
    state = stage_today(PAPA, SOWN, SOWN)
    assert (state.stage, state.stage_progress_pct, state.days_since_sowing) == ("initial", 0.0, 0)
    assert state.harvest_estimate == SOWN + timedelta(days=165)
    assert state.stage_method == "calendar" and not state.harvest_due


def test_cada_etapa_empieza_el_dia_que_termina_la_anterior():
    assert stage_today(PAPA, SOWN, SOWN + timedelta(days=44)).stage == "initial"
    assert stage_today(PAPA, SOWN, SOWN + timedelta(days=45)).stage == "development"
    middle = stage_today(PAPA, SOWN, SOWN + timedelta(days=75 + 35))
    assert (middle.stage, middle.stage_progress_pct) == ("mid", 50.0)


def test_pasada_la_cosecha_estimada_queda_en_la_ultima_etapa_y_lo_dice():
    state = stage_today(PAPA, SOWN, SOWN + timedelta(days=200))
    assert (state.stage, state.stage_progress_pct, state.harvest_due) == ("late", 100.0, True)


def test_sin_etapas_no_hay_etapa_ni_cosecha_estimada():
    state = stage_today([], SOWN, SOWN + timedelta(days=10))
    assert (state.stage, state.harvest_estimate, state.days_since_sowing) == (None, None, 10)


def test_mismos_datos_mismo_resultado():
    assert stage_today(PAPA, SOWN, date(2026, 10, 1)) == stage_today(PAPA, SOWN, date(2026, 10, 1))
