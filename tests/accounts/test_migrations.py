"""Las migraciones son la única forma de cambiar la base de datos (HU-161). Estas pruebas cuidan el flujo del equipo."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from backend.db.models import Base
from backend.db.revision import after, existing, next_revision
from tests.conftest import alembic_config

TABLES = {"users", "sessions", "login_attempts", "lots", "seasons", "support_tickets", "activity_log", "usage_daily"}


def test_los_modelos_y_las_migraciones_dicen_lo_mismo(engine):
    """Si alguien cambia `models.py` y no deja su migración, esta prueba falla y dice qué falta."""
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True, "compare_server_default": True})
        pending = compare_metadata(context, Base.metadata)
    assert pending == [], "Hay cambios en los modelos sin migración. Corra: uv run alembic revision --autogenerate -m '...'"


def test_hay_una_sola_ultima_migracion(database_url):
    """Dos personas que crean una migración a la vez dejan dos «cabezas». Se arregla antes de fusionar (backend/README.md)."""
    heads = ScriptDirectory.from_config(alembic_config(database_url)).get_heads()
    assert len(heads) == 1, f"Hay {len(heads)} migraciones finales: {heads}. Una de las dos debe ir después de la otra."


def test_las_migraciones_bajan_y_vuelven_a_subir(engine, database_url):
    """Cada migración se puede deshacer: sirve para volver atrás si una sale mal."""
    config = alembic_config(database_url)
    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) == TABLES | {"alembic_version"}


def test_borrar_un_usuario_borra_en_cascada_lo_suyo(engine):
    """El borrado en cascada lo hace la base de datos, no el código (R9)."""
    inspector = inspect(engine)
    for table, parent in (("sessions", "users"), ("lots", "users"), ("seasons", "lots"), ("support_tickets", "users")):
        foreign_key = next(fk for fk in inspector.get_foreign_keys(table) if fk["referred_table"] == parent)
        assert foreign_key["options"].get("ondelete") == "CASCADE", table


def test_la_cuenta_no_guarda_datos_de_contacto(engine):
    """Sin correo, celular, documento ni dirección (R9)."""
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    assert columns == {
        "user_id",
        "username",
        "password_hash",
        "display_name",
        "role",
        "blocked_at",
        "consent_version",
        "consent_at",
        "priorities",
        "created_at",
        "updated_at",
    }


def test_el_contador_de_uso_no_puede_decir_quien_consulto(engine):
    """`usage_daily` no tiene usuario, sesión, IP, hora ni datos de la finca, y no se une con nada (R9)."""
    inspector = inspect(engine)
    assert {column["name"] for column in inspector.get_columns("usage_daily")} == {"day", "endpoint", "municipality_id", "crop_id", "count"}
    assert inspector.get_foreign_keys("usage_daily") == []


def test_la_bitacora_no_tiene_donde_guardar_ip_ni_valores(engine):
    columns = {column["name"] for column in inspect(engine).get_columns("activity_log")}
    assert columns == {
        "event_id",
        "occurred_at",
        "request_id",
        "actor_user_id",
        "actor_role",
        "subject_user_id",
        "action",
        "object_type",
        "object_id",
        "outcome",
        "ticket_id",
        "reason",
        "details",
    }


# ---------- Numeración: 1.1, 1.2 … 1.9 y después 2.1; el primer número es la carpeta ----------


def test_cada_migracion_esta_en_su_carpeta_y_va_detras_de_la_anterior(database_url):
    """`1/1.1_…`, `1/1.2_…`, `2/2.1_…`: el archivo, su identificador y su orden dicen lo mismo."""
    numbers = existing()
    assert numbers, "No hay migraciones"
    assert numbers[0] == (1, 1)
    scripts = ScriptDirectory.from_config(alembic_config(database_url))
    previous = None
    for folder, position in numbers:
        revision = f"{folder}.{position}"
        script = scripts.get_revision(revision)
        assert script is not None, f"El archivo de {revision} no declara ese identificador"
        assert script.down_revision == previous, f"{revision} debe ir después de {previous}"
        previous = revision
    assert len(numbers) == len(list(scripts.walk_revisions())), "Hay una migración fuera de su carpeta o con otro nombre"


def test_los_numeros_no_se_saltan():
    numbers = existing()
    for number, following in zip(numbers, numbers[1:], strict=False):
        assert following == after(number), f"Después de {number} debe venir {after(number)}, no {following}"


def test_como_se_numera_la_siguiente():
    assert next_revision([]) == ("1", "1.1")
    assert next_revision([(1, 1), (1, 2)]) == ("1", "1.3")
    assert next_revision([(1, 8)]) == ("1", "1.9")
    assert next_revision([(1, 9)]) == ("2", "2.1")
    assert next_revision([(2, 9)]) == ("3", "3.1")
