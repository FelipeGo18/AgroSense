"""`GET /api/v1/trends` (HU-078): el agua de la ventana por año, el área sembrada del semestre y el verdor normal.

El dataset parte de `data/examples/` (rotulado como ejemplo) y se le cambian la lluvia, la ET0, la oferta y el verdor por
cifras de ejemplo armadas para poder hacer la cuenta a mano (R5). El catálogo y las etapas son los reales (FAO-56).
"""

import math
import shutil
from calendar import monthrange
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from structlog.testing import capture_logs

from backend.api import calc_models as m
from backend.api.main import app
from backend.config.settings import get_settings
from backend.db.models import Base
from common import signal_sources

SAMACA, TUNJA = "15646", "15001"
YEARS = range(2015, 2025)
# Siembra de papa el 2 de agosto: la ventana va del 2 de agosto al 13 de enero (165 días) y pasa al año siguiente.
PAPA_AUGUST = "2027-08-02"


def trends(client: TestClient, municipality_id: str = SAMACA, crop_id: str = "papa", sowing_date: str = PAPA_AUGUST):
    return client.get("/api/v1/trends", params={"municipality_id": municipality_id, "crop_id": crop_id, "sowing_date": sowing_date})


def rain_value(year: int, month: int) -> float:
    """Lluvia de ejemplo: 10 mm por el número del mes; en 2018, 2 mm por día (para una cuenta a mano distinta)."""
    return 2.0 * monthrange(year, month)[1] if year == 2018 else 10.0 * month


def write_dataset(folder: Path, *, supply: bool, ndvi: bool) -> None:
    shutil.copytree(Path("data/examples").resolve(), folder)
    # La lluvia de GPM IMERG (la que define catalog/sources.yaml para la región) solo en Samacá; a octubre de 2017 le falta.
    precip = [
        {
            "municipality_id": SAMACA,
            "year": year,
            "month": month,
            "source_id": "imerg",
            "precip_mm": rain_value(year, month),
            "quality": "ok",
        }
        for year in YEARS
        for month in range(1, 13)
        if (year, month) != (2017, 10)
    ]
    pl.DataFrame(precip, schema_overrides={"year": pl.Int16, "month": pl.Int8}).write_parquet(folder / "precip_month.parquet")
    # La ET0 de NASA POWER en los dos municipios: 4 mm por día. Tunja trae también lluvia de POWER, que no se usa: la
    # fuente de la región es IMERG y nunca se cambia a la de contraste (R1).
    climate = [
        {
            "municipality_id": place,
            "year": year,
            "month": month,
            "precip_mm": 999.0,
            "et0_mm": 4.0 * monthrange(year, month)[1],
            "quality": "ok",
            "source_id": "nasa_power",
        }
        for place in (SAMACA, TUNJA)
        for year in YEARS
        for month in range(1, 13)
    ]
    pl.DataFrame(climate, schema_overrides={"year": pl.Int16, "month": pl.Int8}).write_parquet(folder / "climate_month.parquet")
    if supply:
        rows = [
            {
                "municipality_id": SAMACA,
                "crop_id": "papa",
                "year": year,
                "semester": half,
                "source_id": "eva",
                "planted_ha": area,
                "preliminary": year == 2021,
                "quality": "ok",
            }
            for year, half, area in ((2021, "B", 130.0), (2019, "B", 110.0), (2020, "B", 120.0), (2020, "A", 90.0))
        ]
        # Otra fuente del mismo indicador: no se mezcla con la de la región (EVA).
        rows.append(
            {
                "municipality_id": SAMACA,
                "crop_id": "papa",
                "year": 2022,
                "semester": "B",
                "source_id": "faostat",
                "planted_ha": 5.0,
                "preliminary": False,
                "quality": "ok",
            }
        )
        pl.DataFrame(rows, schema_overrides={"year": pl.Int16}).write_parquet(folder / "supply_semester.parquet")
    else:
        (folder / "supply_semester.parquet").unlink()
    if ndvi:
        rows = [
            {
                "municipality_id": SAMACA,
                "period": period,
                "ndvi_normal": round(0.4 + period / 100, 2),
                "years": 20,
                "quality": "partial" if period == 12 else "ok",
                "source_id": "modis_ndvi",
            }
            for period in reversed(range(1, 24))
        ]
        pl.DataFrame(rows, schema_overrides={"period": pl.Int8, "years": pl.Int16}).write_parquet(
            folder / "ndvi_municipality_normal.parquet"
        )
    else:
        (folder / "ndvi_municipality_normal.parquet").unlink()


def use(folder: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGROSENSE_DATA_DIR", str(folder))
    get_settings.cache_clear()


@pytest.fixture
def published_like(tmp_path, monkeypatch):
    """Un dataset con lluvia y ET0, sin `supply_semester` ni `ndvi_municipality_normal`: el caso sin oferta ni verdor. El
    publicado trae `supply_semester` desde HU-031; ese caso es el de `complete`."""
    folder = tmp_path / "published"
    write_dataset(folder, supply=False, ndvi=False)
    use(folder, monkeypatch)
    return folder


@pytest.fixture
def complete(tmp_path, monkeypatch):
    """Con las cinco tablas: lluvia, ET0, oferta y verdor."""
    folder = tmp_path / "published"
    write_dataset(folder, supply=True, ndvi=True)
    use(folder, monkeypatch)
    return folder


# ---------- agua ----------


def test_el_agua_trae_por_anio_la_lluvia_y_la_necesidad_de_la_ventana(published_like):
    response = trends(TestClient(app))
    assert response.status_code == 200
    body = response.json()
    m.TrendsResponse.model_validate(body)
    assert body["request"] == {"municipality_id": SAMACA, "crop_id": "papa", "sowing_date": PAPA_AUGUST}
    water = body["water"]
    assert (water["status"], water["source_id"], water["unit"]) == ("available", "imerg", "mm")
    points = {point["year"]: point for point in water["points"]}
    # Cuenta a mano de 2015, con la lluvia prorrateada por día: agosto 80 × 30/31, septiembre a diciembre enteros
    # (90 + 100 + 110 + 120) y enero de 2016, 10 × 13/31. Total 501,6 mm.
    assert points[2015]["precip_mm"] == pytest.approx(round(80 * 30 / 31 + 420 + 10 * 13 / 31, 1))
    # En 2018 llueven 2 mm por día de agosto a diciembre; enero de 2019 vuelve a 10 mm: 2 × 152 + 10 × 13/31 = 308,2.
    assert points[2018]["precip_mm"] == pytest.approx(round(2 * 152 + 10 * 13 / 31, 1))
    # La necesidad: 4 mm de ET0 por día por Σ Kc de la papa en FAO-56 (146,875; tests/engine/test_agua_de_la_ventana.py).
    assert points[2015]["need_mm"] == points[2018]["need_mm"] == 587.5


def test_un_anio_sin_la_lluvia_de_un_mes_no_se_inventa(published_like):
    points = {point["year"]: point for point in trends(TestClient(app)).json()["water"]["points"]}
    # A octubre de 2017 le falta la lluvia: el año se muestra sin lluvia, nunca con cero ni con los meses que sí hay.
    assert points[2017]["precip_mm"] is None
    assert points[2017]["need_mm"] == 587.5


def test_una_ventana_que_pasa_de_anio_usa_el_siguiente_y_no_sale_del_periodo(published_like):
    # Arveja sembrada el 2 de noviembre: 110 días, hasta el 19 de febrero.
    body = trends(TestClient(app), crop_id="arveja", sowing_date="2026-11-02").json()
    points = body["water"]["points"]
    # El último año con datos es 2024: su ventana llegaría a 2025, que el dataset no cubre. No es un dato que falta.
    assert [point["year"] for point in points] == list(range(2015, 2024))
    first = points[0]
    # Noviembre 110 × 29/30, diciembre 120, enero de 2016 10 y 19 días de febrero de 2016, que tuvo 29: 20 × 19/29.
    assert first["precip_mm"] == pytest.approx(round(110 * 29 / 30 + 120 + 10 + 20 * 19 / 29, 1))
    # Σ Kc de la arveja: 17,5 + 20,95 + 34,5 + 22,475 = 95,425; por 4 mm de ET0 al día.
    assert first["need_mm"] == pytest.approx(381.7)


def drop_rain(folder: Path, *months: tuple[int, int]) -> None:
    """Quita del dataset las filas de lluvia de esos meses: el periodo que la fuente publica se acorta."""
    table = pl.read_parquet(folder / "precip_month.parquet")
    keep = ~pl.any_horizontal([(pl.col("year") == year) & (pl.col("month") == month) for year, month in months])
    table.filter(keep).write_parquet(folder / "precip_month.parquet")


def test_el_ultimo_anio_parcial_queda_fuera_del_periodo(published_like):
    # Como IMERG en data/published: el último año llega solo hasta septiembre.
    drop_rain(published_like, *((2024, month) for month in range(10, 13)))
    client = TestClient(app)
    # La papa del 2 de agosto llega a enero: la ventana de 2024 pasa de septiembre de 2024 y no entra. La de 2023 sí,
    # entera (agosto de 2023 a enero de 2024): el periodo es por (año, mes), no por año.
    points = trends(client).json()["water"]["points"]
    assert [point["year"] for point in points] == list(range(2015, 2024))
    assert points[-1]["precip_mm"] is not None
    # La arveja del 1 de marzo termina en junio: su ventana de 2024 cae entera antes de septiembre y entra.
    points = trends(client, crop_id="arveja", sowing_date="2027-03-01").json()["water"]["points"]
    assert [point["year"] for point in points] == list(YEARS)
    assert points[-1]["precip_mm"] is not None


def test_el_primer_anio_parcial_queda_fuera_del_periodo(published_like):
    # La fuente empieza en marzo de 2015: una ventana que empieza en febrero no tiene 2015.
    drop_rain(published_like, (2015, 1), (2015, 2))
    points = trends(TestClient(app), crop_id="arveja", sowing_date="2027-02-01").json()["water"]["points"]
    assert [point["year"] for point in points] == list(range(2016, 2025))


def test_un_mes_que_falta_dentro_del_periodo_sigue_dando_lluvia_nula(published_like):
    # Con el último año recortado, a octubre de 2017 le sigue faltando la lluvia: es un dato que falta, no un año fuera.
    drop_rain(published_like, *((2024, month) for month in range(10, 13)))
    points = {point["year"]: point for point in trends(TestClient(app)).json()["water"]["points"]}
    assert 2017 in points and points[2017]["precip_mm"] is None


def test_sin_la_et0_de_un_mes_la_necesidad_es_nula_y_la_lluvia_no(published_like):
    climate = pl.read_parquet(published_like / "climate_month.parquet")
    hole = (pl.col("municipality_id") == SAMACA) & (pl.col("year") == 2016) & (pl.col("month") == 10)
    climate.with_columns(pl.when(hole).then(None).otherwise(pl.col("et0_mm")).alias("et0_mm")).write_parquet(
        published_like / "climate_month.parquet"
    )
    points = {point["year"]: point for point in trends(TestClient(app)).json()["water"]["points"]}
    assert points[2016]["need_mm"] is None
    assert points[2016]["precip_mm"] is not None
    # La ET0 no recorta años: 2016 sigue en la serie y los demás años tienen su necesidad.
    assert points[2015]["need_mm"] == 587.5


def test_un_nan_en_la_lluvia_o_la_et0_es_un_dato_que_falta(published_like):
    precip = pl.read_parquet(published_like / "precip_month.parquet")
    hole = (pl.col("year") == 2019) & (pl.col("month") == 9)
    precip.with_columns(pl.when(hole).then(math.nan).otherwise(pl.col("precip_mm")).alias("precip_mm")).write_parquet(
        published_like / "precip_month.parquet"
    )
    climate = pl.read_parquet(published_like / "climate_month.parquet")
    hole = (pl.col("year") == 2020) & (pl.col("month") == 9)
    climate.with_columns(pl.when(hole).then(math.nan).otherwise(pl.col("et0_mm")).alias("et0_mm")).write_parquet(
        published_like / "climate_month.parquet"
    )
    response = trends(TestClient(app))
    assert response.status_code == 200
    assert "NaN" not in response.text
    points = {point["year"]: point for point in response.json()["water"]["points"]}
    assert points[2019]["precip_mm"] is None and points[2019]["need_mm"] == 587.5
    assert points[2020]["need_mm"] is None and points[2020]["precip_mm"] is not None


def test_una_siembra_el_29_de_febrero_se_proyecta_desde_el_1_de_marzo_en_anios_no_bisiestos(published_like):
    # Arveja sembrada el 29 de febrero de 2028 (bisiesto): 110 días, del 29 de febrero al 17 de junio.
    response = trends(TestClient(app), crop_id="arveja", sowing_date="2028-02-29")
    assert response.status_code == 200
    points = {point["year"]: point for point in response.json()["water"]["points"]}
    assert list(points) == list(YEARS)
    # 2015 no tiene 29 de febrero: ese día no aporta. Marzo 30, abril 40, mayo 50 y 17 días de junio, 60 × 17/30.
    assert points[2015]["precip_mm"] == pytest.approx(round(30 + 40 + 50 + 60 * 17 / 30, 1))
    # Sin el 29 de febrero falta el primer día del ciclo (Kc 0,5): 4 × (95,425 − 0,5).
    assert points[2015]["need_mm"] == pytest.approx(379.7)
    # 2016 sí lo tiene: suma 1/29 de la lluvia de febrero y la necesidad completa (4 × 95,425).
    assert points[2016]["precip_mm"] == pytest.approx(round(20 / 29 + 30 + 40 + 50 + 60 * 17 / 30, 1))
    assert points[2016]["need_mm"] == pytest.approx(381.7)


def test_una_ventana_dentro_del_anio_usa_todos_los_anios(published_like):
    points = trends(TestClient(app), crop_id="arveja", sowing_date="2027-03-01").json()["water"]["points"]
    assert [point["year"] for point in points] == list(YEARS)


def test_sin_lluvia_de_la_fuente_de_la_region_el_agua_viene_vacia(published_like):
    # Tunja tiene ET0 y lluvia de NASA POWER, pero no de GPM IMERG: no se cambia de fuente (R1).
    body = trends(TestClient(app), municipality_id=TUNJA).json()
    assert body["water"] == {"status": "insufficient_data", "source_id": "imerg", "unit": "mm", "points": []}
    assert body["limitations"][0] == "Sin la lluvia de imerg para esta ventana en la zona: la serie de agua viene vacía"


def test_un_cultivo_sin_etapas_no_tiene_ventana_ni_serie_de_agua(published_like):
    stages = pl.read_parquet(published_like / "crop_stages.parquet")
    stages.filter(pl.col("crop_id") != "papa").write_parquet(published_like / "crop_stages.parquet")
    water = trends(TestClient(app)).json()["water"]
    assert (water["status"], water["points"]) == ("insufficient_data", [])


# ---------- oferta y verdor ----------


def test_sin_tablas_de_oferta_ni_verdor_vienen_vacias(published_like):
    body = trends(TestClient(app)).json()
    assert body["supply"] == {"status": "insufficient_data", "source_id": "eva", "unit": "ha", "semester": "B", "points": []}
    assert body["ndvi"] == {"status": "insufficient_data", "source_id": None, "quality": None, "points": []}
    assert body["limitations"] == [
        "Sin el área sembrada de eva del semestre B en la zona: la serie de oferta viene vacía",
        "El verdor todavía no tiene una fuente asignada para la región: la serie de verdor viene vacía",
    ]


def test_con_las_tablas_lee_la_oferta_del_semestre(complete):
    body = trends(TestClient(app)).json()
    m.TrendsResponse.model_validate(body)
    supply = body["supply"]
    assert (supply["status"], supply["source_id"], supply["semester"]) == ("available", "eva", "B")
    # Solo el semestre B (la siembra es en agosto) y solo EVA, en orden de año: la fila de FAOSTAT no se mezcla.
    assert supply["points"] == [
        {"year": 2019, "planted_ha": 110.0, "preliminary": False},
        {"year": 2020, "planted_ha": 120.0, "preliminary": False},
        {"year": 2021, "planted_ha": 130.0, "preliminary": True},
    ]


def test_el_verdor_viene_vacio_sin_fuente_asignada_aunque_la_tabla_exista(complete):
    # `sources.yaml` no asigna fuente al verdor: no se elige una por otra regla (orden alfabético, la única que hay…),
    # tampoco con dos fuentes en la tabla (R1, R8; Felipe, 14 nov 2026, PR #104).
    table = pl.read_parquet(complete / "ndvi_municipality_normal.parquet")
    other = table.with_columns(pl.lit("landsat_ndvi").alias("source_id"))
    pl.concat([table, other]).write_parquet(complete / "ndvi_municipality_normal.parquet")
    body = trends(TestClient(app)).json()
    assert body["ndvi"] == {"status": "insufficient_data", "source_id": None, "quality": None, "points": []}
    assert body["limitations"] == ["El verdor todavía no tiene una fuente asignada para la región: la serie de verdor viene vacía"]


def test_una_siembra_de_marzo_lee_el_semestre_a(complete):
    supply = trends(TestClient(app), sowing_date="2027-03-01").json()["supply"]
    assert (supply["semester"], supply["points"]) == ("A", [{"year": 2020, "planted_ha": 90.0, "preliminary": False}])


def test_sin_filas_del_municipio_la_oferta_y_el_verdor_vienen_vacios(complete):
    body = trends(TestClient(app), municipality_id=TUNJA).json()
    assert (body["supply"]["status"], body["supply"]["points"]) == ("insufficient_data", [])
    assert (body["ndvi"]["status"], body["ndvi"]["points"], body["ndvi"]["quality"]) == ("insufficient_data", [], None)


# ---------- entradas, versiones, determinismo y R9 ----------


@pytest.mark.parametrize(
    ("municipality_id", "crop_id"),
    [(SAMACA, "yuca"), (SAMACA, "avena_vicia"), (SAMACA, "descanso"), ("1564", "papa"), (SAMACA, "Papa")],
)
def test_una_entrada_fuera_del_catalogo_responde_422(published_like, municipality_id, crop_id):
    response = trends(TestClient(app), municipality_id=municipality_id, crop_id=crop_id)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"


@pytest.mark.parametrize("sowing_date", [None, "2027-13-01", "2027-02-30", "mañana", "02/08/2027"])
def test_una_fecha_de_siembra_ausente_o_invalida_responde_422(published_like, sowing_date):
    params = {"municipality_id": SAMACA, "crop_id": "papa"} | ({"sowing_date": sowing_date} if sowing_date else {})
    response = TestClient(app).get("/api/v1/trends", params=params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"


def test_una_region_sin_fuentes_responde_500_sin_decir_el_motivo(published_like, monkeypatch):
    """Si `catalog/sources.yaml` no tiene la región del dataset es un error de despliegue: 500 con la forma de los
    errores del contrato. El motivo va al log, nunca al cliente."""
    real = signal_sources.get_signal_sources()
    other = signal_sources.SignalSources(real.version, {"otra-region": next(iter(real.regions.values()))}, real.planned)
    monkeypatch.setattr(signal_sources, "get_signal_sources", lambda: other)
    with capture_logs() as logs:
        response = trends(TestClient(app, raise_server_exceptions=False))
    assert response.status_code == 500
    body = response.json()
    assert set(body) == {"error"} and set(body["error"]) == {"code", "message", "request_id"}
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    for leak in ("co-boyaca-cundinamarca", "sources.yaml", "SignalSourcesError", "región"):
        assert leak not in response.text, leak
    failure = next(entry for entry in logs if entry["event"] == "internal_error")
    assert "SignalSourcesError" in failure["detail"]
    assert "co-boyaca-cundinamarca" in str(failure["exc_info"])


def test_sin_dataset_responde_503():
    assert trends(TestClient(app)).status_code == 503


def test_trae_las_versiones_del_dataset_y_de_las_reglas(complete):
    assert trends(TestClient(app)).json()["versions"] == {"dataset": "ejemplo", "rules": "0.1.0+umbrales.1.1.0+pesos.1.1.0"}


def test_mismos_datos_misma_respuesta_byte_a_byte(complete):
    client = TestClient(app)
    assert trends(client).content == trends(client).content


def test_el_openapi_ya_no_anuncia_501():
    assert "501" not in app.openapi()["paths"]["/api/v1/trends"]["get"]["responses"]


def snapshot(db) -> dict[str, list[str]]:
    """El contenido completo de cada tabla de la base, ordenado: no solo cuántas filas hay."""
    db.expire_all()
    return {table.name: sorted(repr(tuple(row)) for row in db.execute(select(table)).all()) for table in Base.metadata.sorted_tables}


def test_no_guarda_nada_ni_escribe_la_consulta_en_el_log(complete, client, db):
    """R9: con sesión y sin ella, la base queda idéntica y el log no lleva el municipio, el cultivo ni la fecha."""
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "username": "rosa.samaca",
            "password": "papaya-criolla-2026",
            "display_name": "Rosa",
            "consent_version": 3,
            "consent_accepted": True,
        },
    )
    assert registered.status_code == 201, registered.json()
    assert client.post("/api/v1/lots", json={"name": "El Alto", "municipality_id": SAMACA, "area_ha": 1.0}).status_code == 201
    before = snapshot(db)
    assert before["users"] and before["lots"]
    with capture_logs() as logs:
        assert trends(client).status_code == 200
        assert trends(TestClient(app)).status_code == 200
    assert snapshot(db) == before
    text = str([{key: value for key, value in entry.items() if key != "request_id"} for entry in logs])
    for value in (SAMACA, "papa", PAPA_AUGUST):
        assert value not in text, value
