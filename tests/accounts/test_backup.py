"""Regla: ninguna migración se aplica sin una copia de seguridad de la base de datos antes (backend/README.md)."""

import subprocess
import sys
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from backend.db import migrate
from tests.conftest import alembic_config


def plain_config(database_url) -> Config:
    """Como la de las pruebas, pero sin la marca: es `migrate` quien debe ponerla."""
    config = alembic_config(database_url)
    del config.attributes["backup_checked"]
    return config


def test_el_nombre_de_la_copia_dice_que_base_cuando_y_entre_que_migraciones():
    name = migrate.backup_name("agrosense", "1.3", "1.4", datetime(2026, 10, 12, 15, 30, 0, tzinfo=UTC))
    assert name == "agrosense_20261012-153000_de-1.3_a-1.4.dump"


def test_antes_de_migrar_se_copia_la_base_y_la_copia_sirve(engine, database_url, tmp_path):
    with engine.begin() as connection:
        row = {"day": "2026-10-12", "endpoint": "diagnostics", "municipality_id": "15646", "crop_id": "papa", "count": 7}
        connection.execute(
            text(
                "insert into usage_daily (day, endpoint, municipality_id, crop_id, count) "
                "values (:day, :endpoint, :municipality_id, :crop_id, :count)"
            ),
            row,
        )
    try:
        saved = migrate.migrate(plain_config(database_url), database_url, target="1.2", down=True, folder=tmp_path)
        assert saved is not None and saved.parent == tmp_path
        assert saved.name.startswith(f"{database_url.database}_") and saved.name.endswith("_de-1.3_a-1.2.dump")
        # Un volcado de PostgreSQL de verdad, y con lo que había antes de migrar.
        content = saved.read_bytes()
        assert content[:5] == b"PGDMP" and b"usage_daily" in content
        assert "usage_daily" not in inspect(engine).get_table_names()
    finally:
        command.upgrade(alembic_config(database_url), "head")
        with engine.begin() as connection:
            connection.execute(text("truncate usage_daily"))


def test_si_ya_esta_al_dia_no_hay_migracion_ni_copia(engine, database_url, tmp_path):
    assert migrate.migrate(plain_config(database_url), database_url, folder=tmp_path) is None
    assert list(tmp_path.iterdir()) == []


def test_si_la_copia_falla_no_se_migra(engine, database_url, tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise migrate.BackupError("No se pudo hacer la copia de seguridad: disco lleno")

    monkeypatch.setattr(migrate, "backup", broken)
    with pytest.raises(migrate.BackupError):
        migrate.migrate(plain_config(database_url), database_url, target="-1", down=True, folder=tmp_path)
    assert migrate.current_revision(database_url) == "1.3"
    assert "usage_daily" in inspect(engine).get_table_names()


def test_una_copia_que_no_es_un_volcado_se_rechaza_y_no_queda_a_medias(database_url, tmp_path, monkeypatch):
    monkeypatch.setattr(migrate, "_dump_command", lambda url, output: ([sys.executable, "-c", "print('esto no es un volcado')"], {}))
    with pytest.raises(migrate.BackupError):
        migrate.backup(database_url, "1.3", "1.4", tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_se_conservan_solo_las_copias_mas_recientes(tmp_path):
    import os

    for i in range(5):
        file = tmp_path / f"agrosense_{i}.dump"
        file.write_bytes(b"PGDMP")
        os.utime(file, (1_700_000_000 + i, 1_700_000_000 + i))
    removed = migrate.prune(tmp_path, keep=2)
    assert sorted(file.name for file in removed) == ["agrosense_0.dump", "agrosense_1.dump", "agrosense_2.dump"]
    assert sorted(file.name for file in tmp_path.iterdir()) == ["agrosense_3.dump", "agrosense_4.dump"]


def test_alembic_upgrade_directo_se_niega_y_dice_que_comando_usar():
    """Quien escriba `alembic upgrade head` a mano se salta la copia: no se le deja."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert result.returncode != 0
    assert "python -m backend.db.migrate" in result.stderr
