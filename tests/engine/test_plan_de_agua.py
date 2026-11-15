"""El plan de agua de una finca o de un ciclo (M7, HU-146): por cultivo y por mes, y la finca sumada.

Las cifras de clima, de etapas y de humedad son de ejemplo (R5). El balance de cada mes es el de HU-144
(`backend/engine/water_balance.py`): aquí se prueba lo que el plan agrega encima (la etapa del mes, el volumen, la suma
de la finca, los huecos, la humedad para contrastar y las limitaciones), no otra cuenta del agua.
"""

from dataclasses import dataclass
from datetime import date

import pytest

from backend.engine import water_plan as wp
from backend.engine.signal_score import AVAILABLE, INSUFFICIENT_DATA
from backend.engine.stages import StageSpan, crop_window
from backend.engine.water_balance import DRY, NORMAL, YEARS, MonthClimate, RootZone, water_balance
from backend.engine.water_notes import NO_RETENTION, RainSource, missing_data

# 40 días desde el 1 de abril: en abril, 5 de inicial, 20 de desarrollo y 5 de media; en mayo, 5 de media y 5 finales.
STAGES = [
    StageSpan("initial", 5, kc=0.5),
    StageSpan("development", 20, kc=None),
    StageSpan("mid", 10, kc=1.1),
    StageSpan("late", 5, kc=0.7),
]
# Las cuatro etapas de 10 días: en abril empatan la inicial, el desarrollo y la media.
EVEN = [StageSpan("initial", 10, kc=0.5), StageSpan("development", 10), StageSpan("mid", 10, kc=1.0), StageSpan("late", 10, kc=0.6)]
ROOT = RootZone(0.4, 0.6, 0.5)
RAIN = RainSource("GPM IMERG", 2001, 2024, "Aviso de ejemplo de la lluvia")
APRIL, MAY = date(2027, 4, 1), date(2027, 5, 1)


def climate(**missing: str) -> dict[int, MonthClimate]:
    """Un año de ejemplo: ET0 de 120 mm al mes, 60 mm de lluvia normal y 30 en el año seco. `missing` quita de un mes
    («mayo») la lluvia (`rain`) o la ET0 (`et0`)."""
    months = {}
    names = {4: "abril", 5: "mayo", 6: "junio", 7: "julio"}
    for month in range(1, 13):
        what = missing.get(names.get(month, ""), "")
        et0 = None if what == "et0" else 120.0
        normal, dry = (None, None) if what == "rain" else (60.0, 30.0)
        months[month] = MonthClimate(et0, normal, dry)
    return months


# Las pruebas usan una finca de 1 ha: el área de cada cultivo en hectáreas es su porcentaje / 100.
FARM_HA = 1.0


def crop(crop_id: str = "papa", sowing: date = APRIL, area: float = 1.0, stages=STAGES, root=ROOT) -> wp.PlanCrop:
    return wp.PlanCrop(crop_id, f"la {crop_id}", "crop", area * 100, sowing, crop_window(stages, sowing), root)


def plan(*crops: wp.PlanCrop, texture: str | None = "franco", weather=None, moisture=(), farm_ha: float = FARM_HA) -> wp.WaterPlan:
    return wp.water_plan(list(crops), farm_ha, weather or climate(), texture, RAIN, moisture)


@dataclass(frozen=True)
class Moisture:
    """Una fuente de humedad del suelo de ejemplo, con la forma que lee el plan."""

    source_id: str
    indicator: str
    unit: str
    by_month: dict[int, float | None]


POWER = Moisture("nasa_power", "soil_wetness_root", "fracción", {month: 0.5 + month / 100 for month in range(1, 13)})


# ---------- por cultivo ----------


def test_cada_mes_trae_la_etapa_que_ocupa_la_mayor_parte_del_mes():
    april, may = plan(crop()).crops[0].months
    assert (april.year, april.month, april.stage) == (2027, 4, "development")
    assert (may.month, may.stage) == (5, "mid")


def test_si_dos_etapas_empatan_en_el_mes_gana_la_primera():
    april, may = plan(crop(stages=EVEN)).crops[0].months
    assert april.stage == "initial"
    assert may.stage == "late"


def test_cada_mes_es_el_del_balance_de_hu144_sin_otra_cuenta():
    result = plan(crop()).crops[0]
    balance = water_balance(crop_window(STAGES, APRIL), climate(), "franco", ROOT)
    assert [month.need_mm for month in result.months] == [month.need_mm for month in balance.months]
    assert [month.rain_mm for month in result.months] == [month.rain_mm for month in balance.months]
    assert [month.deficit_mm for month in result.months] == [month.deficit_mm for month in balance.months]
    assert all(month.status == AVAILABLE for month in result.months)
    assert (result.harvest_estimate, result.harvest_basis, result.sowing_date) == (date(2027, 5, 11), "calendar", APRIL)


def test_el_volumen_es_el_deficit_por_10_por_el_area():
    result = plan(crop(area=2.5)).crops[0]
    for month in result.months:
        for year in YEARS:
            low, high = month.deficit_mm[year]
            assert month.volume_m3[year] == pytest.approx((low * 25, high * 25), abs=0.06)
    balance = water_balance(crop_window(STAGES, APRIL), climate(), "franco", ROOT)
    for year in YEARS:
        low, high = balance.deficit_mm[year]
        assert result.total_volume_m3[year] == pytest.approx((low * 25, high * 25), abs=0.06)
        assert result.total_volume_m3[year][0] <= result.total_volume_m3[year][1]


def test_los_meses_dan_exacto_el_total_del_cultivo_y_de_la_finca():
    """Revisión del PR #135: el total era el déficit total del balance, redondeado aparte, y con una finca grande no
    daba la suma de sus meses. Con 10 ha, 0,1 mm son 1 m³, y una siembra a mitad de mes parte los meses: con el total
    viejo, la papa sembrada el 17 de abril (6 ha) descuadraba 6 m³."""
    result = plan(crop("papa", date(2027, 4, 17), 0.6), crop("arveja", MAY, 0.4), farm_ha=10.0)
    for year in YEARS:
        for one in result.crops:
            assert one.total_volume_m3[year] == wp._sum([month.volume_m3[year] for month in one.months])
        assert result.farm.total_volume_m3[year] == wp._sum([month.volume_m3[year] for month in result.farm.months])


def test_un_mes_sin_la_lluvia_de_la_fuente_es_sin_datos_con_nulos_y_el_total_es_nulo():
    result = plan(crop(), weather=climate(mayo="rain")).crops[0]
    april, may = result.months
    assert april.status == AVAILABLE and april.volume_m3[DRY] is not None
    assert may.status == INSUFFICIENT_DATA
    assert may.rain_mm == {NORMAL: None, DRY: None}
    assert may.deficit_mm == {NORMAL: None, DRY: None}
    assert may.volume_m3 == {NORMAL: None, DRY: None}
    # Lo que pide el cultivo sí se sabe: la ET0 del mes está (contrato: el ejemplo trae `need_mm`).
    assert may.need_mm is not None
    assert result.total_volume_m3 == {NORMAL: None, DRY: None}


def test_los_meses_sin_datos_van_a_las_limitaciones_con_el_texto_de_la_senal():
    result = plan(crop(), weather=climate(mayo="rain"))
    window = crop_window(STAGES, APRIL)
    (expected,) = missing_data(RAIN, [window.months()[1]], [])
    assert expected in result.limitations
    without_et0 = plan(crop(), weather=climate(abril="et0"))
    (expected,) = missing_data(RAIN, [], [window.months()[0]])
    assert expected in without_et0.limitations
    assert without_et0.crops[0].months[0].status == INSUFFICIENT_DATA


# ---------- la finca ----------


def test_la_finca_suma_los_cultivos_que_se_solapan_como_rango():
    papa, arveja = crop("papa", APRIL, 1.0), crop("arveja", MAY, 0.5)
    result = plan(papa, arveja)
    by_crop = {c.crop_id: {(m.year, m.month): m.volume_m3 for m in c.months} for c in result.crops}
    assert [(m.year, m.month) for m in result.farm.months] == [(2027, 4), (2027, 5), (2027, 6)]
    april, may, june = result.farm.months
    for year in YEARS:
        assert april.volume_m3[year] == by_crop["papa"][(2027, 4)][year]
        expected = tuple(round(a + b, 1) for a, b in zip(by_crop["papa"][(2027, 5)][year], by_crop["arveja"][(2027, 5)][year], strict=True))
        assert may.volume_m3[year] == pytest.approx(expected)
        assert june.volume_m3[year] == by_crop["arveja"][(2027, 6)][year]
        totals = [c.total_volume_m3[year] for c in result.crops]
        assert result.farm.total_volume_m3[year] == pytest.approx((totals[0][0] + totals[1][0], totals[0][1] + totals[1][1]))


def test_un_hueco_de_un_cultivo_deja_nulo_ese_mes_de_la_finca_y_su_total():
    papa, arveja = crop("papa", APRIL), crop("arveja", MAY)
    result = plan(papa, arveja, weather=climate(junio="rain"))
    april, may, june = result.farm.months
    assert june.volume_m3 == {NORMAL: None, DRY: None}
    # Los meses en que todos los cultivos tienen dato sí se suman.
    assert april.volume_m3[DRY] is not None and may.volume_m3[DRY] is not None
    assert result.farm.total_volume_m3 == {NORMAL: None, DRY: None}


# ---------- sin retención, sin etapas, sin Kc y descanso ----------


def test_siempre_dice_que_es_una_estimacion_y_trae_el_aviso_de_la_lluvia_sin_repetir():
    result = plan(crop("papa"), crop("arveja", MAY))
    assert result.limitations[0] == wp.ESTIMATE
    assert RAIN.caveat in result.limitations
    assert len(result.limitations) == len(set(result.limitations))


def test_sin_textura_la_limitacion_de_retencion_una_vez():
    result = plan(crop("papa"), crop("arveja", MAY), texture=None)
    assert result.limitations.count(NO_RETENTION) == 1
    assert result.soil_used is False
    with_texture = plan(crop("papa"), texture="franco")
    assert NO_RETENTION not in with_texture.limitations
    assert with_texture.soil_used is True


def test_con_textura_y_sin_la_raiz_de_un_cultivo_dice_de_que_cultivo():
    result = plan(crop("papa"), crop("arveja", MAY, root=None))
    assert wp.no_root_note("la arveja") in result.limitations
    assert NO_RETENTION not in result.limitations
    assert "la arveja" in wp.no_root_note("la arveja")
    # La papa sí usó la textura.
    assert result.soil_used is True


def test_sin_etapas_el_cultivo_no_tiene_meses_ni_cosecha_y_la_finca_queda_sin_total():
    sin_etapas = wp.PlanCrop("haba", "el haba", "crop", 100.0, APRIL, None, ROOT)
    result = plan(crop("papa"), sin_etapas)
    haba = result.crops[1]
    assert (haba.months, haba.harvest_estimate, haba.harvest_basis) == ((), None, None)
    assert haba.total_volume_m3 == {NORMAL: None, DRY: None}
    assert wp.no_window_note("el haba") in result.limitations
    # No se sabe en qué meses pide agua el haba: ningún mes de la finca se suma con ese hueco (R1).
    assert result.farm.total_volume_m3 == {NORMAL: None, DRY: None}
    assert all(month.volume_m3 == {NORMAL: None, DRY: None} for month in result.farm.months)


def test_sin_el_kc_de_una_etapa_no_hay_meses_y_la_finca_queda_sin_dato_en_sus_meses():
    sin_kc = [StageSpan("initial", 31, kc=None), StageSpan("development", 10), StageSpan("mid", 10, kc=1.0), StageSpan("late", 10)]
    result = plan(crop("papa", APRIL), crop("maiz", date(2027, 6, 1), stages=sin_kc))
    maiz = result.crops[1]
    assert maiz.months == ()
    assert maiz.harvest_estimate == crop_window(sin_kc, date(2027, 6, 1)).harvest_estimate
    assert maiz.harvest_basis == "calendar"
    assert wp.kc_missing_note("la maiz") in result.limitations
    by_month = {(m.year, m.month): m.volume_m3 for m in result.farm.months}
    # Abril y mayo solo tienen la papa; de junio en adelante falta el maíz.
    assert by_month[(2027, 4)][DRY] is not None
    assert by_month[(2027, 6)] == {NORMAL: None, DRY: None}
    assert result.farm.total_volume_m3 == {NORMAL: None, DRY: None}


def test_el_descanso_no_tiene_agua_ni_cambia_la_finca():
    descanso = wp.PlanCrop("descanso", "el descanso", wp.FALLOW, 100.0, APRIL, None, None)
    alone = plan(crop("papa"))
    result = plan(crop("papa"), descanso)
    rest = result.crops[1]
    assert (rest.months, rest.harvest_estimate, rest.harvest_basis) == ((), None, None)
    assert rest.total_volume_m3 == {NORMAL: None, DRY: None}
    assert wp.fallow_note("el descanso") in result.limitations
    # El descanso no es un dato que falta: la finca es la de la papa sola.
    assert result.farm == alone.farm
    assert wp.no_window_note("el descanso") not in result.limitations


def test_solo_un_descanso_no_tiene_meses_ni_total():
    result = plan(wp.PlanCrop("descanso", "el descanso", wp.FALLOW, 100.0, APRIL, None, None))
    assert result.farm.months == ()
    assert result.farm.total_volume_m3 == {NORMAL: None, DRY: None}
    assert result.soil_moisture == ()


# ---------- humedad del suelo para contrastar ----------


def test_la_humedad_trae_los_meses_de_las_ventanas_por_fuente_y_sin_repetir_mes():
    smap = Moisture("smap", "soil_moisture_surface", "m³/m³", {4: 0.31, 5: None})
    # Una siembra en diciembre: diciembre y enero del año siguiente; y otra en abril.
    december = crop("arveja", date(2026, 12, 1))
    result = plan(december, crop("papa", APRIL), moisture=(POWER, smap))
    readings = [(m.source_id, m.month) for m in result.soil_moisture]
    assert readings == [
        ("nasa_power", 12), ("nasa_power", 1), ("nasa_power", 4), ("nasa_power", 5),
        ("smap", 12), ("smap", 1), ("smap", 4), ("smap", 5),
    ]  # fmt: skip
    values = {(m.source_id, m.month): m for m in result.soil_moisture}
    assert values[("nasa_power", 4)].value == pytest.approx(0.54)
    assert (values[("nasa_power", 4)].indicator, values[("nasa_power", 4)].unit) == ("soil_wetness_root", "fracción")
    # Sin dato de un mes, nulo (R1); nunca se rellena con la otra fuente.
    assert values[("smap", 5)].value is None and values[("smap", 12)].value is None
    assert values[("smap", 4)].value == pytest.approx(0.31)


def test_la_humedad_no_cambia_el_deficit():
    without = plan(crop("papa"), crop("arveja", MAY))
    wetter = Moisture("nasa_power", "soil_wetness_root", "fracción", dict.fromkeys(range(1, 13), 0.99))
    with_moisture = plan(crop("papa"), crop("arveja", MAY), moisture=(wetter,))
    assert with_moisture.crops == without.crops
    assert with_moisture.farm == without.farm
    assert with_moisture.limitations == without.limitations


# ---------- R4 ----------


def test_misma_entrada_mismo_resultado():
    crops = (crop("papa"), crop("arveja", MAY, 0.3), wp.PlanCrop("descanso", "el descanso", wp.FALLOW, 20.0, APRIL, None, None))
    assert plan(*crops, moisture=(POWER,)) == plan(*crops, moisture=(POWER,))
    # El orden de los cultivos de la consulta se respeta, y la suma de la finca no depende de él.
    reversed_plan = plan(*reversed(crops), moisture=(POWER,))
    assert [c.crop_id for c in reversed_plan.crops] == ["descanso", "arveja", "papa"]
    assert reversed_plan.farm == plan(*crops).farm


def test_el_area_de_cada_cultivo_sale_de_su_porcentaje_de_la_finca():
    """El motor calcula el área de cada cultivo; la API solo pasa el porcentaje y el área de la finca."""
    papa = wp.PlanCrop("papa", "la papa", "crop", 40.0, APRIL, crop_window(STAGES, APRIL), ROOT)
    result = wp.water_plan([papa], 2.5, climate(), "franco", RAIN)
    assert result.crops[0].area_ha == 1.0
