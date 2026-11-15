"""La versión de las reglas con que responde la API (HU-075; specs/02-contratos.md, «Configuración versionada»; R4).

`versions.rules` de cada respuesta junta tres versiones en un solo texto: la del catálogo (`rules_version` del
manifiesto, la de `catalog/crops.yaml` y `catalog/rotation_rules.yaml`), la de `thresholds.yaml` y la de `weights.yaml`.
Así, si cambian los umbrales o los pesos, cambia la versión de la respuesta, y el mismo resultado se puede reproducir
(aprobado por Felipe el 14 de noviembre de 2026). La forma es la de los metadatos de compilación de SemVer:

    0.1.0+umbrales.1.0.0+pesos.1.0.0

Sin la versión del catálogo (un dataset publicado sin ella) no se inventa una: es nula (R5).
"""

from backend.config.thresholds import get_thresholds
from backend.config.weights import get_default_weights


def rules_version(catalog_version: str | None) -> str | None:
    """La versión de las reglas de una respuesta: catálogo, umbrales y pesos. Nula sin la del catálogo."""
    if not catalog_version:
        return None
    return f"{catalog_version}+umbrales.{get_thresholds().version}+pesos.{get_default_weights().version}"
