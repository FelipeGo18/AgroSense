"""HU-084 (y la parte de endpoint de HU-223): `POST /api/v1/rotations` conectado al motor.

Datos de EJEMPLO (R5): el dataset de `tests/conftest.py` con el catálogo y las `rotation_rules` reales (fixture `datos`
de los casos de referencia). Samacá (15646) es fría: la papa es apta. Girardot (25307) es cálida: la papa no es apta.
El suelo y la rejilla del lote dibujado son cifras inventadas, como en `tests/test_suelo_del_lote.py`.
"""

import polars as pl
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import box, mapping
from structlog.testing import capture_logs

from backend.api import calc_models as m
from backend.api import rotations as rotations_module
from backend.api.main import app
from backend.api.soil_signals import LOT_SOIL_LIMITATION
from backend.dataset import SOIL_COLUMNS
from backend.engine.rotations.current import NO_CURRENT_LIMITATION
from common.grid import cell_id
from common.region import region_today
from tests.engine.casos.conftest import EJEMPLO_CALIDO, EJEMPLO_FRIO, EJEMPLO_PRIORIDADES, datos  # noqa: F401
from tests.test_diagnostico import create_lot, dump, register, rows

CRITERIOS = ("water", "soil", "income", "risk")


def cuerpo(**campos) -> dict:
    return {
        "municipality_id": EJEMPLO_FRIO,
        "sowing_date": region_today().isoformat(),
        "previous_crop_ids": [],
        "priorities": EJEMPLO_PRIORIDADES,
        **campos,
    }


def consultar(cliente: TestClient, **campos) -> dict:
    respuesta = cliente.post("/api/v1/rotations", json=cuerpo(**campos))
    assert respuesta.status_code == 200, respuesta.text
    m.RotationResponse.model_validate(respuesta.json())
    return respuesta.json()


@pytest.fixture
def api(datos) -> TestClient:  # noqa: F811
    return TestClient(app)


# ---------- la forma y las versiones ----------


def test_responde_con_la_forma_del_contrato_y_las_versiones(api, datos):  # noqa: F811
    respuesta = consultar(api, cycles=2)
    assert respuesta["versions"]["dataset"] and respuesta["versions"]["rules"]
    assert respuesta["weights"] == EJEMPLO_PRIORIDADES
    assert set(respuesta["excluded_counts"]) == {"rule", "not_suitable", "soil_ph", "high_risk"}
    assert 0 < len(respuesta["strategies"]) <= 10
    assert [s["rank"] for s in respuesta["strategies"]] == list(range(1, len(respuesta["strategies"]) + 1))
    for estrategia in respuesta["strategies"]:
        assert estrategia["kind"] == "suggested"
        assert len(estrategia["cycles"]) == len(estrategia["crop_ids"]) == 2
        assert set(estrategia["soil_health"]) == {"nitrogen", "organic_carbon", "soil_cover", "pest_break", "erosion"}
        assert 2 <= len(estrategia["reasons"]) <= 4
    assert respuesta["soil_basis"] == respuesta["slope_basis"] == "municipality"
    assert "Compara estrategias según reglas con fuente. No predice cuánto va a mejorar el suelo" in respuesta["limitations"]


def test_misma_entrada_misma_respuesta(api):
    """R4: dos consultas iguales dan la misma respuesta."""
    assert consultar(api, cycles=2, current_crop_ids=["papa", "arveja"]) == consultar(api, cycles=2, current_crop_ids=["papa", "arveja"])


def test_el_primer_ciclo_es_el_diagnostico_de_esa_ventana(api):
    respuesta = consultar(api, cycles=2)
    primero = respuesta["strategies"][0]["cycles"][0]
    diagnostico = api.post(
        "/api/v1/diagnostics",
        json={"municipality_id": EJEMPLO_FRIO, "crop_id": primero["crop_id"], "sowing_date": primero["sowing_date"]},
    ).json()
    assert primero["diagnosis"]["signals"] == diagnostico["signals"]
    assert primero["light"] == diagnostico["overall"]["light"]


# ---------- excluidas ----------


def test_hasta_diez_excluidas_con_su_motivo_y_los_conteos_de_todas(api):
    respuesta = consultar(api, previous_crop_ids=["haba"])
    assert 0 < len(respuesta["excluded"]) <= 10
    assert sum(respuesta["excluded_counts"].values()) >= len(respuesta["excluded"])
    for excluida in respuesta["excluded"]:
        assert excluida["reason"] and excluida["source_ids"]
        assert excluida["kind"] in respuesta["excluded_counts"]
        sugeridas = [s["crop_ids"] for s in respuesta["strategies"]]
        assert excluida["crop_ids"] not in sugeridas


def test_un_cultivo_no_apto_se_excluye_con_la_razon_de_diagnostics(api):
    respuesta = consultar(api, municipality_id=EJEMPLO_CALIDO, cycles=2)
    assert respuesta["excluded_counts"]["not_suitable"] > 0
    assert all("papa" not in s["crop_ids"] for s in respuesta["strategies"])


def test_sin_estrategias_validas_responde_200_con_strategies_vacia(api, monkeypatch):
    # Solo dos candidatas, las dos con dos leguminosas seguidas: la regla `familia_seguida` las descarta.
    monkeypatch.setattr(rotations_module, "candidates", lambda crops, cycles: [("arveja", "haba"), ("haba", "arveja")])
    respuesta = consultar(api, cycles=2)
    assert respuesta["strategies"] == []
    assert respuesta["excluded_counts"]["rule"] == 2
    assert {tuple(e["crop_ids"]) for e in respuesta["excluded"]} == {("arveja", "haba"), ("haba", "arveja")}
    assert all(e["rule_id"] == "familia_seguida" for e in respuesta["excluded"])


# ---------- la rotación actual (HU-223, endpoint) ----------


def test_papa_papa_papa_viene_en_current_strategy_con_la_regla_de_familia_en_issues(api):
    respuesta = consultar(api, current_crop_ids=["papa", "papa", "papa"])
    actual = respuesta["current_strategy"]
    assert (actual["kind"], actual["rank"], actual["crop_ids"]) == ("current", None, ["papa", "papa", "papa"])
    reglas = {i["rule_id"] for i in actual["issues"] if i["kind"] == "rule"}
    assert {"familia_seguida", "papa_seguida"} <= reglas
    assert all(i["source_ids"] for i in actual["issues"])
    # Nunca se excluye en silencio ni se repite entre las sugeridas (R3).
    assert all(e["crop_ids"] != ["papa", "papa", "papa"] for e in respuesta["excluded"])
    assert all(s["crop_ids"] != ["papa", "papa", "papa"] for s in respuesta["strategies"])
    assert actual["cycles"] and set(actual["soil_health"]) == {"nitrogen", "organic_carbon", "soil_cover", "pest_break", "erosion"}
    assert actual["reasons"][0].startswith("Es la rotación que usted viene haciendo")


def test_con_la_actual_y_dos_sugeridas_se_comparan_al_menos_tres(api):
    respuesta = consultar(api, current_crop_ids=["papa", "avena_vicia", "arveja"])
    actual = respuesta["current_strategy"]
    assert actual is not None and len(respuesta["strategies"]) >= 2
    assert NO_CURRENT_LIMITATION not in respuesta["limitations"]
    for estrategia in respuesta["strategies"]:
        assert estrategia["crop_ids"] != actual["crop_ids"]  # la igual a la actual no se repite
        for criterio in CRITERIOS:
            esperado = (
                None
                if estrategia["scores"][criterio] is None or actual["scores"][criterio] is None
                else estrategia["scores"][criterio] - actual["scores"][criterio]
            )
            assert estrategia["vs_current"][criterio] == esperado
        total = (
            None
            if estrategia["total_score"] is None or actual["total_score"] is None
            else estrategia["total_score"] - actual["total_score"]
        )
        assert estrategia["vs_current"]["total"] == total


def test_la_actual_corta_se_repite_desde_el_primero(api):
    actual = consultar(api, current_crop_ids=["papa", "arveja"])["current_strategy"]
    assert actual["crop_ids"] == ["papa", "arveja", "papa"]


def test_la_actual_larga_se_recorta_y_las_limitaciones_lo_dicen(api):
    respuesta = consultar(api, cycles=2, current_crop_ids=["papa", "avena_vicia", "arveja"])
    assert respuesta["current_strategy"]["crop_ids"] == ["papa", "avena_vicia"]
    assert any(t.startswith("Su rotación tiene 3 cultivos; con 2 ciclos se compararon papa y avena") for t in respuesta["limitations"])


def test_sin_rotacion_actual_no_hay_referencia_ni_vs_current(api):
    respuesta = consultar(api, cycles=2)
    assert respuesta["current_strategy"] is None
    assert all(s["vs_current"] is None for s in respuesta["strategies"])
    assert NO_CURRENT_LIMITATION in respuesta["limitations"]


# ---------- el lote, la sesión y R9 ----------


def test_con_lot_id_y_sin_sesion_responde_401(api, client):
    respuesta = client.post("/api/v1/rotations", json=cuerpo(lot_id="00000000-0000-4000-8000-000000000001"))
    assert respuesta.status_code == 401


def test_con_un_lote_ajeno_o_inexistente_responde_404(api, client):
    register(client, "rosa.rotacion")
    lot_id = create_lot(client)
    assert client.post("/api/v1/auth/logout").status_code == 204
    register(client, "fabio.rotacion")
    for otro in (lot_id, "00000000-0000-4000-8000-000000000001"):
        respuesta = client.post("/api/v1/rotations", json=cuerpo(lot_id=otro, cycles=2))
        assert respuesta.status_code == 404, respuesta.json()


@pytest.fixture
def suelo(datos):  # noqa: F811
    """Suelo del municipio y rejilla con pendiente para un lote dibujado: cifras de EJEMPLO (R5)."""
    filas = [
        {
            "cell_id": cell_id(5.49125, lon),
            "altitude_m": 2700.0,
            "slope_pct": pendiente,
            **dict.fromkeys(SOIL_COLUMNS, 10.0),
            "ph": 5.6,
            "ph_p05": 5.2,
            "ph_p95": 6.0,
            "texture_class": "franco",
            "quality": "ok",
            "source_ids": ["ejemplo"],
        }
        for lon, pendiente in [(-73.48375, 18.0), (-73.48625, 2.0)]
    ]
    pl.DataFrame(filas).write_parquet(datos / "grid_cells.parquet")
    municipio = {
        "municipality_id": EJEMPLO_FRIO,
        **dict.fromkeys(SOIL_COLUMNS, 10.0),
        "ph": 5.5,
        "ph_p05": 5.1,
        "ph_p95": 5.9,
        "texture_class": "arcilloso",
        "cells": 30,
        "quality": "ok",
        "source_id": "ejemplo",
    }
    pl.DataFrame([municipio]).write_parquet(datos / "soil_municipality.parquet")
    return datos


def test_con_lote_dibujado_el_suelo_y_la_pendiente_son_del_lote_y_no_escribe_nada(suelo, client, db):
    register(client, "rosa.rotacion")
    contorno = mapping(box(-73.487, 5.4905, -73.483, 5.492))
    dibujado = create_lot(client, geometry=contorno)
    sin_dibujo = create_lot(client, name="El Bajo")
    antes, contenido = rows(db), dump(db)
    with capture_logs() as logs:
        lote = consultar(client, lot_id=dibujado, cycles=2, current_crop_ids=["papa", "arveja"])
        municipio = consultar(client, lot_id=sin_dibujo, cycles=2)
        libre = consultar(client, cycles=2)
    assert rows(db) == antes and dump(db) == contenido  # R9: ninguna tabla cambia
    assert (lote["soil_basis"], lote["slope_basis"]) == ("lot", "lot")
    assert (municipio["soil_basis"], municipio["slope_basis"]) == ("municipality", "municipality")
    assert (libre["soil_basis"], libre["slope_basis"]) == ("municipality", "municipality")
    # Pendiente del lote: la mediana de 18 y 2 es 10 %, por debajo del 12 % de `erosion_pendiente`.
    erosion = lote["strategies"][0]["soil_health"]["erosion"]
    assert erosion["status"] == "available" and "10,0 %" in erosion["reasons"][0]
    # El carbono del suelo llega a `organic_carbon` (HU-184) con la fuente del suelo.
    carbono = lote["strategies"][0]["soil_health"]["organic_carbon"]
    assert carbono["status"] == "available" and "ejemplo" in carbono["source_ids"]
    assert all(LOT_SOIL_LIMITATION in s["limitations"] for s in municipio["strategies"])
    assert any("250 m" in t for t in lote["limitations"])  # rótulo de estimación (R10)
    # Al log no van el municipio, los cultivos, la fecha, las prioridades ni el lote (R9).
    texto = str([{k: v for k, v in e.items() if k != "request_id"} for e in logs])
    for valor in (EJEMPLO_FRIO, dibujado, sin_dibujo, "papa", "arveja", region_today().isoformat(), "El Alto"):
        assert valor not in texto, valor
