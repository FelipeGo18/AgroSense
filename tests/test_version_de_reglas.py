"""HU-075: `versions.rules` de cada respuesta junta el catálogo, los umbrales y los pesos (R4).

Si cambia `thresholds.yaml` o `weights.yaml`, cambia la versión de la respuesta: el mismo resultado se puede reproducir
(specs/02-contratos.md, «Configuración versionada»; aprobado por Felipe el 14 de noviembre de 2026).
"""

from dataclasses import replace

from backend.config import versions
from backend.config.thresholds import get_thresholds
from backend.config.weights import get_default_weights


def test_junta_las_tres_versiones():
    esperada = f"0.1.0+umbrales.{get_thresholds().version}+pesos.{get_default_weights().version}"
    assert versions.rules_version("0.1.0") == esperada


def test_sin_la_version_del_catalogo_no_se_inventa_una():
    assert versions.rules_version(None) is None
    assert versions.rules_version("") is None


def test_cambiar_los_umbrales_o_los_pesos_cambia_la_version(monkeypatch):
    antes = versions.rules_version("0.1.0")
    monkeypatch.setattr(versions, "get_thresholds", lambda: replace(get_thresholds(), version="1.1.0"))
    con_umbrales = versions.rules_version("0.1.0")
    monkeypatch.setattr(versions, "get_default_weights", lambda: replace(get_default_weights(), version="2.0.0"))
    con_pesos = versions.rules_version("0.1.0")
    assert len({antes, con_umbrales, con_pesos}) == 3
    assert con_pesos == "0.1.0+umbrales.1.1.0+pesos.2.0.0"


def test_cabe_en_la_columna_de_las_temporadas():
    # `seasons.rules_version` es String(40) y guarda la versión del diagnóstico que vio el usuario al sembrar.
    assert len(versions.rules_version("0.1.0")) <= 40
