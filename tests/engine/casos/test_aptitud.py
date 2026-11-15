# ruff: noqa: F401, F811  (los fixtures se importan de datos_reales.py y se piden por nombre)
"""Casos de referencia de la aptitud del cultivo en la zona (HU-121, PR 2; regla 0 de la agregación del semáforo).

REALES: papa en Puerto Salgar y en Duitama, sobre `data/published`. `versions.dataset` se compara con la `dataset_version` de
su `manifest.json`, sea cual sea.
EJEMPLO (R5): Girardot y Samacá con las cifras de clima de `tests/conftest.py`.
"""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from tests.engine.casos.datos_reales import (
    EJEMPLO_CALIDO,
    EJEMPLO_FRIO,
    PUBLICADO,
    cliente,
    consulta,
    datos_reales,
    diagnostico,
    tabla,
    valor,
    version_publicada,
)


def test_real_papa_en_puerto_salgar_no_es_apta(datos_reales):
    # Valor esperado: `municipalities.tmean_annual_c` de 25572 (28,4 °C) frente a `crops.tmean_max_c` de papa (16 °C, UPRA).
    # 28,4 > 16: fuera del rango absoluto, así que `not_suitable` (specs/01-reglas.md, «Aptitud del cultivo en la zona»).
    assert valor(datos_reales, "municipalities", "municipality_id", "25572", "tmean_annual_c") == 28.4
    assert valor(datos_reales, "crops", "crop_id", "papa", "tmean_max_c") == 16.0

    respuesta = consulta(TestClient(app), municipality_id="25572")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["suitability"]["level"] == "not_suitable"
    assert cuerpo["suitability"]["score"] == 0  # fuera del límite absoluto
    assert cuerpo["suitability"]["basis"] == "municipality"
    assert cuerpo["suitability"]["tmean_annual_c"] == 28.4
    assert cuerpo["window"] is None and cuerpo["signals"] is None
    assert not cuerpo.get("best_windows")  # no se evalúan ventanas
    for luz in (cuerpo["overall"], cuerpo["overall_default"]):
        assert (luz["light"], luz["action"]) == ("red", "rotate")
    # La razón cita el dato de la ficha que excluye el cultivo (R5): el valor de la zona y el límite de la ficha.
    razon = " ".join(cuerpo["suitability"]["reasons"])
    assert "28,4 °C" in razon and "hasta 16 °C" in razon and "papa" in razon
    assert cuerpo["versions"]["dataset"] == version_publicada()  # R4


def test_real_la_ficha_que_excluye_a_la_papa_trae_fuentes_que_existen(datos_reales):
    # R8: la respuesta no lleva `source_ids` por valor (`crops` guarda las del cultivo entero): se comprueba en la tabla.
    # Supuesto por confirmar: la HU pide «razón y fuentes que citen la ficha»; hoy la API solo cita la razón.
    fuentes_ficha = valor(datos_reales, "crops", "crop_id", "papa", "source_ids")
    publicadas = set(tabla(datos_reales, "sources")["source_id"].to_list())
    assert "upra_papa_diacol" in fuentes_ficha  # la fuente del rango de temperatura media de la papa
    assert set(fuentes_ficha) <= publicadas


@pytest.mark.parametrize("riego", [True, False, None])
def test_ejemplo_papa_en_girardot_no_es_apta_sin_importar_pesos_ni_riego(cliente, riego):
    # Girardot (EJEMPLO: 28,4 °C) frente a los 16 °C de la papa. La regla 0 no mira pesos ni riego, y la prioridad del agua en 0
    # no la esconde: la luz sigue roja y no se evalúan ventanas. Lo común (forma, razón) lo prueba `tests/test_calculos.py`.
    pesos = {"water": 0, "frost": 0, "heat": 0, "soil": 0, "supply": 5, "market": 0}
    cuerpo = diagnostico(cliente, municipality_id=EJEMPLO_CALIDO, irrigated=riego, priorities=pesos)
    assert cuerpo["suitability"]["level"] == "not_suitable"
    assert cuerpo["window"] is None and cuerpo["signals"] is None and not cuerpo.get("best_windows")
    assert (cuerpo["overall"]["light"], cuerpo["overall"]["action"]) == ("red", "rotate")
    assert (cuerpo["overall_default"]["light"], cuerpo["overall_default"]["action"]) == ("red", "rotate")
    assert cuerpo["weights"] == pesos


def test_ejemplo_la_aptitud_es_determinista(cliente):
    # R4: misma entrada, misma salida (con la versión del dataset y de las reglas en la respuesta).
    primera, segunda = diagnostico(cliente, municipality_id=EJEMPLO_CALIDO), diagnostico(cliente, municipality_id=EJEMPLO_CALIDO)
    assert primera == segunda
    assert primera["versions"]["dataset"] and "rules" in primera["versions"]


# Pasa desde el endpoint de diagnóstico (HU-076, PR #102): se quitó la marca de pendiente.
def test_real_papa_en_duitama_es_apta_con_nota_100(datos_reales):
    # Valor esperado: `municipalities.tmean_annual_c` de 15238 (14,4 °C) dentro del óptimo de papa (`crops.tmean_opt_min_c` 12
    # a `tmean_opt_max_c` 15): la curva da 100 (specs/01-reglas.md, «Aptitud del cultivo en la zona»).
    assert valor(datos_reales, "municipalities", "municipality_id", "15238", "tmean_annual_c") == 14.4
    assert (
        valor(datos_reales, "crops", "crop_id", "papa", "tmean_opt_min_c")
        <= 14.4
        <= valor(datos_reales, "crops", "crop_id", "papa", "tmean_opt_max_c")
    )

    respuesta = consulta(TestClient(app), municipality_id="15238")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["suitability"]["level"] == "suitable" and cuerpo["suitability"]["score"] == 100
    assert cuerpo["suitability"]["tmean_annual_c"] == 14.4
    assert cuerpo["window"] is not None and cuerpo["signals"] is not None  # apta: se evalúa la ventana
    assert cuerpo["versions"]["dataset"] == version_publicada()  # R4


# Pasa desde el endpoint de diagnóstico (HU-076, PR #102): se quitó la marca de pendiente.
def test_ejemplo_ficha_sin_rango_de_temperatura_da_aptitud_insufficient_data_y_no_bloquea(cliente):
    # La ficha real de `cebolla_bulbo` no trae `tmean_max_c` con fuente (catalog/crops.yaml): sin el rango completo, la aptitud
    # es `insufficient_data` (R1, R8). Se evalúa en Samacá (EJEMPLO). Se comprueba el supuesto de la ficha antes de seguir.
    assert valor(PUBLICADO, "crops", "crop_id", "cebolla_bulbo", "tmean_max_c") is None, (
        "la ficha de cebolla_bulbo ya trae tmean_max_c: busque otra sin rango (HU-121)"
    )

    cuerpo = diagnostico(cliente, municipality_id=EJEMPLO_FRIO, crop_id="cebolla_bulbo")
    assert cuerpo["suitability"]["level"] == "insufficient_data"
    assert cuerpo["window"] is not None and cuerpo["signals"] is not None  # no bloquea
    # Supuesto por confirmar: el texto de la limitación no está fijado; se pide que la aptitud quede dicha en `limitations`.
    assert any("aptitud" in texto.lower() or "temperatura" in texto.lower() for texto in cuerpo["limitations"])
