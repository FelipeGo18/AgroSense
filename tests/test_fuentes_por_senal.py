"""Qué fuente calcula cada señal (`catalog/sources.yaml`, HU-122): su forma, la lluvia temporal y R8."""

from pathlib import Path

import polars as pl
import pytest
import yaml

from common.signal_sources import (
    P0_SIGNALS,
    SIGNAL_SOURCES_FILE,
    SignalSourcesError,
    check_shape,
    check_sources,
    get_signal_sources,
)
from pipeline.build import ADAPTERS

REGION = "co-boyaca-cundinamarca"


def real() -> dict:
    return yaml.safe_load(SIGNAL_SOURCES_FILE.read_text(encoding="utf-8"))


def test_el_archivo_del_repositorio_tiene_las_seis_senales_de_la_region():
    config = get_signal_sources()
    assert config.version
    assert tuple(config.for_region(REGION)) == P0_SIGNALS


def test_la_lluvia_es_de_power_por_ahora_con_su_aviso_e_imerg_por_llegar():
    """Decisión de Felipe del 11 de noviembre de 2026: POWER calcula el agua mientras no exista IMERG (HU-207)."""
    config = get_signal_sources()
    water = config.for_region(REGION)["water"]
    assert (water.used, water.et0) == ("nasa_power", "nasa_power")
    assert water.contrast == ("imerg",) and config.planned["imerg"] == "HU-207"
    assert "sobrestima" in water.caveat and "IDEAM" in water.caveat


def test_cada_fuente_esta_publicada_o_por_llegar_en_el_dataset_del_repositorio():
    """R8 contra lo publicado: hoy POWER y SIPSA están; IMERG, SoilGrids, EVA y SMAP esperan su HU."""
    published = set(pl.read_parquet(Path("data/published/sources.parquet"))["source_id"].to_list())
    assert check_sources(get_signal_sources(), REGION, published, set(ADAPTERS)) == []


def test_una_fuente_que_nadie_conoce_es_un_error():
    data = real()
    data["regions"][REGION]["frost"] = {"used": "nasa_powr"}
    with pytest.raises(SignalSourcesError, match="nasa_powr"):
        check_sources(check_shape(data), REGION, {"nasa_power"}, set(ADAPTERS))


def test_una_fuente_con_adaptador_que_no_se_publico_no_es_un_error_y_se_avisa():
    """Sin la caché de POWER se publica lo demás: la señal será `insufficient_data` (R1), no un pipeline caído."""
    missing = check_sources(get_signal_sources(), REGION, {"dane_divipola", "dane_sipsa"}, set(ADAPTERS))
    assert missing == ["nasa_power"]


def test_una_fuente_de_planned_que_ya_se_publica_tiene_que_salir_de_la_lista():
    with pytest.raises(SignalSourcesError, match="siguen en `planned`"):
        check_sources(get_signal_sources(), REGION, {"nasa_power", "dane_sipsa", "imerg"}, set(ADAPTERS))


def test_una_region_que_no_esta_en_el_archivo_es_un_error():
    with pytest.raises(SignalSourcesError, match="no tiene la región"):
        get_signal_sources().for_region("otra-region")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d["regions"][REGION].pop("heat"), "le faltan las señales: heat"),
        (lambda d: d["regions"][REGION].update(granizo={"used": "x"}), "no son del P0"),
        (lambda d: d["regions"][REGION]["water"].pop("rain"), "rain"),
        (lambda d: d["regions"][REGION]["soil"].pop("used"), "debe tener `used`"),
        (lambda d: d["regions"][REGION]["water"].update(rain_contrast="imerg"), "lista"),
        (lambda d: d["planned"].update(imerg="pronto"), "HU-xxx"),
        (lambda d: d.update(version=1), "version"),
        (lambda d: d.update(regions={}), "al menos una región"),
    ],
)
def test_un_archivo_que_no_cumple_su_forma_no_se_lee(change, message):
    data = real()
    change(data)
    with pytest.raises(SignalSourcesError, match=message):
        check_shape(data)
