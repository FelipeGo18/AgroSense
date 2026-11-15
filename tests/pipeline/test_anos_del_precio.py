"""HU-073 (decisión 17): los años en que el precio del mes quedó por encima y por debajo del promedio de su año
(`years_above`, `years_below` en `market_price_season` y `market_month`) y la central por cultivo
(`region.crop_market_overrides`). Los precios son de prueba, salvo los del dataset publicado, que se leen sin cambiarlo.
"""

import io

import polars as pl
import pytest

from pipeline import build
from pipeline.sources import dane, sipsa
from tests.conftest import SAMPLE_MARKETS, SAMPLE_META, SAMPLE_MUNICIPALITIES, SAMPLE_REGION, sipsa_row, sipsa_xml

CROPS = {"papa": {"product_id": "papa-negra"}}


def read(xml_rows: list[str]) -> pl.DataFrame:
    return sipsa.prices(io.BytesIO(sipsa_xml(xml_rows).encode()), SAMPLE_MARKETS)


def rows(years: range, price) -> list[str]:
    return [sipsa_row("1", "Papa negra*", f"{y}-{m:02d}-15", price(y, m), price(y, m), price(y, m)) for y in years for m in range(1, 13)]


def price(year: int, month: int) -> int:
    """Marzo caro en 2021 y 2022 y barato en 2023; octubre siempre barato; los demás meses, todos iguales, salvo por
    marzo y octubre. Con la inflación doblando el precio cada año, que el conteo no ve."""
    base = 1000 * 2 ** (year - 2021)
    if month == 3:
        return base * (2 if year < 2023 else 0.5)
    if month == 10:
        return base // 2
    return base


def season() -> pl.DataFrame:
    return sipsa.seasonal(read(rows(range(2021, 2024), price)))


def month(table: pl.DataFrame, number: int) -> dict:
    return table.filter(pl.col("month") == number).row(0, named=True)


def test_cuenta_los_anos_por_encima_y_por_debajo_con_los_mismos_cocientes_del_indice():
    table = season()
    march, october = month(table, 3), month(table, 10)
    assert (march["years"], march["years_above"], march["years_below"]) == (3, 2, 1)
    assert (october["years_above"], october["years_below"]) == (0, 3)
    # Un mes cualquiera queda por debajo del promedio en los años en que marzo fue caro y por encima cuando fue barato.
    january = month(table, 1)
    assert (january["years_above"], january["years_below"]) == (1, 2)


def test_contar_no_es_promediar():
    """Marzo: el índice dice «por encima» (promedia un marzo muy caro) y los años también (2 de 3); un año con marzo
    muy caro no cambia el conteo de los demás. El índice y los años salen de los mismos cocientes."""
    march = month(season(), 3)
    assert march["seasonal_index"] > 1
    assert march["years_above"] + march["years_below"] <= march["years"]


def test_un_mes_igual_al_promedio_de_su_ano_no_cuenta_en_ninguno():
    """Todos los meses al mismo precio: cada cociente es 1, así que es un empate en los tres años."""
    flat = sipsa.seasonal(read(rows(range(2021, 2024), lambda y, m: 1000)))
    assert set(flat["years_above"].to_list()) == {0} and set(flat["years_below"].to_list()) == {0}
    assert set(flat["years"].to_list()) == {3}


def test_el_empate_es_con_el_cociente_redondeado_a_tres_decimales():
    """Un cociente de 1,0004 redondea a 1,000: empate. Uno de 1,002 cuenta por encima."""
    assert sipsa.RATIO_DECIMALS == 3

    def tiny(year: int, number: int) -> float:
        # Enero un poco más caro: 1,0004 veces el promedio en 2021 y 1,002 en 2022 y 2023 (aprox.).
        if number == 1:
            return 100_000 * (1.00044 if year == 2021 else 1.0022)
        return 100_000

    january = month(sipsa.seasonal(read(rows(range(2021, 2024), tiny))), 1)
    assert (january["years_above"], january["years_below"]) == (2, 0)


def test_market_month_trae_los_anos_y_el_periodo_de_la_temporada():
    prices = read(rows(range(2021, 2024), price) + [sipsa_row("1", "Papa negra*", "2024-01-15", 9000, 9000, 9000)])
    table = sipsa.monthly(prices, sipsa.seasonal(prices), CROPS)
    march = month(table, 3)
    assert (march["years"], march["years_above"], march["years_below"], march["first_year"], march["last_year"]) == (3, 2, 1, 2021, 2023)
    assert list(table.columns) == list(sipsa.MONTH_SCHEMA)


def test_el_build_rechaza_anos_que_no_cuadran():
    table = season()
    with pytest.raises(build.ValidationError, match="no cuadran"):
        build.validate_years_counted("market_price_season", table.with_columns(pl.lit(3, dtype=pl.Int16).alias("years_below")))
    with pytest.raises(build.ValidationError, match="no cuadran"):
        build.validate_years_counted("market_price_season", table.with_columns(pl.lit(-1, dtype=pl.Int16).alias("years_above")))
    build.validate_years_counted("market_price_season", table)


def test_la_papa_de_corabastos_en_septiembre_con_los_precios_publicados():
    """Criterio de HU-073: con los precios publicados (los de `desarrollo`), la papa negra de Corabastos en septiembre da
    0 años por encima y 5 por debajo (2021–2025) e índice 0,774. Se recalcula de `market_price_day` sin tocar
    `data/published`. La arveja de Corabastos en mayo, de la prueba de HU-241, da 5 de 5."""
    path = build.PUBLISHED / "market_price_day.parquet"
    if not path.exists():
        pytest.skip("data/published no trae precios en esta imagen")
    table = sipsa.seasonal(pl.read_parquet(path))
    papa = table.filter((pl.col("product_id") == "papa-negra") & (pl.col("market_id") == "1") & (pl.col("month") == 9)).row(0, named=True)
    assert (papa["years_above"], papa["years_below"], papa["years"], papa["first_year"], papa["last_year"]) == (0, 5, 5, 2021, 2025)
    assert papa["seasonal_index"] == pytest.approx(0.774)
    arveja = table.filter((pl.col("product_id") == "arveja-verde-en-vaina") & (pl.col("market_id") == "1") & (pl.col("month") == 5)).row(
        0, named=True
    )
    assert (arveja["years_above"], arveja["years"]) == (5, 5)
    build.validate_years_counted("market_price_season", table)


# ---------- La central por cultivo (crop_market_overrides) ----------

PAPA_OVERRIDE = {"15": {"papa": {"market_id": "1", "reason": "Tunja no publica papa negra"}}}


def region(overrides) -> dict:
    return {
        "dataset_version": "0.0.0-pruebas",
        "region": {
            **SAMPLE_REGION["region"],
            "markets": SAMPLE_MARKETS,
            "department_markets": {"15": "9", "25": "1"},
            "crop_market_overrides": overrides,
        },
    }


def test_la_region_del_repositorio_manda_la_papa_de_boyaca_a_corabastos():
    loaded = build.load_region()
    assert loaded["region"]["crop_market_overrides"] == {
        "15": {
            "papa": {
                "market_id": "1",
                "reason": "Tunja no publica papa negra desde el 27 de julio de 2021; su temporada es casi la de Corabastos",
            }
        }
    }
    build.validate_crop_market_overrides(loaded, {"papa", "arveja"})


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"15": {"papa": {"market_id": "99", "reason": "x"}}}, "la central '99' no está en `markets`"),
        ({"15": {"papa": {"market_id": 1, "reason": "x"}}}, "no está en `markets`"),
        ({"52": {"papa": {"market_id": "1", "reason": "x"}}}, "departamentos que no están"),
        ({"15": {"papa": {"market_id": "1", "reason": " "}}}, "sin `reason`"),
        ({"15": {"papa": {"market_id": "1"}}}, "solo `market_id` y `reason`"),
        ({"15": {"yuca": {"market_id": "1", "reason": "x"}}}, "no está en `catalog/crops.yaml`"),
        ({"15": {}}, "cultivo → `market_id`"),
    ],
)
def test_una_central_por_cultivo_mal_escrita_no_se_acepta(overrides, message):
    with pytest.raises(build.ValidationError, match=message):
        build.validate_crop_market_overrides(region(overrides), {"papa"})


def test_una_central_por_cultivo_que_no_existe_hace_fallar_el_build(tmp_path):
    prices = read(rows(range(2021, 2024), price))
    sources = pl.DataFrame([dane.source(SAMPLE_META), sipsa.source(prices, "2026-10-20T15:34:00+00:00")])
    bad = region({"15": {"papa": {"market_id": "2", "reason": "Medellín"}}})
    with pytest.raises(build.ValidationError, match="no está en `markets`"):
        build.publish(bad, dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"]), sources, tmp_path, prices=prices)
    assert not (tmp_path / "manifest.json").exists()


def test_el_manifiesto_publica_la_central_por_cultivo(tmp_path):
    prices = read(rows(range(2021, 2024), price))
    sources = pl.DataFrame([dane.source(SAMPLE_META), sipsa.source(prices, "2026-10-20T15:34:00+00:00")])
    manifest = build.publish(
        region(PAPA_OVERRIDE), dane.municipalities(SAMPLE_MUNICIPALITIES, ["15", "25"]), sources, tmp_path, prices=prices
    )
    assert manifest["region"]["crop_market_overrides"] == PAPA_OVERRIDE
