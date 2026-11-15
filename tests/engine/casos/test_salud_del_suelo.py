"""Casos de referencia de la salud del suelo (HU-121, PR 1). Casos de EJEMPLO (R5): tablas mínimas de pruebas.

Llaman a `/rotations` con `soil_health` (HU-084). No predicen cuánto mejora el suelo: comparan por reglas.
El dataset de ejemplo no trae carbono orgánico del suelo (SoilGrids), así que `organic_carbon` no tiene dato.
"""

import json

import polars as pl

from tests.engine.casos.conftest import SOIL_CRITERIA, rotacion


def niveles_de(datos, rule_id: str) -> dict:
    """Los cortes de una regla tal como quedan publicados en `rotation_rules` (el PR #62 ya está dentro)."""
    regla = pl.read_parquet(datos / "rotation_rules.parquet").filter(pl.col("rule_id") == rule_id)
    assert regla.height == 1, rule_id
    return json.loads(regla["levels"][0])


def test_ejemplo_sin_carbono_organico_el_criterio_es_insufficient_data(api):
    respuesta = rotacion(api)
    assert respuesta["strategies"]
    for estrategia in respuesta["strategies"]:
        carbono = estrategia["soil_health"]["organic_carbon"]
        assert carbono["status"] == "insufficient_data"
        assert carbono["level"] is None  # R1: nunca se pinta como malo


def test_ejemplo_la_leguminosa_mejora_el_nitrogeno(api, datos, familias):
    # `leguminosa_en_rotacion` publica `levels: {favorable: 1, moderate: 1}`: favorable desde 1 ciclo con leguminosa, sin
    # franja intermedia. Con ninguno, `unfavorable`. Si el catálogo cambia los cortes, el caso falla aquí.
    assert niveles_de(datos, "leguminosa_en_rotacion") == {"favorable": 1, "moderate": 1}
    # Las 10 primeras suelen llevar leguminosa (el suelo pesa): la rotación actual papa–maíz, sin leguminosa, da el otro
    # lado con el mismo cálculo (decisión 14: se evalúa igual que las sugeridas).
    respuesta = rotacion(api, current_crop_ids=["papa", "maiz"])
    assert respuesta["strategies"]
    vistos = set()
    for estrategia in [*respuesta["strategies"], respuesta["current_strategy"]]:
        ciclos = sum(1 for crop_id in estrategia["crop_ids"] if familias[crop_id][1])
        nitrogeno = estrategia["soil_health"]["nitrogen"]
        assert nitrogeno["status"] == "available"
        assert nitrogeno["level"] == ("favorable" if ciclos else "unfavorable"), estrategia["crop_ids"]
        vistos.add(bool(ciclos))
    # Los dos lados: hay estrategias con y sin leguminosa (si todas fueran de un lado, el caso no prueba el corte).
    assert vistos == {True, False}


def test_ejemplo_rotacion_de_referencia_agrosavia_sale_moderate_en_pest_break(api, datos):
    # Papa -> avena con vicia -> arveja (Agrosavia, Tibaitatá). `papa_espera`: Solanaceae, `levels: {favorable: 3, moderate: 2}`.
    # Cálculo (supuesto por confirmar en HU-212: la rotación se repite): entre una papa y la siguiente quedan 2 ciclos de
    # otras familias (avena con vicia, Gramineae; arveja, Leguminosae), que llegan al corte `moderate` (2) y no al
    # `favorable` (3): `moderate`. Con papa -> arveja -> papa (el ejemplo del contrato) queda 1 ciclo, bajo 2: `unfavorable`.
    assert niveles_de(datos, "papa_espera") == {"favorable": 3, "moderate": 2}
    agrosavia = rotacion(api, current_crop_ids=["papa", "avena_vicia", "arveja"])["current_strategy"]["soil_health"]["pest_break"]
    assert (agrosavia["status"], agrosavia["level"]) == ("available", "moderate")
    assert "papa_espera" in agrosavia["rule_ids"]
    sola = rotacion(api, current_crop_ids=["papa", "arveja", "papa"])["current_strategy"]["soil_health"]["pest_break"]
    assert (sola["status"], sola["level"]) == ("available", "unfavorable")


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
