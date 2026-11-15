"""HU-213: los ciclos de una estrategia con su diagnóstico (`backend/api/strategy_cycles.py`).

Usa el dataset de ejemplo del repositorio (`data/examples/`, rotulado como ejemplo, R5): Samacá, con heladas de ejemplo
(la papa sembrada en noviembre tiene helada crítica). «Hoy» queda fijo en el 14 de noviembre de 2026 en la región (R4).
En el ejemplo la papa dura 165 días, la arveja 110, la zanahoria 150 y el descanso 180 (`fallow_days`, HU-063).

Desde el jueves 1 de abril de 2027: la papa se cosecha el lunes 13 de septiembre y la arveja se siembra ese mismo día
(hueco 0); la arveja se cosecha el sábado 1 de enero de 2028 y el ciclo 3 se siembra el lunes 3 de enero (hueco 2), más
de doce meses después de hoy.
"""

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.api import strategy_cycles
from backend.api.main import app
from backend.api.strategy_cycles import StrategyCycles
from backend.api.window_diagnosis import window_query
from backend.config.weights import get_default_weights
from backend.dataset import get_dataset
from backend.engine.diagnosis import IRRIGATION_UNKNOWN
from backend.engine.rotations.exclusions import high_risk_motives
from backend.engine.traffic_light import DEFAULT, FARMER
from common import region
from tests.test_diagnostico import EXAMPLES, NO_WATER, SAMACA, use

TODAY = datetime(2026, 11, 14, 17, 0, tzinfo=UTC)
APRIL = date(2027, 4, 1)


@pytest.fixture(autouse=True)
def today(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return TODAY.astimezone(tz) if tz else TODAY

    monkeypatch.setattr(region, "datetime", Clock)


@pytest.fixture
def examples(monkeypatch):
    use(monkeypatch, EXAMPLES)


def strategy(sowing: date = APRIL, priorities: dict[str, int] | None = None, lot=None, irrigated: bool | None = None):
    """Los ciclos como los armaría `/rotations`: los pesos de `signal_priorities` o, sin ellos, los de `weights.yaml`."""
    dataset = get_dataset()
    defaults = get_default_weights().weights
    weights, basis = (priorities, FARMER) if priorities is not None else (defaults, DEFAULT)
    query = window_query(dataset, dataset.municipalities[SAMACA], lot, weights, basis, defaults, irrigated)
    return StrategyCycles(query, sowing)


def cycles_of(sequence: tuple[str, ...], **query):
    cycles = strategy(**query)
    planned = cycles.plan(sequence)
    assert planned is not None
    return cycles.cycles(planned)


def diagnostics(crop_id: str, sowing: date, **extra) -> dict:
    body = {"municipality_id": SAMACA, "crop_id": crop_id, "sowing_date": sowing.isoformat(), **extra}
    response = TestClient(app).post("/api/v1/diagnostics", json=body)
    assert response.status_code == 200, response.json()
    found = response.json()
    del found["request"]
    found.pop("best_windows", None)
    return found


def test_fechas_de_los_ciclos_desde_la_fecha_de_siembra(examples):
    cycles = cycles_of(("papa", "arveja", "descanso"))
    assert [(c.cycle, c.crop_id, c.sowing_date, c.harvest_estimate, c.harvest_basis) for c in cycles] == [
        (1, "papa", date(2027, 4, 1), date(2027, 9, 13), "calendar"),
        (2, "arveja", date(2027, 9, 13), date(2028, 1, 1), "calendar"),
        (3, "descanso", date(2028, 1, 3), date(2028, 7, 1), "calendar"),
    ]


def test_cada_ciclo_trae_el_mismo_diagnostico_que_diagnostics(examples):
    """Criterio de HU-213: el primer ciclo y `/diagnostics` con la misma entrada dan las mismas señales y
    calificaciones; también el segundo, con su propia fecha. Se compara la respuesta entera, sin `request` ni
    `best_windows`, que un ciclo no trae."""
    cycles = cycles_of(("papa", "arveja", "descanso"), priorities=NO_WATER)
    for cycle in cycles[:2]:
        assert cycle.diagnosis is not None
        assert cycle.diagnosis.model_dump(mode="json") == diagnostics(cycle.crop_id, cycle.sowing_date, priorities=NO_WATER)
        assert (cycle.light, cycle.light_default) == (cycle.diagnosis.overall.light, cycle.diagnosis.overall_default.light)
        assert cycle.limiting_signal == cycle.diagnosis.overall.limiting_signal
        assert cycle.high_risk == cycle.diagnosis.overall.high_risk


def test_el_descanso_no_tiene_diagnostico(examples):
    rest = cycles_of(("papa", "arveja", "descanso"))[2]
    assert (rest.light, rest.light_default, rest.limiting_signal, rest.diagnosis, rest.high_risk) == (None, None, None, None, False)


def test_sin_prioridades_usa_los_pesos_por_defecto_y_las_dos_luces_coinciden(examples):
    first = cycles_of(("papa", "arveja"))[0]
    assert first.diagnosis is not None
    assert first.diagnosis.weights.model_dump() == get_default_weights().weights
    assert first.diagnosis.overall.weights_basis == "default"
    assert first.light == first.light_default


def test_con_prioridades_la_luz_es_la_del_agricultor(examples):
    first = cycles_of(("papa", "arveja"), priorities=NO_WATER)[0]
    assert first.diagnosis is not None
    assert first.diagnosis.weights.model_dump() == NO_WATER
    assert first.diagnosis.overall.weights_basis == "farmer"
    assert first.diagnosis.overall_default.weights_basis == "default"


def test_un_ciclo_a_mas_de_doce_meses_se_evalua_igual(examples):
    """El ciclo 3 cae el 3 de enero de 2028: `/diagnostics` no lo acepta como fecha de siembra (más de doce meses), pero
    en una estrategia se evalúa igual, con la historia de la zona."""
    third = cycles_of(("papa", "arveja", "zanahoria"))[2]
    assert third.sowing_date == date(2028, 1, 3)
    assert third.diagnosis is not None and third.diagnosis.signals is not None
    assert set(third.diagnosis.signals) == {"water", "frost", "heat", "soil", "supply", "market"}
    response = TestClient(app).post(
        "/api/v1/diagnostics", json={"municipality_id": SAMACA, "crop_id": "zanahoria", "sowing_date": "2028-01-03"}
    )
    assert response.status_code == 422


def test_con_lote_el_riego_es_el_del_lote(examples):
    """Con `lot_id`, el riego sale del lote aunque la consulta diga otra cosa (EP-16). El lote es DE EJEMPLO, sin
    contorno: la temperatura y la textura son las del municipio."""
    unknown = SimpleNamespace(irrigated=None, geometry=None)
    first = cycles_of(("papa", "arveja"), lot=unknown, irrigated=True)[0]
    assert first.diagnosis is not None and IRRIGATION_UNKNOWN in first.diagnosis.limitations
    known = SimpleNamespace(irrigated=False, geometry=None)
    first = cycles_of(("papa", "arveja"), lot=known)[0]
    assert first.diagnosis is not None and IRRIGATION_UNKNOWN not in first.diagnosis.limitations


def test_el_filtro_recibe_un_diagnostico_por_ciclo_con_su_fuente(examples):
    """HU-081, fase 2: la papa sembrada en noviembre tiene helada crítica en el ejemplo. El diagnóstico de ese ciclo da
    el motivo `high_risk` con la razón de la señal y la fuente que calcula las heladas en la región (NASA POWER). El
    descanso no tiene diagnóstico."""
    cycles = strategy(sowing=date(2026, 11, 2))
    diagnoses = cycles.diagnoser()(("papa", "descanso"))
    assert len(diagnoses) == 2 and diagnoses[1] is None
    assert diagnoses[0] is not None
    frost = diagnoses[0]["frost"]
    assert frost.score.critical and frost.score.level == "unfavorable"
    assert frost.source_ids == ("nasa_power",)
    assert diagnoses[0]["water"].source_ids == ("imerg", "nasa_power")
    motives = high_risk_motives(("papa", "descanso"), diagnoses)
    assert [(m.kind, m.cycle, m.signal, m.source_ids) for m in motives] == [("high_risk", 1, "frost", ("nasa_power",))]
    assert motives[0].reason == frost.reason


def test_un_ciclo_repetido_entre_estrategias_se_diagnostica_una_vez(examples, monkeypatch):
    calls = []
    real = strategy_cycles.diagnose_window

    def counted(query, crop_id, sowing_date):
        calls.append((crop_id, sowing_date))
        return real(query, crop_id, sowing_date)

    monkeypatch.setattr(strategy_cycles, "diagnose_window", counted)
    cycles = strategy()
    for sequence in (("papa", "arveja"), ("papa", "zanahoria"), ("papa", "arveja", "zanahoria")):
        planned = cycles.plan(sequence)
        assert planned is not None
        cycles.cycles(planned)
    assert calls.count(("papa", APRIL)) == 1
    assert calls.count(("arveja", date(2027, 9, 13))) == 1
