"""«Hoy» es el día en la región, no el del servidor ni el de quien consulta (contrato, «Fechas»; HU-076, HU-091)."""

from datetime import UTC, date, datetime

import pytest

from common import region
from common.region import RegionError, load_timezone, region_today

# 30 de noviembre de 2026 a las 8:00 p. m. en Bogotá: en UTC ya es 1 de diciembre.
NOCHE_DEL_30 = datetime(2026, 12, 1, 1, 0, tzinfo=UTC)
# 1 de diciembre a las 12:30 a. m. en Bogotá.
MADRUGADA_DEL_1 = datetime(2026, 12, 1, 5, 30, tzinfo=UTC)


def test_hoy_es_el_dia_en_la_region_y_no_en_utc():
    assert region_today(NOCHE_DEL_30) == date(2026, 11, 30)
    assert region_today(MADRUGADA_DEL_1) == date(2026, 12, 1)
    # Un instante dado en otra zona horaria (alguien que consulta desde Tokio) da el mismo día de la región.
    tokio = NOCHE_DEL_30.astimezone(region.ZoneInfo("Asia/Tokyo"))
    assert tokio.date() == date(2026, 12, 1) and region_today(tokio) == date(2026, 11, 30)


def test_la_zona_horaria_sale_de_region_yaml():
    assert str(load_timezone()) == "America/Bogota"


@pytest.mark.parametrize(
    ("timezone", "message"),
    [(None, "region.timezone"), ("America/Duitama", "no es una zona horaria conocida")],
)
def test_sin_zona_horaria_valida_no_se_sabe_que_dia_es(tmp_path, timezone, message):
    line = f"  timezone: {timezone}\n" if timezone else ""
    path = tmp_path / "region.yaml"
    path.write_text(f"region:\n  id: x\n{line}", encoding="utf-8")
    with pytest.raises(RegionError, match=message):
        load_timezone(path)


@pytest.fixture
def reloj(monkeypatch):
    """Fija el instante que ve la API."""

    def fijar(instante: datetime) -> None:
        class Reloj(datetime):
            @classmethod
            def now(cls, tz=None):
                return instante.astimezone(tz) if tz else instante

        monkeypatch.setattr(region, "datetime", Reloj)

    return fijar


def diagnostico(client, sowing_date: str):
    body = {"municipality_id": "15646", "crop_id": "papa", "sowing_date": sowing_date}
    return client.post("/api/v1/diagnostics", json=body)


def test_de_noche_el_mes_en_curso_sigue_valiendo(dataset, client, reloj):
    """El caso de HU-076: a las 8:00 p. m. del 30 de noviembre en Bogotá, noviembre todavía es el mes en curso."""
    reloj(NOCHE_DEL_30)
    response = diagnostico(client, "2026-11-01")
    # Pasa la validación de la fecha; el cálculo todavía no existe (501).
    assert response.status_code == 501, response.json()


def test_pasada_la_medianoche_en_la_region_el_mes_anterior_ya_no_vale(dataset, client, reloj):
    reloj(MADRUGADA_DEL_1)
    response = diagnostico(client, "2026-11-01")
    assert response.status_code == 422 and response.json()["error"]["code"] == "invalid_input"


def test_la_etapa_de_hoy_de_una_siembra_cuenta_los_dias_en_la_region(reloj, monkeypatch):
    from backend.api import season_stage

    reloj(NOCHE_DEL_30)
    assert season_stage.today() == date(2026, 11, 30)
