"""HU-081, PR B, paso 0: candidatas de una estrategia (specs/01-reglas.md, «Estrategias de rotación»; decisión 15).

Escritas antes del código (HU-121). El motor es Python puro (R6): el catálogo se lee aquí, en la prueba, y se pasa como
`CropInfo`. Los catálogos «de ejemplo» de abajo son datos armados para la prueba (R5), no del catálogo real.
"""

from pathlib import Path

import pytest
import yaml

from backend.engine.rotations.candidates import CropInfo, candidates

CATALOGO = Path(__file__).resolve().parents[2] / "catalog" / "crops.yaml"


def _cultivos_reales() -> list[CropInfo]:
    fichas = yaml.safe_load(CATALOGO.read_text(encoding="utf-8"))["crops"]
    return [
        CropInfo(
            crop_id=f["crop_id"],
            kind=f["kind"]["v"],
            family=f["family"]["v"] if "family" in f else None,
            secondary_families=tuple(f.get("secondary_families", {}).get("v") or ()),
        )
        for f in fichas
    ]


# Catálogo DE EJEMPLO con dos descansos distintos: con uno solo, «mismo crop_id seguido» ya cubre «dos descansos».
EJEMPLO = [
    CropInfo("ejemplo_a", "crop", "FamiliaA"),
    CropInfo("ejemplo_b", "crop", "FamiliaB"),
    CropInfo("ejemplo_f1", "fallow", None),
    CropInfo("ejemplo_f2", "fallow", None),
]


def test_el_catalogo_real_tiene_8_cultivos_de_los_tres_kind():
    reales = _cultivos_reales()
    assert len(reales) == 8
    assert {c.kind for c in reales} == {"crop", "cover", "fallow"}


def test_con_los_8_cultivos_reales_salen_392_con_3_ciclos():
    """HU-081: 8 × 7 × 7 = 392."""
    assert len(candidates(_cultivos_reales(), 3)) == 392


def test_con_los_8_cultivos_reales_salen_56_con_2_ciclos():
    """HU-081: 8 × 7 = 56."""
    assert len(candidates(_cultivos_reales(), 2)) == 56


@pytest.mark.parametrize("ciclos", [2, 3])
def test_ninguna_candidata_repite_el_crop_id_seguido(ciclos):
    secuencias = candidates(_cultivos_reales(), ciclos)
    assert secuencias
    assert all(len(s) == ciclos for s in secuencias)
    assert not [s for s in secuencias if any(a == b for a, b in zip(s, s[1:], strict=False))]


@pytest.mark.parametrize("ciclos", [2, 3])
def test_las_candidatas_son_unicas(ciclos):
    secuencias = candidates(_cultivos_reales(), ciclos)
    assert len(set(secuencias)) == len(secuencias)


def test_con_dos_descansos_distintos_ninguna_candidata_los_pone_seguidos():
    f = {"ejemplo_f1", "ejemplo_f2"}
    secuencias = candidates(EJEMPLO, 3)
    assert secuencias
    assert not [s for s in secuencias if any(a in f and b in f for a, b in zip(s, s[1:], strict=False))]
    # Control: los pares permitidos sí salen (cultivo-descanso y descanso-cultivo).
    assert ("ejemplo_a", "ejemplo_f1", "ejemplo_b") in secuencias
    assert ("ejemplo_f2", "ejemplo_a", "ejemplo_f1") in secuencias


def test_conteo_del_catalogo_de_ejemplo():
    """Pares permitidos: 4 × 3 − 2 (f1-f2 y f2-f1) = 10. Caminos de 3 ciclos: suma de entradas × salidas por ciclo
    medio = 3·3 + 3·3 + 2·2 + 2·2 = 26."""
    assert len(candidates(EJEMPLO, 2)) == 10
    assert len(candidates(EJEMPLO, 3)) == 26


def test_el_orden_es_alfabetico_por_crop_id_ciclo_por_ciclo():
    assert candidates(EJEMPLO, 2) == [
        ("ejemplo_a", "ejemplo_b"),
        ("ejemplo_a", "ejemplo_f1"),
        ("ejemplo_a", "ejemplo_f2"),
        ("ejemplo_b", "ejemplo_a"),
        ("ejemplo_b", "ejemplo_f1"),
        ("ejemplo_b", "ejemplo_f2"),
        ("ejemplo_f1", "ejemplo_a"),
        ("ejemplo_f1", "ejemplo_b"),
        ("ejemplo_f2", "ejemplo_a"),
        ("ejemplo_f2", "ejemplo_b"),
    ]


def test_con_el_catalogo_real_la_primera_y_la_ultima_candidata():
    """Orden alfabético: arveja, avena_vicia, cebolla_bulbo, descanso, haba, maiz, papa, zanahoria."""
    secuencias = candidates(_cultivos_reales(), 3)
    assert secuencias[0] == ("arveja", "avena_vicia", "arveja")
    assert secuencias[-1] == ("zanahoria", "papa", "zanahoria")
    assert secuencias == sorted(secuencias)


def test_el_orden_no_depende_del_orden_de_entrada_y_es_determinista():
    reales = _cultivos_reales()
    esperado = candidates(reales, 3)
    assert candidates(reales, 3) == esperado
    assert candidates(list(reversed(reales)), 3) == esperado


@pytest.mark.parametrize("ciclos", [0, 1, 4])
def test_ciclos_fuera_de_2_a_3_dan_value_error(ciclos):
    with pytest.raises(ValueError):
        candidates(_cultivos_reales(), ciclos)
