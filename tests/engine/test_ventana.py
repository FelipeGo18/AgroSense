"""La ventana de un cultivo por calendario (HU-220): sus etapas día a día, sus meses y los meses sensibles."""

from datetime import date, timedelta

import pytest

from backend.engine.stages import (
    AVAILABLE,
    FROST,
    HEAT,
    INSUFFICIENT_DATA,
    NOT_APPLICABLE,
    StageSpan,
    crop_window,
    stage_today,
)

# Papa: FAO-56, fila «Idaho, USA» (catalog/crops.yaml): 165 días, sensible a la helada en todas las etapas y sin el dato
# del calor.
PAPA = [
    StageSpan("initial", 45, kc=0.5, frost_sensitive=True),
    StageSpan("development", 30, frost_sensitive=True),
    StageSpan("mid", 70, kc=1.15, frost_sensitive=True),
    StageSpan("late", 20, kc=0.75, frost_sensitive=True),
]
SOWN = date(2026, 8, 2)


def with_sensitivity(frost, heat=(False, False, False, False)):
    return [StageSpan(span.stage, span.days, frost_sensitive=f, heat_sensitive=h) for span, f, h in zip(PAPA, frost, heat, strict=True)]


def test_un_cultivo_de_150_dias_sembrado_el_3_de_agosto_se_cosecha_el_31_de_diciembre():
    """El caso de referencia de la HU."""
    window = crop_window([StageSpan("initial", 50), StageSpan("mid", 50), StageSpan("late", 50)], date(2026, 8, 3))
    assert window.harvest_estimate == date(2026, 12, 31)
    assert (window.harvest_basis, window.length_days, window.last_day) == ("calendar", 150, date(2026, 12, 30))


def test_cada_etapa_empieza_el_dia_siguiente_al_fin_de_la_anterior():
    window = crop_window(PAPA, SOWN)
    assert [(p.span.stage, p.start, p.end) for p in window.periods] == [
        ("initial", date(2026, 8, 2), date(2026, 9, 15)),
        ("development", date(2026, 9, 16), date(2026, 10, 15)),
        ("mid", date(2026, 10, 16), date(2026, 12, 24)),
        ("late", date(2026, 12, 25), date(2027, 1, 13)),
    ]
    assert window.harvest_estimate == date(2027, 1, 14) == SOWN + timedelta(days=165)


def test_la_etapa_de_cada_dia_y_fuera_de_la_ventana_ninguna():
    window = crop_window(PAPA, SOWN)
    assert window.stage_on(SOWN).stage == "initial"
    assert window.stage_on(date(2026, 9, 15)).stage == "initial"
    assert window.stage_on(date(2026, 9, 16)).stage == "development"
    assert window.stage_on(date(2027, 1, 13)).stage == "late"
    # El día de la cosecha y el anterior a la siembra no son de la ventana.
    assert window.stage_on(date(2027, 1, 14)) is None and window.stage_on(date(2026, 8, 1)) is None
    # El Kc de la ficha viaja con la etapa, para el agua (HU-071).
    assert window.stage_on(date(2026, 11, 1)).kc == 1.15


def test_los_meses_de_una_ventana_que_pasa_de_diciembre_a_enero():
    months = crop_window(PAPA, SOWN).months()
    assert [(m.year, m.month, m.days) for m in months] == [
        (2026, 8, 30),
        (2026, 9, 30),
        (2026, 10, 31),
        (2026, 11, 30),
        (2026, 12, 31),
        (2027, 1, 13),
    ]
    assert sum(m.days for m in months) == 165
    assert months[1].stages == ("initial", "development")
    assert months[4].stages == ("mid", "late")
    assert months[5].stages == ("late",)


def test_meses_sensibles_a_la_helada_solo_en_la_etapa_media():
    window = crop_window(with_sensitivity(frost=(False, False, True, False)), SOWN)
    frost = window.sensitive_months(FROST)
    assert frost.status == AVAILABLE
    # La etapa media va del 16 de octubre al 24 de diciembre: octubre, noviembre y diciembre.
    assert [(m.year, m.month) for m in frost.months] == [(2026, 10), (2026, 11), (2026, 12)]


def test_papa_sensible_a_la_helada_en_todo_el_ciclo_mira_los_seis_meses():
    frost = crop_window(PAPA, SOWN).sensitive_months(FROST)
    assert frost.status == AVAILABLE and len(frost.months) == 6


def test_sin_ninguna_etapa_sensible_el_riesgo_no_aplica():
    window = crop_window(with_sensitivity(frost=(False, False, False, False)), SOWN)
    assert window.sensitive_months(FROST).status == NOT_APPLICABLE
    assert window.sensitive_months(FROST).months == ()


@pytest.mark.parametrize("frost", [(False, False, None, False), (None, None, None, None)])
def test_si_ninguna_etapa_es_sensible_y_alguna_no_lo_dice_no_se_puede_decir_que_no_aplica(frost):
    """R1: la helada de la zanahoria (no, nulo, no, no) no es «no aplica»: en el desarrollo no se sabe (PR #69)."""
    sensitive = crop_window(with_sensitivity(frost=frost), SOWN).sensitive_months(FROST)
    assert (sensitive.status, sensitive.months, sensitive.unknown) == (INSUFFICIENT_DATA, (), ())


def test_con_alguna_etapa_sensible_se_evaluan_esas_y_las_nulas_van_aparte():
    """Decidido por Felipe el 14 nov 2026: los meses sensibles se evalúan y los que solo tocan etapas nulas se dicen
    (`unknown`), para las limitaciones; nunca se rellenan con «no sensible» (R1)."""
    sensitive = crop_window(with_sensitivity(frost=(None, None, True, None)), SOWN).sensitive_months(FROST)
    assert sensitive.status == AVAILABLE
    assert sensitive.months and all(m.sensitive(FROST) for m in sensitive.months)
    assert sensitive.unknown and all(m.sensitive(FROST) is None for m in sensitive.unknown)
    assert not set(sensitive.months) & set(sensitive.unknown)


def test_una_etapa_nula_entre_sensibles_no_borra_la_senal():
    sensitive = crop_window(with_sensitivity(frost=(True, True, None, True)), SOWN).sensitive_months(FROST)
    assert sensitive.status == AVAILABLE
    assert sensitive.months


def test_sin_el_dato_del_calor_en_ninguna_etapa_la_senal_queda_sin_datos():
    """`PAPA` de estas pruebas no trae `heat_sensitive`: el calor es `insufficient_data` (R1)."""
    assert crop_window(PAPA, SOWN).sensitive_months(HEAT).status == INSUFFICIENT_DATA


def test_el_mes_dice_nulo_si_ninguna_etapa_es_sensible_y_alguna_no_lo_dice():
    months = crop_window(with_sensitivity(frost=(False, None, False, False)), SOWN).months()
    assert months[0].sensitive(FROST) is False  # agosto: solo la inicial, que no es sensible
    assert months[1].sensitive(FROST) is None  # septiembre: la inicial (no) y el desarrollo (sin dato)


def test_sin_etapas_o_con_una_etapa_sin_dias_no_hay_ventana():
    assert crop_window([], SOWN) is None
    assert crop_window([StageSpan("initial", 0), StageSpan("mid", 30)], SOWN) is None
    assert stage_today([StageSpan("initial", 0)], SOWN, SOWN).harvest_estimate is None


def test_un_riesgo_que_no_existe_es_un_error():
    with pytest.raises(ValueError, match="Riesgo desconocido"):
        crop_window(PAPA, SOWN).sensitive_months("granizo")


def test_la_etapa_de_hoy_y_la_ventana_dicen_lo_mismo():
    window = crop_window(PAPA, SOWN)
    for offset in (0, 44, 45, 120, 164):
        day = SOWN + timedelta(days=offset)
        assert stage_today(PAPA, SOWN, day).stage == window.stage_on(day).stage
        assert stage_today(PAPA, SOWN, day).harvest_estimate == window.harvest_estimate


def test_mismos_datos_mismo_resultado():
    assert crop_window(PAPA, SOWN) == crop_window(PAPA, SOWN)
    assert crop_window(PAPA, SOWN).months() == crop_window(PAPA, SOWN).months()


def test_con_el_catalogo_publicado_cada_cultivo_tiene_su_ventana(dataset):
    """Las etapas llegan del dataset con su Kc y su sensibilidad; el descanso no tiene ventana (su duración es otra)."""
    from backend.dataset import get_dataset

    stages = get_dataset().stages
    papa = crop_window(stages["papa"], SOWN)
    assert papa.length_days == sum(span.days for span in stages["papa"])
    assert papa.sensitive_months(FROST).status == AVAILABLE
    assert crop_window(stages.get("descanso", []), SOWN) is None


def test_una_siembra_el_29_de_febrero_cuenta_bien_los_dias():
    window = crop_window(PAPA, date(2028, 2, 29))
    assert window.harvest_estimate == date(2028, 8, 12)
    months = window.months()
    assert (months[0].year, months[0].month, months[0].days) == (2028, 2, 1)
    assert sum(m.days for m in months) == 165


def test_los_meses_sensibles_de_una_ventana_que_pasa_de_diciembre_a_enero():
    """Para contar las heladas por año (`climate_frost_month`), enero es del año siguiente."""
    window = crop_window(with_sensitivity(frost=(False, False, False, True)), SOWN)
    frost = window.sensitive_months(FROST)
    assert [(m.year, m.month) for m in frost.months] == [(2026, 12), (2027, 1)]
