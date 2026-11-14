"""Balance hídrico por etapa y por mes (M7, HU-144). Las cifras de clima y de etapas son de ejemplo (R5)."""

from datetime import date

import pytest

from backend.engine import water_balance as wb
from backend.engine.stages import AVAILABLE, INSUFFICIENT_DATA, StageSpan, crop_window
from pipeline import catalog

# Una ventana de ejemplo sembrada el 1 de abril: 30 días en abril y 10 en mayo.
STAGES = [
    StageSpan("initial", 10, kc=0.5),
    StageSpan("development", 10, kc=None),
    StageSpan("mid", 10, kc=1.0),
    StageSpan("late", 10, kc=0.6),
]
WINDOW = crop_window(STAGES, date(2027, 4, 1))
ROOT = wb.RootZone(0.4, 0.6, 0.5)


def climate(april_rain: float | None, may_rain: float | None, dry_factor: float = 1.0) -> dict[int, wb.MonthClimate]:
    """ET0 de 1 mm al día en abril (30 mm) y en mayo (31 mm)."""

    def month(et0, rain):
        return wb.MonthClimate(et0, rain, None if rain is None else rain * dry_factor)

    return {4: month(30.0, april_rain), 5: month(31.0, may_rain)}


@pytest.mark.parametrize(("rain", "expected"), [(100, 55.0), (75, 35.0), (50, 20.0), (10, 0.0), (0, 0.0)])
def test_la_lluvia_efectiva_es_la_del_manual_de_la_fao(rain, expected):
    assert wb.effective_rain_mm(rain) == pytest.approx(expected)


def test_lo_que_necesita_el_cultivo_sigue_el_kc_de_cada_etapa():
    result = wb.water_balance(WINDOW, climate(0.0, 0.0))
    april, may = result.months
    # Abril: inicial 10 × 0,5; desarrollo en recta de 0,5 a 1,0 (10 × 0,5 + 0,5 × 5,5); media 10 × 1,0.
    # Se publica con un decimal.
    assert april.need_mm == pytest.approx(5 + 7.75 + 10, abs=0.06)
    # Mayo: la final en recta de 1,0 a 0,6.
    assert may.need_mm == pytest.approx(10 - 0.4 * 5.5, abs=0.05)
    assert (april.stages, may.stages, may.days) == (("initial", "development", "mid"), ("late",), 10)


def test_sin_lluvia_el_deficit_es_todo_lo_que_necesita():
    result = wb.water_balance(WINDOW, climate(0.0, 0.0), "franco", ROOT)
    assert result.deficit_mm["normal"] == (result.need_mm, result.need_mm)
    assert result.covered_pct() == (0.0, 0.0)


def test_un_suelo_arenoso_da_un_deficit_mayor_o_igual_que_uno_arcilloso():
    # Abril llueve de más y mayo nada: lo que guarda el suelo en abril se gasta en mayo.
    rain = climate(200.0, 0.0)
    sandy = wb.water_balance(WINDOW, rain, "arenoso", ROOT)
    clayey = wb.water_balance(WINDOW, rain, "arcilloso", ROOT)
    for year in wb.YEARS:
        assert sandy.deficit_mm[year][0] >= clayey.deficit_mm[year][0]
        assert sandy.deficit_mm[year][1] >= clayey.deficit_mm[year][1]
    assert clayey.deficit_mm["normal"] == (0.0, 0.0)
    assert sandy.deficit_mm["normal"][1] > 0


def test_el_rango_va_de_la_raiz_y_el_agua_mas_altas_a_las_mas_bajas():
    # Arena: de 0,01 a 0,03 m³/m³; raíz de 0,4 a 0,6 m; p = 0,5: guarda de 2 a 9 mm.
    assert wb.storable_mm("arenoso", ROOT) == pytest.approx((2.0, 9.0))
    # Abril llena el suelo; mayo necesita 7,8 mm y no llueve: con 9 mm guardados no falta nada, con 2 faltan 5,8.
    result = wb.water_balance(WINDOW, climate(200.0, 0.0), "arenoso", ROOT)
    assert result.deficit_mm["normal"] == pytest.approx((0.0, 5.8), abs=0.06)


def test_sin_textura_o_sin_raiz_no_hay_agua_guardada_y_se_dice():
    rain = climate(200.0, 0.0)
    plain = wb.water_balance(WINDOW, rain)
    assert not plain.retention and not wb.water_balance(WINDOW, rain, "franco", None).retention
    assert wb.water_balance(WINDOW, rain, "franco", ROOT).retention
    may = plain.months[1]
    assert may.deficit_mm["normal"] == (may.need_mm, may.need_mm)


def test_el_ano_seco_da_un_deficit_mayor_o_igual_que_el_normal():
    result = wb.water_balance(WINDOW, climate(40.0, 60.0, dry_factor=0.5), "franco", ROOT)
    assert result.deficit_mm["dry"][0] >= result.deficit_mm["normal"][0]
    assert result.deficit_mm["dry"][1] >= result.deficit_mm["normal"][1]
    assert result.months[0].rain_mm == {"normal": 40.0, "dry": 20.0}


def test_sin_kc_de_una_etapa_no_hay_balance():
    stages = [StageSpan("initial", 10, kc=None), StageSpan("mid", 10, kc=1.0)]
    result = wb.water_balance(crop_window(stages, date(2027, 4, 1)), climate(0.0, 0.0))
    assert (result.status, result.reason, result.deficit_mm) == (INSUFFICIENT_DATA, wb.KC_MISSING, {"normal": None, "dry": None})


def test_un_mes_sin_lluvia_no_tiene_deficit_y_el_total_tampoco():
    result = wb.water_balance(WINDOW, climate(50.0, None), "franco", ROOT)
    april, may = result.months
    assert april.status == AVAILABLE and april.deficit_mm["normal"] is not None
    assert may.status == INSUFFICIENT_DATA and may.deficit_mm == {"normal": None, "dry": None}
    assert result.deficit_mm == {"normal": None, "dry": None} and result.status == INSUFFICIENT_DATA
    assert result.covered_pct() is None


def test_un_mes_sin_et0_no_tiene_lo_que_necesita():
    rain = climate(50.0, 50.0)
    rain[5] = wb.MonthClimate(None, 50.0, 50.0)
    result = wb.water_balance(WINDOW, rain)
    assert result.months[1].need_mm is None and result.need_mm is None and result.status == INSUFFICIENT_DATA


def test_misma_entrada_mismo_resultado():
    rain = climate(120.0, 30.0, dry_factor=0.6)
    assert wb.water_balance(WINDOW, rain, "franco arcilloso", ROOT) == wb.water_balance(WINDOW, rain, "franco arcilloso", ROOT)


def test_el_volumen_es_el_deficit_por_el_area():
    assert wb.volume_m3((10.0, 20.0), 2.0) == (200.0, 400.0)
    assert wb.volume_m3(None, 2.0) is None


def test_la_cobertura_del_ano_seco_es_un_rango():
    result = wb.water_balance(WINDOW, climate(80.0, 10.0, dry_factor=0.5), "franco", ROOT)
    low, high = result.covered_pct()
    assert 0 <= low <= high <= 100


def test_el_agua_disponible_cubre_las_doce_clases_de_textura_del_usda():
    # Las clases del triángulo del USDA con los nombres del IGAC, las de `texture_class` (HU-181).
    assert set(wb.AVAILABLE_WATER) == {
        "arenoso", "arenoso franco", "franco arenoso", "franco", "franco limoso", "limoso", "franco arcillo arenoso",
        "franco arcilloso", "franco arcillo limoso", "arcillo arenoso", "arcillo limoso", "arcilloso",
    }  # fmt: skip
    assert all(0 < low <= high < 1 for low, high in wb.AVAILABLE_WATER.values())


def test_las_fuentes_del_metodo_estan_en_el_catalogo():
    known = {source["source_id"] for source in catalog.load()["sources"]}
    assert set(wb.SOURCE_IDS.values()) <= known


def test_la_raiz_de_cada_cultivo_sale_de_su_ficha():
    crops, _, _ = catalog.build(catalog.load())
    roots = {row["crop_id"]: wb.root_zone(row) for row in crops.to_dicts()}
    assert roots["papa"] == wb.RootZone(0.4, 0.6, 0.35)
    assert roots["descanso"] is None
    assert all(root is not None for crop_id, root in roots.items() if crop_id != "descanso")
