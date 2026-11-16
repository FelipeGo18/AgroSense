"""HU-235: en producción, el job que migra no tiene disco que dure, así que la copia de antes de migrar sube a Cloud
Storage (`AGROSENSE_BACKUP_BUCKET`). Si no sube completa, no se migra."""

import io
import json
import urllib.error

import pytest
from alembic import command

from backend.config.settings import get_settings
from backend.db import migrate
from backend.db.state import expected_revision
from tests.accounts.test_backup import plain_config
from tests.conftest import alembic_config

TOKEN = "ya29.token-de-prueba"


class FakeGoogle:
    """El servidor de metadatos y Cloud Storage: guarda lo que se le pidió y responde como ellos."""

    def __init__(self, size: int | None = None, fail: int | None = None):
        self.requests = []
        self.size = size
        self.fail = fail

    def __call__(self, request, timeout):
        self.requests.append(request)
        if request.full_url == migrate.METADATA_TOKEN_URL:
            return io.BytesIO(json.dumps({"access_token": TOKEN, "expires_in": 3599}).encode())
        if self.fail:
            raise urllib.error.HTTPError(request.full_url, self.fail, "no", {}, io.BytesIO(b"{}"))
        size = self.size if self.size is not None else len(request.data)
        return io.BytesIO(json.dumps({"name": "x", "size": str(size)}).encode())


@pytest.fixture
def dump(tmp_path):
    file = tmp_path / "agrosense_20261115-120000_de-1.5_a-1.6.dump"
    file.write_bytes(b"PGDMP" + b"x" * 100)
    return file


def test_sube_la_copia_con_la_cuenta_del_job(dump):
    google = FakeGoogle()
    stored = migrate.upload(dump, "agrosense-prod-2026-copias", opener=google)
    assert stored == f"gs://agrosense-prod-2026-copias/antes-de-migrar/{dump.name}"
    token_request, upload_request = google.requests
    assert token_request.get_header("Metadata-flavor") == "Google"
    assert upload_request.get_method() == "POST"
    assert upload_request.full_url == (
        "https://storage.googleapis.com/upload/storage/v1/b/agrosense-prod-2026-copias/o"
        f"?uploadType=media&name=antes-de-migrar%2F{dump.name}"
    )
    assert upload_request.get_header("Authorization") == f"Bearer {TOKEN}"
    assert upload_request.data == dump.read_bytes()


def test_si_cloud_storage_la_rechaza_no_hay_copia_y_el_error_no_trae_la_credencial(dump):
    with pytest.raises(migrate.BackupError, match="respondió 403") as error:
        migrate.upload(dump, "agrosense-prod-2026-copias", opener=FakeGoogle(fail=403))
    assert TOKEN not in str(error.value)


def test_si_no_quedo_completa_no_hay_copia(dump):
    with pytest.raises(migrate.BackupError, match="no quedó completa"):
        migrate.upload(dump, "agrosense-prod-2026-copias", opener=FakeGoogle(size=3))


def test_sin_el_servidor_de_metadatos_no_hay_copia(dump):
    def offline(request, timeout):
        raise urllib.error.URLError("sin red")

    with pytest.raises(migrate.BackupError, match="URLError"):
        migrate.upload(dump, "agrosense-prod-2026-copias", opener=offline)


@pytest.fixture
def bucket(monkeypatch):
    monkeypatch.setenv("AGROSENSE_BACKUP_BUCKET", "agrosense-prod-2026-copias")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_si_la_copia_no_sube_no_se_migra(engine, database_url, tmp_path, monkeypatch, bucket):
    def fails(file, name):
        raise migrate.BackupError("No se pudo subir la copia a gs://agrosense-prod-2026-copias: URLError")

    monkeypatch.setattr(migrate, "upload", fails)
    try:
        with pytest.raises(migrate.BackupError, match="No se pudo subir"):
            migrate.migrate(plain_config(database_url), database_url, target="1.2", down=True, folder=tmp_path)
        assert migrate.current_revision(database_url) == expected_revision()
    finally:
        command.upgrade(alembic_config(database_url), "head")


def test_con_bucket_se_sube_la_copia_y_despues_se_migra(engine, database_url, tmp_path, monkeypatch, bucket):
    uploaded = []

    def records(file, name):
        # Cuando sube, la base todavía no se migró.
        uploaded.append((file, name, migrate.current_revision(database_url)))
        return f"gs://{name}/antes-de-migrar/{file.name}"

    monkeypatch.setattr(migrate, "upload", records)
    try:
        saved = migrate.migrate(plain_config(database_url), database_url, target="1.2", down=True, folder=tmp_path)
        assert uploaded == [(saved, "agrosense-prod-2026-copias", expected_revision())]
        assert migrate.current_revision(database_url) == "1.2"
    finally:
        command.upgrade(alembic_config(database_url), "head")


def test_sin_bucket_no_se_sube_nada(engine, database_url, tmp_path, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setattr(migrate, "upload", lambda file, name: pytest.fail("no debía subir"))
    try:
        assert migrate.migrate(plain_config(database_url), database_url, target="1.2", down=True, folder=tmp_path) is not None
    finally:
        command.upgrade(alembic_config(database_url), "head")
