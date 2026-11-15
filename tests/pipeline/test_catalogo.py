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


def test_el_forraje_es_true_en_maiz_arveja_y_avena_vicia_y_nulo_en_los_demas():
    """HU-227 (Felipe, 15 nov 2026, PR #155): `forage` es booleano anulable; `true` con fuente en maíz, arveja y avena con
    vicia; nulo (sin fuente, R1) en haba, zanahoria, papa, cebolla de bulbo y descanso."""
    crops, _, sources = build()
    assert crops.schema["forage"] == pl.Boolean
    forage = dict(zip(crops["crop_id"].to_list(), crops["forage"].to_list(), strict=True))
    assert {k for k, v in forage.items() if v} == {"maiz", "arveja", "avena_vicia"}
    assert {k for k, v in forage.items() if v is None} == {"haba", "zanahoria", "papa", "cebolla_bulbo", "descanso"}
    cited = dict(zip(crops["crop_id"].to_list(), crops["source_ids"].to_list(), strict=True))
    for crop_id, source in {
        "maiz": "feedipedia_maize_stover",
        "arveja": "feedipedia_pea_forage",
        "avena_vicia": "feedipedia_oat_forage",
    }.items():
        assert source in cited[crop_id]
        assert source in set(sources["source_id"].to_list())
    # Las otras dos fuentes de la avena con vicia y la de Agrosavia están registradas, aunque cada valor cita una sola.
    assert {"feedipedia_common_vetch", "agrosavia_altoandina_2020"} <= set(sources["source_id"].to_list())
    # No se registran las que no sostienen ningún valor.
    assert not {"feedipedia_faba_bean", "feedipedia_carrot", "feedipedia_maize_silage"} & set(sources["source_id"].to_list())


def test_un_forraje_falso_con_fuente_se_publica_como_falso():
    crops, _, _ = build(lambda d: crop(d, "papa").update(forage={"v": False, "s": "feedipedia_pea_forage"}))
    assert crops.filter(pl.col("crop_id") == "papa")["forage"].to_list() == [False]


def test_solo_la_avena_con_vicia_tiene_segunda_familia():
    crops, _, _ = build()
    assert crops.schema["secondary_families"] == pl.List(pl.String)
    by_id = dict(zip(crops["crop_id"].to_list(), crops["secondary_families"].to_list(), strict=True))
    assert by_id.pop("avena_vicia") == ["Leguminosae"]
    assert all(v == [] for v in by_id.values())
    row = crops.filter(crops["crop_id"] == "avena_vicia")["source_ids"].to_list()[0]
    assert "fao_ecocrop" in row


def test_el_descanso_dura_180_dias_y_solo_el_lleva_fallow_days():
    """HU-063 (decisión 7 del PR #109; contrato aprobado por Haider el 15 de noviembre de 2026): el descanso dura un valor
    fijo de su ficha, 180 días con `criterio_equipo_2026`, y su `cycle_months` sale de ahí (180 / 30,44 = 5,9)."""
    crops, stages, sources = build()
    assert crops.schema["fallow_days"] == pl.Int32
    by_id = {row["crop_id"]: row for row in crops.to_dicts()}
    descanso = by_id.pop("descanso")
    assert (descanso["fallow_days"], descanso["cycle_months"]) == (180, 5.9)
    assert "criterio_equipo_2026" in descanso["source_ids"]
    assert all(row["fallow_days"] is None for row in by_id.values())
    assert "descanso" not in set(stages["crop_id"].to_list())
    # La fuente es la misma de `catalog/rotation_rules.yaml` (R8).
    assert "criterio_equipo_2026" in set(sources["source_id"].to_list())


def test_un_descanso_sin_duracion_con_nota_queda_sin_cycle_months():
    """Sin el dato (nulo y con su nota), el descanso no tiene duración: quien lo usa lo trata como dato que falta (R1)."""
    crops, _, _ = build(lambda d: crop(d, "descanso").update(fallow_days={"v": None, "n": "Sin decidir"}))
    descanso = crops.filter(crops["crop_id"] == "descanso").to_dicts()[0]
    assert (descanso["fallow_days"], descanso["cycle_months"]) == (None, None)
    assert "criterio_equipo_2026" not in descanso["source_ids"]


def test_un_dato_sin_fuente_va_nulo_y_dice_por_que():
    crops, stages, _ = build()
    # Sin una fuente que dé la temperatura de daño en la fase vegetativa, la helada del haba en esas etapas queda sin dato
    # (R1); en la floración sí hay fuente (HU-142).
    haba = stages.filter(stages["crop_id"] == "haba").sort("stage")
    assert dict(zip(haba["stage"].to_list(), haba["frost_sensitive"].to_list(), strict=True)) == {
        "development": None,
        "initial": None,
        "mid": True,
    }
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
        (lambda d: crop(d, "papa").update(article={"v": "los", "s": "agrosense_diseno"}), "`article`"),
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
        # HU-142: la sensibilidad de una etapa va con su propia fuente (R8).
        (lambda d: crop(d, "papa")["stages"]["list"][0].update(frost_sensitive=True), r"\{v: true o false, s: fuente\}"),
        (lambda d: crop(d, "papa")["stages"]["list"][0].update(heat_sensitive={"v": True}), "no cita una fuente"),
        (lambda d: crop(d, "papa")["stages"]["list"][0].update(heat_sensitive={"v": True, "s": "inventada"}), "no cita una fuente"),
        (lambda d: crop(d, "papa")["stages"]["list"][0].update(frost_sensitive={"v": "sí", "s": "fao_ecocrop"}), "true o false"),
        # HU-144: la raíz va completa, ordenada y con `p` entre 0 y 1.
        (lambda d: crop(d, "papa").pop("depletion_p"), "completa"),
        (lambda d: crop(d, "papa").update(root_depth_min_m={"v": 0.9, "s": "fao_56_tabla_22"}), "la mínima primero"),
        (lambda d: crop(d, "papa").update(depletion_p={"v": 1.5, "s": "fao_56_tabla_22"}), "entre 0 y 1"),
        # HU-063: `fallow_days` es solo del descanso, en días enteros mayores que cero, y el descanso no lleva etapas.
        (lambda d: crop(d, "papa").update(fallow_days={"v": 90, "s": "criterio_equipo_2026"}), "solo del descanso"),
        (lambda d: crop(d, "avena_vicia").update(fallow_days={"v": 90, "s": "criterio_equipo_2026"}), "solo del descanso"),
        (lambda d: crop(d, "descanso").update(fallow_days={"v": 0, "s": "criterio_equipo_2026"}), "mayor que cero"),
        (lambda d: crop(d, "descanso").update(fallow_days={"v": 90.5, "s": "criterio_equipo_2026"}), "entero de días"),
        (lambda d: crop(d, "descanso").update(fallow_days={"v": True, "s": "criterio_equipo_2026"}), "entero de días"),
        (lambda d: crop(d, "descanso").update(fallow_days={"v": 180, "s": "inventada"}), "no cita una fuente"),
        (lambda d: crop(d, "descanso").update(fallow_days={"v": None}), "nulo y no dice por qué"),
        (lambda d: crop(d, "descanso").update(stages=crop(d, "papa")["stages"]), "no lleva etapas"),
        # HU-227 (R8): un `forage` con valor lleva una fuente que existe; el descanso no lo lleva.
        (lambda d: crop(d, "maiz").update(forage={"v": True}), "no cita una fuente"),
        (lambda d: crop(d, "maiz").update(forage={"v": False}), "no cita una fuente"),
        (lambda d: crop(d, "maiz").update(forage={"v": True, "s": "inventada"}), "no cita una fuente"),
        (lambda d: crop(d, "papa").update(forage={"v": None}), "nulo y no dice por qué"),
        (lambda d: crop(d, "papa").update(forage={"v": "sí", "s": "feedipedia_pea_forage"}), "true, false o nulo"),
        (lambda d: crop(d, "descanso").update(forage={"v": True, "s": "feedipedia_oat_forage"}), "no lleva `forage`"),
    ],
)
def test_un_catalogo_que_no_cumple_no_se_publica(change, message):
    with pytest.raises(catalog.CatalogError, match=message):
        build(change)


def test_la_sensibilidad_de_cada_etapa_dice_su_propia_fuente():
    """HU-142 (aprobado por Felipe el 13 de noviembre de 2026): `frost_source_id` y `heat_source_id` son la fuente de cada
    sensibilidad, distinta de la de los días y el Kc (`source_id`); nulas cuando el valor es nulo, y ninguna queda fuera
    de `source_ids` del cultivo (R8)."""
    crops, stages, _ = build()
    for flag, source in (("frost_sensitive", "frost_source_id"), ("heat_sensitive", "heat_source_id")):
        assert stages.filter(stages[flag].is_null() != stages[source].is_null()).is_empty()
    cited = dict(zip(crops["crop_id"].to_list(), crops["source_ids"].to_list(), strict=True))
    for row in stages.iter_rows(named=True):
        for source in (row["frost_source_id"], row["heat_source_id"]):
            assert source is None or source in cited[row["crop_id"]]


def test_un_valor_nulo_de_sensibilidad_no_lleva_fuente():
    def change(d):
        crop(d, "papa")["stages"]["list"][0].update(heat_sensitive={"v": None, "s": "fao_ecocrop"})

    _, stages, _ = build(change)
    papa = stages.filter((stages["crop_id"] == "papa") & (stages["stage"] == "initial"))
    assert papa.select("heat_sensitive", "heat_source_id").row(0) == (None, None)


def test_un_limite_nulo_con_fuente_es_un_rango_abierto():
    """La UPRA no pone techo a la cebolla de bulbo: el máximo va nulo, con su fuente, y el catálogo es válido."""
    crops, _, _ = build()
    assert crops.filter(crops["crop_id"] == "cebolla_bulbo")["tmean_max_c"].to_list() == [None]


def test_secondary_families_se_publica_ordenada_sin_depender_del_orden_del_yaml():
    # R4: dos órdenes del YAML dan la misma lista publicada.
    def published(order):
        crops, _, _ = build(lambda d: crop(d, "avena_vicia").update(secondary_families={"v": order, "s": "fao_ecocrop"}))
        return crops.filter(pl.col("crop_id") == "avena_vicia")["secondary_families"].to_list()[0]

    assert published(["Solanaceae", "Leguminosae"]) == published(["Leguminosae", "Solanaceae"]) == ["Leguminosae", "Solanaceae"]
