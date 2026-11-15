"""La señal de agua en `/diagnostics` (HU-071, cableado de HU-076): las fuentes de la lluvia y de la humedad del suelo
para contrastar, el aviso de `catalog/sources.yaml` y el balance hídrico que recibe la señal.

Usa una copia del dataset de ejemplo del repositorio (`data/examples/`, rotulado como ejemplo, R5): Samacá, con lluvia
de ejemplo en `precip_month` (la tabla de GPM IMERG) y en `climate_month` (la de NASA POWER) para 2015-2024, rotulada
con la fuente de su tabla (`tests/ejemplos_con_fuente.py`): la señal solo lee las filas de la fuente que dice
`catalog/sources.yaml`, como `/trends`. «Hoy» queda fijo en el 14 de noviembre de 2026 en la región (R4).

La API pide el balance en un solo punto, `backend.api.window_signals.balance_for`: el de HU-144
(`backend/engine/water_balance.py`), con el agua que guarda el suelo. Para probar casos puntuales, algunas pruebas
cambian ese punto por uno que devuelve un balance **de ejemplo** (`EXAMPLE_*`), igual para todas las ventanas: no son
datos de ninguna zona (R5).
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.api import calc_models as m
from backend.api import window_signals as window_signals_module
from backend.api.main import app
from backend.api.water_signals import SourceReading, WaterSignal
from backend.api.window_signals import pending_signal, signal_sources
from backend.config.settings import get_settings
from backend.dataset import get_dataset
from backend.engine.sensitive_signal import ClimateSignalResult
from backend.engine.water_signal import NO_RETENTION, WaterBalanceSummary
from common import region
from common.signal_sources import get_signal_sources
from tests.ejemplos_con_fuente import EXAMPLES, examples_with_sources

SAMACA = "15646"
TODAY = datetime(2026, 11, 14, 17, 0, tzinfo=UTC)
NOVEMBER, APRIL = "2026-11-01", "2027-04-01"

# Balances de ejemplo (R5), con lo que pide el cultivo en la ventana y el déficit del año seco [mín, máx].
EXAMPLE_HIGH_DEFICIT = WaterBalanceSummary(need_mm=400.0, dry_deficit_mm=(300.0, 340.0), retention=True)  # cubre 15-25 %
EXAMPLE_NO_DEFICIT = WaterBalanceSummary(need_mm=400.0, dry_deficit_mm=(0.0, 0.0), retention=True)  # cubre 100 %
EXAMPLE_NO_RETENTION = WaterBalanceSummary(need_mm=400.0, dry_deficit_mm=(0.0, 0.0), retention=False)

RAIN_INDICATORS = {"precip_dry_mm", "precip_normal_mm"}


@pytest.fixture(autouse=True)
def today(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return TODAY.astimezone(tz) if tz else TODAY

    monkeypatch.setattr(region, "datetime", Clock)


@pytest.fixture(autouse=True)
def examples(tmp_path, monkeypatch):
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(examples_with_sources(tmp_path / "ejemplos")))
    get_settings.cache_clear()


def use_balance(monkeypatch, balance: WaterBalanceSummary | None) -> None:
    """Cambia el balance de producción por uno de ejemplo, para las pruebas que necesitan un déficit fijo. No fija qué
    recibe `balance_for`: solo qué devuelve."""
    monkeypatch.setattr(window_signals_module, "balance_for", lambda *args, **kwargs: balance)


def diagnose(sowing_date: str = APRIL, **extra) -> dict:
    body = {"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": sowing_date, **extra}
    response = TestClient(app).post("/api/v1/diagnostics", json=body)
    assert response.status_code == 200, response.json()
    m.DiagnosisResponse.model_validate(response.json())
    return response.json()


def rain_caveat() -> str:
    caveat = get_signal_sources().for_region(get_dataset().region["id"])["water"].caveat
    assert caveat, "la región piloto tiene `rain_caveat` en catalog/sources.yaml"
    return caveat


# ---------- el balance de hoy: con lo nuestro, sin el agua guardada y dicho (R1, R5) ----------


def test_el_agua_se_califica_con_el_balance_de_hu144_y_el_agua_que_guarda_el_suelo():
    """Con la lluvia del año seco, la ET0, la textura del municipio y la raíz de la ficha, el balance de HU-144 califica
    el agua: nivel, calificación y el déficit como indicador, contando el agua que guarda el suelo."""
    body = diagnose()
    water = body["signals"]["water"]
    assert water["status"] == "available"
    assert water["level"] in ("favorable", "moderate", "unfavorable")
    assert isinstance(water["score"], int) and 0 <= water["score"] <= 100
    assert water["indicators"] == ["water_deficit_mm"]
    assert "la lluvia y el agua que guarda el suelo cubren" in water["reasons"][0]
    assert NO_RETENTION not in body["limitations"]
    # Con el agua calificada, la luz de AgroSense ya no es `not_evaluable` por falta de agua (regla 1).
    assert body["overall_default"]["light"] != "not_evaluable"


def test_sin_balance_el_agua_es_sin_datos_y_dice_que_falta_el_balance(monkeypatch):
    """Si el balance no se puede armar: `insufficient_data` con nivel y calificación nulos, no crítica, y la razón dice
    que falta el balance (no la lluvia ni la ET0, que sí están), también en las limitaciones."""
    use_balance(monkeypatch, None)
    body = diagnose()
    water = body["signals"]["water"]
    assert (water["status"], water["level"], water["score"], water["critical"], water["indicators"]) == (
        "insufficient_data", None, None, False, []
    )  # fmt: skip
    assert len(water["reasons"]) == 1
    assert water["reasons"][0].startswith("Sin el balance hídrico de la papa")
    assert "Sin la lluvia" not in water["reasons"][0] and "evapotranspiración" not in water["reasons"][0]
    assert body["limitations"].count(water["reasons"][0]) == 1
    assert "Sin datos para la zona: el agua no se evaluó." not in body["limitations"]
    # Con el agua sin datos y con peso, la luz de AgroSense no se puede evaluar (regla 1).
    assert (body["overall_default"]["light"], body["overall_default"]["action"]) == ("not_evaluable", "review_data")


@pytest.mark.parametrize("irrigated", [None, False, True])
def test_el_aviso_de_la_lluvia_va_en_las_limitaciones_aunque_el_agua_no_se_califique(irrigated):
    """HU-071: el `rain_caveat` de la región va en cada respuesta que evalúa una ventana, una sola vez."""
    assert diagnose(irrigated=irrigated)["limitations"].count(rain_caveat()) == 1


# ---------- signals.water.sources: las fuentes juntas, nunca mezcladas (decisión 11, R1, R10) ----------


def water_sources(body: dict) -> list[dict]:
    sources = body["signals"]["water"].get("sources")
    assert sources, "signals.water.sources viene en el diagnóstico"
    return sources


@pytest.mark.parametrize("balance", [None, EXAMPLE_NO_DEFICIT])
def test_las_fuentes_del_agua_traen_la_lluvia_de_imerg_y_de_power_y_la_humedad_de_power(monkeypatch, balance):
    """IMERG calcula la señal con su año seco (`used = true`) y muestra su normal (`used = false`); POWER se muestra para
    contrastar (`used = false`), y la humedad del suelo de raíces de POWER también (`used = false`, no califica). Una
    sola entrada con `used = true`. SMAP está en `planned`: no aparece."""
    use_balance(monkeypatch, balance)
    sources = water_sources(diagnose())
    pairs = {(source["source_id"], source["indicator"]): source for source in sources}
    assert len(pairs) == len(sources), "sin entradas repetidas"

    assert [(source["source_id"], source["indicator"]) for source in sources if source["used"]] == [("imerg", "precip_dry_mm")]
    assert pairs[("imerg", "precip_normal_mm")]["used"] is False
    power_rain = [source for source in sources if source["source_id"] == "nasa_power" and source["indicator"] in RAIN_INDICATORS]
    assert power_rain and not any(source["used"] for source in power_rain)
    assert pairs[("nasa_power", "soil_wetness_root")]["used"] is False

    assert not any(source["source_id"] == "smap" or source["indicator"] == "sm_rootzone_m3_m3" for source in sources)
    assert {source["source_id"] for source in sources} <= {"imerg", "nasa_power"}


def test_cada_fuente_de_lluvia_trae_su_valor_su_unidad_y_su_periodo():
    """La lluvia de la ventana de cada fuente, en mm y con los años de su periodo (los de ejemplo, 2015-2024). La normal
    nunca es menor que la del año seco (el año seco es el percentil 20), y la humedad del suelo es una fracción."""
    sources = water_sources(diagnose())
    rain = [source for source in sources if source["indicator"] in RAIN_INDICATORS]
    assert {source["source_id"] for source in rain} == {"imerg", "nasa_power"}
    for source in rain:
        assert source["unit"] == "mm"
        assert source["value"] is not None and source["value"] > 0
        assert source["period"] and "2015" in source["period"] and "2024" in source["period"]
    for source_id in ("imerg", "nasa_power"):
        values = {source["indicator"]: source["value"] for source in rain if source["source_id"] == source_id}
        if values.keys() >= RAIN_INDICATORS:
            assert values["precip_normal_mm"] >= values["precip_dry_mm"]
    wetness = next(source for source in sources if source["indicator"] == "soil_wetness_root")
    assert wetness["value"] is not None and 0 <= wetness["value"] <= 1


def test_la_senal_y_las_tendencias_leen_las_mismas_filas_de_cada_fuente(monkeypatch):
    """Una sola regla para saber de qué tabla y de qué filas sale la lluvia de una fuente (`monthly_climate.rain_rows`):
    con las filas del dataset de ejemplo sin rotular (`source_id = ejemplo`), ni la señal ni `/trends` las toman por
    GPM IMERG ni por NASA POWER (R1, R5)."""
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(EXAMPLES.resolve()))
    get_settings.cache_clear()
    body = diagnose()
    water = body["signals"]["water"]
    assert water["status"] == "insufficient_data"
    rain = [source for source in water_sources(body) if source["indicator"] in RAIN_INDICATORS]
    assert {source["source_id"] for source in rain} == {"imerg", "nasa_power"}
    assert all(source["value"] is None for source in rain)
    # La razón dice la causa real: falta la lluvia de la fuente que calcula la señal (R5).
    assert water["reasons"][0].startswith("Sin la lluvia de GPM IMERG para la zona ")
    assert "no se usa otra fuente" in water["reasons"][0]
    assert water["reasons"][0] in body["limitations"]
    trends = TestClient(app).get("/api/v1/trends", params={"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": APRIL})
    assert trends.json()["water"]["status"] == "insufficient_data"


def test_solo_el_agua_trae_fuentes_en_el_mvp():
    """`sources` aparece en una señal cuando hay más de una fuente; en el MVP, solo en el agua (la oferta, en P1)."""
    signals = diagnose()["signals"]
    assert all(signals[name].get("sources") is None for name in ("frost", "heat", "soil", "market"))


def test_signal_sources_lee_las_fuentes_solo_de_la_senal_que_las_trae():
    """`signal_sources` distingue por el tipo (`ContrastedSignal`), sin `getattr`: las señales del motor y las que
    todavía no tienen motor no traen fuentes."""
    reading = SourceReading("imerg", "precip_dry_mm", 120.0, "mm", "2001-2024", True)
    water = WaterSignal("insufficient_data", None, False, None, (), ("razón",), (), (reading,))
    climate = ClimateSignalResult("insufficient_data", None, False, None, (), ("razón",))
    assert signal_sources(water) == (reading,)
    assert signal_sources(climate) is None
    assert signal_sources(pending_signal("soil")) is None


# ---------- con un balance de ejemplo: la señal calificada ----------


def test_con_un_balance_de_ejemplo_el_agua_se_califica_y_lleva_el_aviso(monkeypatch):
    use_balance(monkeypatch, EXAMPLE_NO_DEFICIT)
    body = diagnose()
    water = body["signals"]["water"]
    assert (water["status"], water["level"], water["score"], water["critical"], water["indicators"]) == (
        "available", "favorable", 100, False, ["water_deficit_mm"]
    )  # fmt: skip
    assert water["counts"] is True
    # La razón cita los años de la lluvia de ejemplo (R5: historia, no pronóstico).
    assert "2015" in water["reasons"][0] and "2024" in water["reasons"][0]
    assert body["limitations"].count(rain_caveat()) == 1
    assert not any("agua no se evaluó" in text for text in body["limitations"])
    # Abril en Samacá: heladas y calor en 100, el agua favorable, lo demás sin datos: verde con el criterio de AgroSense.
    assert (body["overall_default"]["light"], body["overall_default"]["action"]) == ("green", "sow")


@pytest.mark.parametrize("irrigated", [False, None])
def test_caso_de_referencia_deficit_alto_sin_riego_es_desfavorable(monkeypatch, irrigated):
    """HU-071: sin riego (o sin dato de riego, que se evalúa como sin riego) un déficit alto da `unfavorable`, crítica,
    y la luz es roja: cambiar de fecha puede ayudar (todo lo desfavorable es de clima)."""
    use_balance(monkeypatch, EXAMPLE_HIGH_DEFICIT)
    body = diagnose(irrigated=irrigated)
    water = body["signals"]["water"]
    assert (water["status"], water["level"], water["critical"]) == ("available", "unfavorable", True)
    assert (body["overall_default"]["light"], body["overall_default"]["action"]) == ("red", "other_window")


def test_caso_de_referencia_el_mismo_deficit_con_riego_no_es_desfavorable(monkeypatch):
    """HU-071: con riego, la misma ventana con el mismo déficit es `favorable` y no crítica; la razón dice cuánto regar
    (de 300 a 340 mm) y que es una estimación (R10)."""
    use_balance(monkeypatch, EXAMPLE_HIGH_DEFICIT)
    body = diagnose(irrigated=True)
    water = body["signals"]["water"]
    assert (water["status"], water["level"], water["score"], water["critical"]) == ("available", "favorable", 100, False)
    reason = water["reasons"][0]
    assert "300" in reason and "340" in reason and "mm" in reason
    assert "estimación" in reason.lower()
    assert body["overall_default"]["light"] == "green"


def test_sin_retencion_del_suelo_se_califica_y_lo_dicen_las_limitaciones(monkeypatch):
    use_balance(monkeypatch, EXAMPLE_NO_RETENTION)
    body = diagnose()
    assert body["signals"]["water"]["status"] == "available"
    assert body["limitations"].count(NO_RETENTION) == 1


def test_caso_de_referencia_helada_critica_con_agua_favorable_da_rojo_y_otra_ventana(monkeypatch):
    """HU-077 (parte que depende del agua): sembrando en noviembre, la helada es crítica (7 de 100); con el agua
    favorable y los pesos de AgroSense la luz es roja y la acción `other_window`, y ninguna de las mejores ventanas es
    de alto riesgo (R2). La oferta todavía no tiene motor (HU-072): queda sin datos."""
    use_balance(monkeypatch, EXAMPLE_NO_DEFICIT)
    body = diagnose(NOVEMBER)
    assert body["signals"]["water"]["level"] == "favorable"
    assert (body["signals"]["frost"]["level"], body["signals"]["frost"]["critical"]) == ("unfavorable", True)
    default = body["overall_default"]
    assert (default["light"], default["action"], default["high_risk"], default["limiting_signal"]) == ("red", "other_window", True, "frost")
    assert body["best_windows"] and not any(window["high_risk"] for window in body["best_windows"])


# ---------- R4 ----------


@pytest.mark.parametrize("balance", [None, EXAMPLE_HIGH_DEFICIT])
def test_dos_consultas_iguales_dan_lo_mismo(monkeypatch, balance):
    use_balance(monkeypatch, balance)
    client = TestClient(app)
    body = {"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": NOVEMBER, "irrigated": True}
    assert client.post("/api/v1/diagnostics", json=body).content == client.post("/api/v1/diagnostics", json=body).content
