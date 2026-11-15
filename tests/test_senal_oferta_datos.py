"""Los datos de la señal de oferta (HU-072): el semestre de EVA en que cae la siembra, leído del dataset publicado."""

from dataclasses import replace
from datetime import date

import pytest

from backend.api.supply_signal import semester_of, supply_in, supply_semester
from backend.dataset import load
from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA
from pipeline.build import PUBLISHED


@pytest.fixture(scope="module")
def published():
    return load(PUBLISHED)


def test_el_semestre_sale_de_la_fecha_de_siembra():
    assert [semester_of(date(2027, m, 1)) for m in (1, 6, 7, 12)] == ["A", "A", "B", "B"]


def test_lee_el_ultimo_ano_con_dato_de_ese_semestre(published):
    """Papa en 15238 (Duitama), con los datos publicados: 2025 B, 10 ha, −40 %, preliminar."""
    semester = supply_semester(published, "15238", "papa", date(2027, 8, 2), "eva")
    assert (semester.year, semester.semester, semester.planted_ha, semester.planted_change_pct, semester.preliminary) == (
        2025,
        "B",
        10.0,
        -40.0,
        True,
    )
    assert semester.same_as_previous is True  # 2024 B también fue 10 ha


def test_la_senal_con_dato_es_disponible_sin_calificar(published):
    result = supply_in(published, "15238", "papa", published.crops["papa"], date(2027, 3, 1))
    assert (result.status, result.level, result.score) == (AVAILABLE, None, None)
    assert result.reasons[1].startswith("En 2025 A (último dato, preliminar) EVA registra 20 ha de papa en su municipio")


def test_sin_dato_de_la_fuente_es_sin_datos(published):
    """Otra fuente no la reemplaza (R1)."""
    assert supply_semester(published, "15238", "papa", date(2027, 8, 2), "otra_fuente") is None
    assert supply_in(published, "15238", "avena_vicia", published.crops["avena_vicia"], date(2027, 8, 2)).status == INSUFFICIENT_DATA
    assert supply_in(published, "15238", "papa", published.crops["papa"], None).status == INSUFFICIENT_DATA
    assert supply_semester(replace(published, supply_semester=None), "15238", "papa", date(2027, 8, 2), "eva") is None


def test_la_misma_consulta_da_la_misma_senal(published):
    first = supply_in(published, "15238", "papa", published.crops["papa"], date(2027, 8, 2))
    assert all(supply_in(published, "15238", "papa", published.crops["papa"], date(2027, 8, 2)) == first for _ in range(3))
