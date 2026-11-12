"""HU-012: los endpoints de cálculo ya tienen su forma del contrato, sus ejemplos y sus validaciones; responden 501."""

from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import calc_examples as ex
from backend.api import calc_models as m
from backend.api.calculations import _get_article, _suitability_reason
from backend.api.errors import ApiError
from backend.api.main import app
from backend.config.settings import get_settings
from backend.config.weights import load_weights
from backend.engine.suitability import ABOVE_MAX, BELOW_MIN, Suitability

SOON = (date.today() + timedelta(days=40)).isoformat()
DIAGNOSIS = {"municipality_id": "15646", "crop_id": "papa", "sowing_date": SOON}
ROTATION = {"municipality_id": "15646", "sowing_date": SOON, "priorities": {"water": 3, "soil": 5, "income": 2, "risk": 4}}
WATER = {"municipality_id": "15646", "total_area_ha": 1.26, "crops": [{"crop_id": "papa", "area_pct": 100, "sowing_date": SOON}]}


@pytest.mark.parametrize(
    ("model", "example"),
    [
        (m.DiagnosisResponse, ex.DIAGNOSIS_OK),
        (m.DiagnosisResponse, ex.DIAGNOSIS_NOT_SUITABLE),
        (m.DiagnosisResponse, ex.DIAGNOSIS_NOT_EVALUABLE),
        (m.DiagnosisResponse, ex.DIAGNOSIS_NOT_APPLICABLE),
        (m.RotationResponse, ex.ROTATIONS),
        (m.RotationResponse, ex.ROTATIONS_EMPTY),
        (m.RotationResponse, ex.ROTATIONS_NO_CURRENT),
        (m.WaterPlanResponse, ex.WATER_PLAN),
        (m.ChangesResponse, ex.CHANGES),
        (m.TrendsResponse, ex.TRENDS),
        (m.MunicipalitySoil, ex.SOIL),
        *[(m.ErrorBody, body) for body in ex.ERRORS.values()],
    ],
)
def test_cada_ejemplo_cumple_su_modelo(model, example):
    model.model_validate(example)


def test_los_ejemplos_de_calculo_se_rotulan_como_ejemplo():
    """R5: ningún ejemplo pasa por un resultado real."""
    for example in (ex.DIAGNOSIS_OK, ex.ROTATIONS, ex.WATER_PLAN, ex.CHANGES, ex.TRENDS, ex.SOIL):
        assert example["versions"] == {"dataset": "ejemplo", "rules": "ejemplo"}


def test_los_ejemplos_cubren_cada_estado():
    statuses = {
        signal["status"]
        for example in (ex.DIAGNOSIS_OK, ex.DIAGNOSIS_NOT_EVALUABLE, ex.DIAGNOSIS_NOT_APPLICABLE)
        for signal in example["signals"].values()
    }
    assert statuses == {"available", "insufficient_data", "not_applicable"}
    assert ex.ROTATIONS["excluded"] and ex.ROTATIONS["current_strategy"]["issues"]
    assert any(month["tmax_p90_c"]["status"] == "insufficient_data" for month in ex.CHANGES["months"])


def test_el_openapi_trae_los_endpoints_de_calculo_con_sus_ejemplos():
    paths = app.openapi()["paths"]
    for path, method, codes in [
        ("/api/v1/diagnostics", "post", {"200", "401", "404", "422", "501", "503"}),
        ("/api/v1/rotations", "post", {"200", "401", "404", "422", "501", "503"}),
        ("/api/v1/water-plans", "post", {"200", "422", "501", "503"}),
        ("/api/v1/changes", "get", {"200", "422", "501", "503"}),
        ("/api/v1/trends", "get", {"200", "422", "501", "503"}),
        ("/api/v1/catalogs/municipalities/{municipality_id}/soil", "get", {"200", "404", "503"}),
    ]:
        responses = paths[path][method]["responses"]
        assert codes <= set(responses), path
        content = responses["200"]["content"]["application/json"]
        assert "examples" in content or "example" in content, path


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/v1/diagnostics", DIAGNOSIS),
        ("post", "/api/v1/rotations", {**ROTATION, "previous_crop_ids": ["papa"], "current_crop_ids": ["papa", "arveja"]}),
        ("post", "/api/v1/water-plans", WATER),
        # El agua del ciclo de un abono verde (HU-215): es una entrada válida.
        ("post", "/api/v1/water-plans", {**WATER, "crops": [{"crop_id": "avena_vicia", "area_pct": 100, "sowing_date": SOON}]}),
        ("get", "/api/v1/changes?municipality_id=15646&crop_id=papa", None),
        ("get", f"/api/v1/trends?municipality_id=15646&crop_id=papa&sowing_date={SOON}", None),
    ],
)
def test_una_entrada_valida_responde_501_con_la_forma_de_los_errores(dataset, method, path, body):
    response = getattr(TestClient(app), method)(path, **({"json": body} if body else {}))
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_implemented"
    assert response.json()["error"]["request_id"]


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/v1/diagnostics", {**DIAGNOSIS, "crop_id": "yuca"}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "crop_id": "avena_vicia"}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "municipality_id": "05001"}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "sowing_date": (date.today() - timedelta(days=40)).isoformat()}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "sowing_date": (date.today() + timedelta(days=420)).isoformat()}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "priorities": {s: 0 for s in ("water", "frost", "heat", "soil", "supply", "market")}}),
        ("/api/v1/diagnostics", {**DIAGNOSIS, "otro_campo": 1}),
        ("/api/v1/rotations", {**ROTATION, "cycles": 4}),
        ("/api/v1/rotations", {**ROTATION, "current_crop_ids": ["papa"]}),
        ("/api/v1/rotations", {**ROTATION, "previous_crop_ids": ["papa", "arveja", "haba", "maiz"]}),
        ("/api/v1/rotations", {**ROTATION, "priorities": {"water": 0, "soil": 0, "income": 0, "risk": 0}}),
        (
            "/api/v1/water-plans",
            {
                **WATER,
                "crops": [
                    {"crop_id": "papa", "area_pct": 70, "sowing_date": SOON},
                    {"crop_id": "arveja", "area_pct": 40, "sowing_date": SOON},
                ],
            },
        ),
    ],
)
def test_una_entrada_invalida_responde_422(dataset, path, body):
    response = TestClient(app).post(path, json=body)
    assert response.status_code == 422, response.json()
    assert response.json()["error"]["code"] == "invalid_input"


def test_el_mes_en_curso_se_acepta_aunque_su_dia_1_ya_paso(dataset):
    first = date.today().replace(day=1).isoformat()
    assert TestClient(app).post("/api/v1/diagnostics", json={**DIAGNOSIS, "sowing_date": first}).status_code == 501


def test_con_lot_id_y_sin_sesion_responde_401(dataset, client):
    response = client.post("/api/v1/diagnostics", json={**DIAGNOSIS, "lot_id": "00000000-0000-4000-8000-000000000001"})
    assert response.status_code == 401


def test_sin_dataset_los_calculos_responden_503():
    assert TestClient(app).post("/api/v1/diagnostics", json=DIAGNOSIS).status_code == 503


def test_el_suelo_del_municipio_sin_suelo_publicado_responde_503(dataset):
    response = TestClient(app).get("/api/v1/catalogs/municipalities/15646/soil")
    assert response.status_code == 503 and response.json()["error"]["code"] == "dataset_unavailable"
    assert TestClient(app).get("/api/v1/catalogs/municipalities/99999/soil").status_code == 404


def test_el_suelo_del_municipio_con_los_datos_de_ejemplo(monkeypatch):
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(Path("data/examples").resolve()))
    get_settings.cache_clear()
    body = TestClient(app).get("/api/v1/catalogs/municipalities/15646/soil").json()
    m.MunicipalitySoil.model_validate(body)
    assert body["source_id"] == "ejemplo" and body["versions"]["dataset"] == "ejemplo"
    assert body["ph"]["p05"] <= body["ph"]["value"] <= body["ph"]["p95"]
    assert body["slope_pct"] == 9.0


# ---------- `_get_article`: el artículo sale del catálogo, nunca de una heurística ----------


def test_get_article_lee_el_campo_del_catalogo():
    """Lee `article` del catálogo tal cual, sin adivinar por la terminación del nombre."""
    assert _get_article({"crop_id": "papa", "name_es": "Papa", "article": "la"}) == "la"
    # Caso que la heurística vieja («termina en 'a' → la») habría fallado: «Haba» termina en «a» pero lleva «el»
    # (excepción fonética, como «el agua»).
    assert _get_article({"crop_id": "haba", "name_es": "Haba", "article": "el"}) == "el"


def test_get_article_sin_el_campo_lanza_error_claro():
    """Sin `article` no se adivina en silencio: se lanza un error que nombra el `crop_id` (en vez de una frase mal
    escrita), con el código del proyecto para errores de la API, no una excepción cruda."""
    with pytest.raises(ApiError) as excinfo:
        _get_article({"crop_id": "cultivo_ficticio", "name_es": "Cultivo ficticio"})
    assert excinfo.value.status_code == 500 and excinfo.value.code == "internal_error"
    assert "cultivo_ficticio" in excinfo.value.log


def test_suitability_reason_sin_article_propaga_el_error():
    """`_suitability_reason` no produce una frase mal escrita cuando la ficha no trae `article`: propaga el error."""
    crop = {"crop_id": "cultivo_ficticio", "name_es": "Cultivo ficticio"}
    result = Suitability("not_suitable", 0.0, ABOVE_MAX)
    with pytest.raises(ApiError) as excinfo:
        _suitability_reason(crop, result, 30.0, 10.0, 20.0)
    assert "cultivo_ficticio" in excinfo.value.log


def test_suitability_reason_usa_el_articulo_del_catalogo():
    """Con un cultivo cuyo nombre termina en «a» pero cuyo artículo correcto es «el» (como «haba»), la frase sale
    bien escrita porque se lee del catálogo, no de la terminación del nombre."""
    crop = {"crop_id": "haba", "name_es": "Haba", "article": "el"}
    result = Suitability("not_suitable", 0.0, ABOVE_MAX)
    reason = _suitability_reason(crop, result, 35.0, 5.0, 32.0)
    assert "aguanta el haba" in reason


def test_suitability_reason_lee_que_limite_se_cruzo_del_motor_sin_repetir_la_comparacion():
    """La API no vuelve a comparar `tmean_annual_c` contra los límites: lee `result.exceeded`, que ya decidió
    `backend.engine.suitability.suitability()` (R6, «la API es una capa delgada»)."""
    crop = {"crop_id": "maiz", "name_es": "Maíz", "article": "el"}
    below = Suitability("not_suitable", 0.0, BELOW_MIN)
    assert "no alcanza la que necesita" in _suitability_reason(crop, below, 6.0, 10.0, 34.0)
    above = Suitability("not_suitable", 0.0, ABOVE_MAX)
    assert "pasa de la que aguanta" in _suitability_reason(crop, above, 40.0, 10.0, 34.0)


# ---------- HU-191: aptitud del cultivo (regla 0 de la agregación del semáforo) ----------
# El motor todavía no la calcula: hoy el endpoint responde 501 para toda entrada válida. Estos casos fijan la forma
# que debe tener la respuesta cuando el cableado exista (200) y la red que impide un 200 adelantado donde la aptitud
# no se puede decidir (501, por falta de clima del municipio o de rango en la ficha del cultivo).


def test_diagnostico_cultivo_no_apto_responde_200_con_la_forma_del_contrato(dataset_con_clima):
    response = TestClient(app).post("/api/v1/diagnostics", json={"municipality_id": "25307", "crop_id": "papa", "sowing_date": SOON})
    assert response.status_code == 200, response.json()
    body = response.json()
    m.DiagnosisResponse.model_validate(body)

    suitability = body["suitability"]
    assert suitability["level"] == "not_suitable"
    assert suitability["score"] == 0
    assert suitability["basis"] == "municipality"
    assert suitability["tmean_annual_c"] == 28.4
    assert suitability["altitude_m"] == 289

    assert body["window"] is None
    assert body["signals"] is None

    for key in ("overall", "overall_default"):
        light = body[key]
        assert light["light"] == "red"
        assert light["action"] == "rotate"
        assert light["limiting_signal"] is None
        assert light["high_risk"] is False
        assert light["reasons"] == ["Este cultivo no se da en su zona: elija otro"]
    assert body["overall"]["weights_basis"] == "default"

    assert body["weights"] == load_weights().weights
    assert body["versions"]["dataset"] not in (None, "ejemplo")
    assert body["request"]["crop_id"] == "papa"
    assert body["request"]["municipality_id"] == "25307"


def test_diagnostico_cultivo_no_apto_la_razon_cita_la_ficha_y_su_fuente(dataset_con_clima):
    """R5, R8: la razón nombra el dato de la ficha que excluye el cultivo (`tmean_max_c` de la papa), no solo la luz."""
    response = TestClient(app).post("/api/v1/diagnostics", json={"municipality_id": "25307", "crop_id": "papa", "sowing_date": SOON})
    assert response.status_code == 200, response.json()
    assert response.json()["suitability"]["reasons"] == [
        "La temperatura media anual del municipio (28,4 °C) pasa de la que aguanta la papa (hasta 16 °C)"
    ]


def test_diagnostico_cultivo_no_apto_por_debajo_del_minimo(dataset_con_clima):
    """El mismo filtro por el otro borde: Villa de Leyva (6,0 °C) queda por debajo del mínimo del maíz (10 °C)."""
    response = TestClient(app).post("/api/v1/diagnostics", json={"municipality_id": "15407", "crop_id": "maiz", "sowing_date": SOON})
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["suitability"]["level"] == "not_suitable"
    assert body["suitability"]["score"] == 0
    assert body["suitability"]["tmean_annual_c"] == 6.0
    assert body["suitability"]["reasons"] == [
        "La temperatura media anual del municipio (6,0 °C) no alcanza la que necesita el maíz (desde 10 °C)"
    ]
    assert body["overall"]["light"] == "red" and body["overall"]["action"] == "rotate"


def test_diagnostico_cultivo_apto_sigue_en_501(dataset_con_clima):
    """Camino feliz: sin las señales todavía no se puede diagnosticar, aunque la aptitud ya se pudiera decidir."""
    response = TestClient(app).post("/api/v1/diagnostics", json={"municipality_id": "15646", "crop_id": "papa", "sowing_date": SOON})
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_implemented"


def test_diagnostico_sin_clima_del_municipio_sigue_en_501(dataset_con_clima):
    """R1: sin `tmean_annual_c`, la aptitud es `insufficient_data` (no bloquea), pero tampoco alcanza para un 200."""
    response = TestClient(app).post("/api/v1/diagnostics", json={"municipality_id": "25899", "crop_id": "papa", "sowing_date": SOON})
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_implemented"


def test_diagnostico_ficha_sin_rango_completo_sigue_en_501(dataset_con_clima):
    """La cebolla de bulbo no tiene `tmean_max_c` con fuente: la aptitud es `insufficient_data`, nunca inventada (R8)."""
    response = TestClient(app).post(
        "/api/v1/diagnostics", json={"municipality_id": "15646", "crop_id": "cebolla_bulbo", "sowing_date": SOON}
    )
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_implemented"
