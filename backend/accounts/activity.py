"""Trazabilidad de las cuentas: quién hizo qué, cuándo y sobre qué (HU-178; specs/02-contratos.md, «Trazabilidad»).

Reglas que este módulo hace cumplir:
- Solo se agrega. Nunca se guardan contraseñas, tokens, el polígono, valores de campos ni la IP.
- `details` lleva solo los nombres de los campos que cambiaron.
- Se conserva 180 días.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session as Db

from backend.accounts.models import User
from backend.accounts.trace_models import ActivityEvent

RETENTION = timedelta(days=180)


def record(
    db: Db,
    action: str,
    *,
    request_id: str,
    actor: User | None,
    outcome: str = "ok",
    object_type: str | None = None,
    object_id: uuid.UUID | None = None,
    fields: list[str] | None = None,
) -> None:
    """Agrega un evento a la sesión de base de datos. Se confirma junto con el cambio que describe:
    no hay cambio sin traza ni traza de un cambio que no ocurrió."""
    db.add(
        ActivityEvent(
            request_id=uuid.UUID(request_id) if request_id else None,
            actor_user_id=actor.user_id if actor else None,
            actor_role=actor.role if actor else None,
            # El agricultor actúa sobre lo suyo: los datos afectados son de quien lo hizo.
            subject_user_id=actor.user_id if actor else None,
            action=action,
            object_type=object_type,
            object_id=object_id,
            outcome=outcome,
            details={"fields": sorted(fields)} if fields is not None else None,
        )
    )


def record_rejected(db: Db, action: str, *, request_id: str, actor: User | None, outcome: str) -> None:
    """Un intento rechazado (`denied`) o fallido (`failed`) se escribe aparte: lo que se estaba haciendo se deshace
    y solo queda el evento."""
    db.rollback()
    record(
        db,
        action,
        request_id=request_id,
        actor=actor,
        outcome=outcome,
        object_type="user" if actor else None,
        object_id=actor.user_id if actor else None,
    )
    db.commit()


def record_lockout(db: Db, action: str, *, request_id: str, actor: User | None, window: timedelta) -> None:
    """Un rechazo por demasiados intentos deja **un** evento `denied` por ventana de bloqueo, no uno por petición: si no,
    cualquiera llenaría el registro repitiendo la petición. Con un usuario que no existe no queda ninguno: no hay de
    quién contarlo, y los intentos fallidos que llevaron al bloqueo ya quedaron."""
    if actor is None:
        return
    since = datetime.now(UTC) - window
    already = db.scalar(
        select(ActivityEvent.event_id)
        .where(
            ActivityEvent.actor_user_id == actor.user_id,
            ActivityEvent.action == action,
            ActivityEvent.outcome == "denied",
            ActivityEvent.occurred_at > since,
        )
        .limit(1)
    )
    if already is None:
        record_rejected(db, action, request_id=request_id, actor=actor, outcome="denied")


def page(db: Db, user: User, before: datetime | None, limit: int) -> tuple[list[ActivityEvent], datetime | None]:
    """Los eventos de un usuario y lo que soporte hizo sobre sus datos, del más reciente al más antiguo.

    La página siguiente pide lo anterior a `next_before`. Varios eventos pueden tener la misma hora (los de una misma
    petición, como los tres del registro): si el corte cae entre ellos, la página se alarga hasta incluirlos a todos,
    porque si no, los que quedaron fuera nunca saldrían. Por eso una página puede traer algunos más que `limit`.
    """
    query = select(ActivityEvent).where(or_(ActivityEvent.subject_user_id == user.user_id, ActivityEvent.actor_user_id == user.user_id))
    if before is not None:
        query = query.where(ActivityEvent.occurred_at < before)
    events = list(db.scalars(query.order_by(ActivityEvent.occurred_at.desc(), ActivityEvent.event_id).limit(limit + 1)))
    if len(events) <= limit:
        return events, None
    events = events[:limit]
    last = events[-1]
    # Los que comparten la hora del último y no cupieron.
    events += db.scalars(
        query.where(ActivityEvent.occurred_at == last.occurred_at, ActivityEvent.event_id > last.event_id).order_by(ActivityEvent.event_id)
    )
    older = db.scalar(query.where(ActivityEvent.occurred_at < last.occurred_at).limit(1))
    return events, last.occurred_at if older is not None else None


def forget_user(db: Db, user: User) -> None:
    """Antes de borrar una cuenta: se borran sus eventos, y en lo que un administrador hizo sobre sus datos se quita
    de quién eran, para no perder quién hizo qué sin guardar a quién (R9)."""
    db.execute(delete(ActivityEvent).where(ActivityEvent.actor_user_id == user.user_id))
    db.execute(
        update(ActivityEvent).where(ActivityEvent.subject_user_id == user.user_id).values(subject_user_id=None, object_id=None, reason=None)
    )


def purge_old(db: Db) -> int:
    """Borra lo que pasó de los 180 días y dice cuántos eventos borró."""
    result = db.execute(delete(ActivityEvent).where(ActivityEvent.occurred_at < datetime.now(UTC) - RETENTION))
    return result.rowcount or 0
