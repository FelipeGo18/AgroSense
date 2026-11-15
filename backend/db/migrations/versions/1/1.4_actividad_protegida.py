"""actividad protegida

Migración 1.4 · va después de 1.3
Creada el 2026-11-14

HU-178: los eventos de `activity_log` no se modifican ni se borran desde la API. Un disparador en la base de datos
rechaza todo `UPDATE` y `DELETE`, salvo tres casos:

- **Anonimizar:** un `UPDATE` que solo deja en nulo quién hizo el evento, de quién eran los datos, el objeto, el ticket o
  el motivo. Es lo que hace borrar una cuenta (R9) y lo que hacen las llaves `ON DELETE SET NULL` al borrar un usuario
  o un ticket. Ningún otro campo puede cambiar.
- **Borrar la cuenta:** un `DELETE` de los eventos de una persona, solo si en la misma transacción se pidió olvidarla
  (`agrosense.forget_user` con su `user_id`, que pone `activity.forget_user`).
- **La limpieza de 180 días:** un `DELETE` de eventos de más de 180 días, solo si en la misma transacción se pidió la
  limpieza (`agrosense.activity_purge = 'on'`, que pone `activity.purge_old`).

La base de la nube del equipo no tiene un rol aparte para la limpieza; este disparador cumple la regla en la base misma
(decidido por Felipe el 14 de noviembre de 2026). Con un rol aparte, el de la API solo tendría `INSERT` y `SELECT`.
"""

from alembic import op

revision: str = "1.4"
down_revision: str | None = "1.3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION activity_log_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                -- Solo anonimizar: cada campo queda igual o pasa a nulo en las columnas que dicen de quién era.
                IF NEW.event_id IS DISTINCT FROM OLD.event_id
                   OR NEW.occurred_at IS DISTINCT FROM OLD.occurred_at
                   OR NEW.request_id IS DISTINCT FROM OLD.request_id
                   OR NEW.actor_role IS DISTINCT FROM OLD.actor_role
                   OR NEW.action IS DISTINCT FROM OLD.action
                   OR NEW.object_type IS DISTINCT FROM OLD.object_type
                   OR NEW.outcome IS DISTINCT FROM OLD.outcome
                   OR NEW.details IS DISTINCT FROM OLD.details
                   OR (NEW.actor_user_id IS NOT NULL AND NEW.actor_user_id IS DISTINCT FROM OLD.actor_user_id)
                   OR (NEW.subject_user_id IS NOT NULL AND NEW.subject_user_id IS DISTINCT FROM OLD.subject_user_id)
                   OR (NEW.object_id IS NOT NULL AND NEW.object_id IS DISTINCT FROM OLD.object_id)
                   OR (NEW.ticket_id IS NOT NULL AND NEW.ticket_id IS DISTINCT FROM OLD.ticket_id)
                   OR (NEW.reason IS NOT NULL AND NEW.reason IS DISTINCT FROM OLD.reason) THEN
                    RAISE EXCEPTION 'activity_log solo se agrega: un evento no se modifica (HU-178)';
                END IF;
                RETURN NEW;
            END IF;
            -- DELETE
            IF current_setting('agrosense.activity_purge', true) = 'on'
               AND OLD.occurred_at < now() - interval '180 days' THEN
                RETURN OLD;
            END IF;
            IF OLD.actor_user_id IS NOT NULL
               AND current_setting('agrosense.forget_user', true) = OLD.actor_user_id::text THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION 'activity_log solo se agrega: un evento no se borra (HU-178)';
        END;
        $$;
        """
    )
    op.execute(
        "CREATE TRIGGER activity_log_guard BEFORE UPDATE OR DELETE ON activity_log FOR EACH ROW EXECUTE FUNCTION activity_log_guard();"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS activity_log_guard ON activity_log;")
    op.execute("DROP FUNCTION IF EXISTS activity_log_guard();")
