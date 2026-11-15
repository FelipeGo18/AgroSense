"""Los datos de la señal de oferta (HU-072): el semestre de EVA en que cae la siembra, leído del dataset publicado."""

from dataclasses import replace
from datetime import date

import polars as pl
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


def test_un_area_menor_que_media_hectarea_no_se_dice_cero(published):
    """Haba en 15248, 2025 A: 0,1 ha. A entero diría «0 ha» cuando sí hubo siembra (R5; revisión del PR #174)."""
    result = supply_in(published, "15248", "haba", published.crops["haba"], date(2027, 3, 1))
    assert "EVA registra 0,1 ha de haba" in result.reasons[1]


def test_la_senal_con_dato_cita_su_fuente(published):
    """`signals.supply.sources`: el área de EVA que respalda la señal, para que la web cite la fuente (R8)."""
    result = supply_in(published, "15238", "papa", published.crops["papa"], date(2027, 8, 2))
    assert [(s.source_id, s.indicator, s.value, s.unit, s.period, s.preliminary, s.used) for s in result.sources] == [
        ("eva", "planted_ha", 10.0, "ha", "2025 B", True, True)
    ]
    assert not hasattr(supply_in(published, "15238", "avena_vicia", published.crops["avena_vicia"], date(2027, 8, 2)), "sources")


def test_menos_de_tres_semestres_anteriores_no_dice_los_tres(published):
    """Haba en 15001 (Tunja), 2025 B: la variación de HU-032 sale con menos de tres semestres B anteriores."""
    semester = supply_semester(published, "15001", "haba", date(2027, 8, 2), "eva")
    assert (semester.year, semester.planted_change_pct, semester.complete_baseline) == (2025, 100.0, False)
    reason = supply_in(published, "15001", "haba", published.crops["haba"], date(2027, 8, 2)).reasons[1]
    assert "el promedio de los semestres B anteriores con dato (menos de tres)" in reason and "los tres" not in reason


def test_la_base_completa_es_la_misma_que_marca_el_pipeline(published):
    """`complete_baseline` repite lo que el pipeline marca con `quality = partial` (contrato): si una de las dos
    definiciones cambia, esta prueba lo dice."""
    table = published.supply_semester.filter(pl.col("planted_ha").is_not_null() & (pl.col("source_id") == "eva"))
    last = table.sort("year").group_by(["municipality_id", "crop_id", "semester"]).agg(pl.all().last())
    for row in last.iter_rows(named=True):
        sowing = date(2027, 3 if row["semester"] == "A" else 8, 1)
        semester = supply_semester(published, row["municipality_id"], row["crop_id"], sowing, "eva")
        assert semester.complete_baseline is (row["quality"] == "ok"), row


def test_sin_el_mismo_semestre_del_ano_anterior_no_dice_si_se_repite(published):
    """Cebolla de bulbo en 15162, 2024 A: no hay 2023 A, así que `same_as_previous` es nulo y la razón no compara."""
    semester = supply_semester(published, "15162", "cebolla_bulbo", date(2027, 3, 1), "eva")
    assert (semester.year, semester.same_as_previous) == (2024, None)
    reason = supply_in(published, "15162", "cebolla_bulbo", published.crops["cebolla_bulbo"], date(2027, 3, 1)).reasons[1]
    assert "el mismo valor" not in reason
