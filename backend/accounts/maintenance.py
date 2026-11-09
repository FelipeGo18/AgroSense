"""Mantenimiento de las cuentas: borra las sesiones vencidas y la actividad de más de 180 días (HU-162, HU-178).

Nunca corre dentro de una petición: cada endpoint hace solo lo suyo. Corre al arrancar la API (`backend/db/migrate.py`)
y se puede programar una vez al día:

    python -m backend.accounts.maintenance

Una sesión vencida ya no sirve aunque siga en la tabla (la API la rechaza con 401); aquí solo se borra.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session as Db

from backend.accounts import activity
from backend.accounts.models import Session
from backend.config import logging
from backend.config.settings import get_settings


@dataclass(frozen=True)
class Cleaned:
    sessions: int
    events: int


def run(db: Db) -> Cleaned:
    """Borra lo vencido y dice cuánto borró. Quien llama confirma la transacción."""
    sessions = db.execute(delete(Session).where(Session.expires_at <= datetime.now(UTC))).rowcount or 0
    events = activity.purge_old(db)
    return Cleaned(sessions=sessions, events=events)


def main() -> None:
    settings = get_settings()
    logging.configure(settings.log_level, settings.log_format)
    log = logging.get_logger("agrosense.maintenance")
    engine = create_engine(settings.database_url, hide_parameters=True, connect_args={"connect_timeout": 3})
    try:
        with Db(engine) as db:
            cleaned = run(db)
            db.commit()
    finally:
        engine.dispose()
    log.info(
        "maintenance_done",
        sessions=cleaned.sessions,
        events=cleaned.events,
        detail=f"Mantenimiento: {cleaned.sessions} sesiones vencidas y {cleaned.events} eventos de más de 180 días borrados",
    )


if __name__ == "__main__":
    main()
