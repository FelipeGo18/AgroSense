"""Casos de referencia de la salud del suelo (HU-121, PR 1). Casos de EJEMPLO (R5): tablas mínimas de pruebas.

Esperan `/rotations` con `soil_health` y van con `xfail(strict=True)`. No predicen cuánto mejora el suelo: comparan por reglas.
El dataset de ejemplo no trae carbono orgánico del suelo (SoilGrids), así que `organic_carbon` no tiene dato.
"""

import pytest

from tests.engine.casos.conftest import SOIL_CRITERIA, rotacion

ESPERA_SUELO = pytest.mark.xfail(strict=True, reason="espera HU-081, HU-213, HU-212 y HU-084")
ESPERA_SUELO_REGLAS = pytest.mark.xfail(strict=True, reason="espera HU-081, HU-213, HU-212, HU-084 y HU-062 (PR #62)")


@ESPERA_SUELO
def test_ejemplo_sin_carbono_organico_el_criterio_es_insufficient_data(api):
    respuesta = rotacion(api)
    assert respuesta["strategies"]
    for estrategia in respuesta["strategies"]:
        carbono = estrategia["soil_health"]["organic_carbon"]
        assert carbono["status"] == "insufficient_data"
        assert carbono["level"] is None  # R1: nunca se pinta como malo


@ESPERA_SUELO_REGLAS
def test_ejemplo_la_leguminosa_mejora_el_nitrogeno(api, familias):
    respuesta = rotacion(api)
    assert respuesta["strategies"]
    for estrategia in respuesta["strategies"]:
        ciclos = sum(1 for crop_id in estrategia["crop_ids"] if familias[crop_id][1])
        nitrogeno = estrategia["soil_health"]["nitrogen"]
        assert nitrogeno["status"] == "available"
        # Supuesto por confirmar (c): los cortes de `legume_cycles` son los del contrato (`favorable` 2, `moderate` 1);
        # lo que la HU fija es «con leguminosa, favorable o moderate; sin ella, unfavorable».
        if ciclos == 0:
            assert nitrogeno["level"] == "unfavorable"
        else:
            assert nitrogeno["level"] in ("favorable", "moderate")


@ESPERA_SUELO_REGLAS
def test_ejemplo_rotacion_de_referencia_agrosavia_no_sale_unfavorable_en_pest_break(api):
    # Papa -> avena con vicia -> arveja (Agrosavia, Tibaitatá). El caso con `papa_espera` en 3 y 2 (`moderate`) necesita
    # cambiar la regla del dataset: queda para cuando el dataset de ejemplo publique `rotation_rules` (TODO(HU-062)).
    respuesta = rotacion(api, current_crop_ids=["papa", "avena_vicia", "arveja"])
    pest_break = respuesta["current_strategy"]["soil_health"]["pest_break"]
    assert pest_break["status"] == "available"
    assert pest_break["level"] != "unfavorable"


@ESPERA_SUELO_REGLAS
def test_ejemplo_forma_de_los_cinco_criterios_de_salud_del_suelo(api, fuentes):
    respuesta = rotacion(api, current_crop_ids=["papa", "avena_vicia", "arveja"])
    estrategias = [*respuesta["strategies"], respuesta["current_strategy"]]
    for estrategia in estrategias:
        assert set(estrategia["soil_health"]) == set(SOIL_CRITERIA)
        for criterio in estrategia["soil_health"].values():
            assert criterio["status"] in ("available", "insufficient_data")
            assert isinstance(criterio["rule_ids"], list)
            assert set(criterio["source_ids"]) <= fuentes  # R8
            if criterio["status"] == "insufficient_data":
                assert criterio["level"] is None  # R1
            else:
                assert criterio["level"] in ("favorable", "moderate", "unfavorable")
                assert criterio["rule_ids"] and criterio["source_ids"]  # sin regla `health` con fuente no hay nivel
