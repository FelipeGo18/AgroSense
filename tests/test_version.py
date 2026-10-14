"""Los pesos por defecto de las señales y el endpoint que los publica (HU-075, HU-198, HU-122)."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.config.weights import P0_SIGNALS, WeightsError, get_default_weights, load_weights

GOOD = """
version: "9.9.9"
weights:
  water: {weight: 3, why: "a"}
  frost: {weight: 3, why: "b"}
  heat: {weight: 3, why: "c"}
  soil: {weight: 2, why: "d"}
  supply: {weight: 3, why: "e"}
  market: {weight: 2, why: "f"}
"""


def write(tmp_path, text):
    path = tmp_path / "weights.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_el_archivo_del_repositorio_tiene_las_seis_senales_con_peso_y_porque():
    defaults = get_default_weights()
    assert tuple(defaults.weights) == P0_SIGNALS
    assert all(1 <= weight <= 5 for weight in defaults.weights.values())
    assert all(defaults.reasons[signal] for signal in P0_SIGNALS)
    assert defaults.version


def test_un_archivo_bien_formado_se_lee(tmp_path):
    defaults = load_weights(write(tmp_path, GOOD))
    assert defaults.version == "9.9.9"
    assert defaults.weights == {"water": 3, "frost": 3, "heat": 3, "soil": 2, "supply": 3, "market": 2}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (('  market: {weight: 2, why: "f"}\n', ""), "le falta el peso de: market"),
        (("soil: {weight: 2,", "soil: {weight: 6,"), "debe ser un entero de 1 a 5"),
        (("soil: {weight: 2,", "soil: {weight: 0,"), "ningún peso por defecto es 0"),
        (("soil: {weight: 2,", "soil: {weight: 2.5,"), "debe ser un entero de 1 a 5"),
        (("soil: {weight: 2,", "soil: {weight: true,"), "debe ser un entero de 1 a 5"),
        (('why: "d"', 'why: ""'), "no dice su porqué"),
        (('version: "9.9.9"', "version: 3"), "`version` como texto"),
        (("  market:", '  rumor: {weight: 1, why: "x"}\n  market:'), "señales que no son del P0: rumor"),
    ],
)
def test_un_archivo_que_no_sirve_dice_que_hay_que_corregir(tmp_path, change, message):
    with pytest.raises(WeightsError, match=message):
        load_weights(write(tmp_path, GOOD.replace(*change)))


def test_sin_archivo_lo_dice(tmp_path):
    with pytest.raises(WeightsError, match="No existe weights.yaml"):
        load_weights(tmp_path / "weights.yaml")


def test_version_publica_los_pesos_por_defecto_sin_inventar_lo_que_no_existe():
    response = TestClient(app).get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    defaults = get_default_weights()
    assert body["default_weights"] == defaults.weights
    assert body["weights_version"] == defaults.version
    assert set(body["weights_reasons"]) == set(P0_SIGNALS)
    # Todavía no hay dataset, reglas, región ni fuentes publicados: vienen nulos o vacíos, no inventados (R5).
    assert (body["dataset_version"], body["rules_version"], body["created_at"], body["region"], body["sources"]) == (
        None,
        None,
        None,
        None,
        [],
    )


def test_version_no_necesita_sesion_ni_base_de_datos():
    # No usa `client` (la base de pruebas): responde igual con las cuentas apagadas.
    assert TestClient(app).get("/api/v1/version").headers["X-Request-ID"]
