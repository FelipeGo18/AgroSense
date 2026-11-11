"""El catálogo agronómico: fichas con fuente por valor y sus validaciones (EP-06: HU-061, HU-199, HU-063; R8)."""

import copy

import polars as pl
import pytest

from pipeline import catalog

REAL = catalog.load()


def build(changes=None):
    data = copy.deepcopy(REAL)
    if changes:
        changes(data)
    return catalog.build(data)


def crop(data, crop_id):
    return next(c for c in data["crops"] if c["crop_id"] == crop_id)


def test_el_catalogo_real_cumple_el_contrato():
    crops, stages, sources = build()
    # Los 7 cultivos del MVP y el descanso, con los identificadores del diseño.
    assert sorted(crops["crop_id"].to_list()) == ["arveja", "avena_vicia", "cebolla_bulbo", "descanso", "haba", "maiz", "papa", "zanahoria"]
    assert set(stages["crop_id"].to_list()) == {"arveja", "avena_vicia", "cebolla_bulbo", "haba", "maiz", "papa", "zanahoria"}
    # Toda fuente citada está en `sources` (R8).
    cited = {s for ids in crops["source_ids"].to_list() for s in ids} | set(stages["source_id"].to_list())
    assert cited <= set(sources["source_id"].to_list())


def test_la_papa_tiene_la_aptitud_de_la_upra_y_las_etapas_de_fao_56():
    crops, stages, _ = build()
    papa = crops.filter(crops["crop_id"] == "papa").to_dicts()[0]
    # UPRA, papa Diacol Capiro: alta 12-15 °C, no apta < 8 y > 16 °C (decisión 13).
    assert (papa["tmean_min_c"], papa["tmean_opt_min_c"], papa["tmean_opt_max_c"], papa["tmean_max_c"]) == (8, 12, 15, 16)
    # EcoCrop: pH óptimo 5,0-6,2.
    assert (papa["ph_opt_min"], papa["ph_opt_max"]) == (5.0, 6.2)
    rows = stages.filter(stages["crop_id"] == "papa").to_dicts()
    # FAO-56, tabla 11, fila «Idaho, USA»: 45, 30, 70 y 20 días; tabla 12: Kc 0,5 (grupo), 1,15 y 0,75.
    assert [(r["stage"], r["days"], r["kc"]) for r in rows] == [
        ("initial", 45, 0.5),
        ("development", 30, None),
        ("mid", 70, 1.15),
        ("late", 20, 0.75),
    ]
    assert papa["cycle_months"] == round(165 / 30.44, 1)


def test_las_leguminosas_fijan_nitrogeno_y_las_demas_no():
    crops, _, _ = build()
    fixes = dict(zip(crops["crop_id"].to_list(), crops["fixes_nitrogen"].to_list(), strict=True))
    assert {k for k, v in fixes.items() if v} == {"arveja", "haba", "avena_vicia"}


def test_solo_la_avena_con_vicia_tiene_segunda_familia():
    crops, _, _ = build()
    assert crops.schema["secondary_families"] == pl.List(pl.String)
    by_id = dict(zip(crops["crop_id"].to_list(), crops["secondary_families"].to_list(), strict=True))
    assert by_id.pop("avena_vicia") == ["Leguminosae"]
    assert all(v == [] for v in by_id.values())
    row = crops.filter(crops["crop_id"] == "avena_vicia")["source_ids"].to_list()[0]
    assert "fao_ecocrop" in row


def test_un_dato_sin_fuente_va_nulo_y_dice_por_que():
    crops, stages, _ = build()
    # Sin temperatura que la mate en EcoCrop: la sensibilidad a la helada de la haba queda sin dato (R1).
    haba = stages.filter(stages["crop_id"] == "haba")
    assert haba["frost_sensitive"].null_count() == haba.height
    assert crops.filter(crops["crop_id"] == "papa")["root_type"].to_list() == [None]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: crop(d, "papa").update(ph_min={"v": 4.2, "s": "inventada"}), "no cita una fuente"),
        (lambda d: crop(d, "papa").update(base_temp_c={"v": None}), "nulo y no dice por qué"),
        (lambda d: crop(d, "papa").update(tmean_opt_max_c={"v": 18, "s": "upra_papa_diacol"}), "por encima del máximo absoluto"),
        (lambda d: crop(d, "papa").update(tmean_opt_min_c={"v": 16, "s": "upra_papa_diacol"}), "mayor que el máximo"),
        (lambda d: crop(d, "papa").update(kind={"v": "arbusto", "s": "agrosense_diseno"}), "`kind`"),
        (lambda d: crop(d, "papa").update(archetype={"v": "nube", "s": "agrosense_diseno"}), "`archetype`"),
        (lambda d: crop(d, "arveja").update(crop_id="papa"), "repetido"),
        (lambda d: crop(d, "papa").update(crop_id="Papa Criolla"), "snake_case"),
        (lambda d: crop(d, "papa")["stages"]["list"][0].update(s="otra"), "no cita una fuente"),
        (lambda d: crop(d, "papa")["stages"]["list"][0].update(days=0), "mayor que cero"),
        (lambda d: crop(d, "papa")["stages"]["list"][0].update(kc=3), "fuera de 0 a 2"),
        (lambda d: crop(d, "papa")["stages"].update(list=[]), "necesita sus etapas"),
        (lambda d: crop(d, "avena_vicia").update(secondary_families={"v": ["Leguminosae"]}), "no cita una fuente"),
        (lambda d: crop(d, "avena_vicia").update(secondary_families={"v": ["Leguminosa"], "s": "fao_ecocrop"}), "de ninguna ficha"),
        (lambda d: crop(d, "avena_vicia").update(secondary_families={"v": ["Gramineae"], "s": "fao_ecocrop"}), "propia ficha"),
        (lambda d: crop(d, "avena_vicia").update(secondary_families={"v": ["Leguminosae"] * 2, "s": "fao_ecocrop"}), "repetidas"),
        (lambda d: crop(d, "avena_vicia").update(secondary_families={"v": "Leguminosae", "s": "fao_ecocrop"}), "lista de textos"),
    ],
)
def test_un_catalogo_que_no_cumple_no_se_publica(change, message):
    with pytest.raises(catalog.CatalogError, match=message):
        build(change)


def test_un_limite_nulo_con_fuente_es_un_rango_abierto():
    """La UPRA no pone techo a la cebolla de bulbo: el máximo va nulo, con su fuente, y el catálogo es válido."""
    crops, _, _ = build()
    assert crops.filter(crops["crop_id"] == "cebolla_bulbo")["tmean_max_c"].to_list() == [None]
