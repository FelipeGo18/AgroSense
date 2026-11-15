"""Mantenimiento de las cuentas: borra las sesiones vencidas, la actividad de más de 180 días (HU-162, HU-178) y, para
siempre, los lotes y las temporadas borrados hace 30 días o más, que ya no se pueden restaurar (HU-204, R9).

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
from backend.accounts.farm_models import RESTORE_WINDOW, Lot, Season
from backend.accounts.models import Session
from backend.config.settings import get_settings
from common import logging


@dataclass(frozen=True)
class Cleaned:
    sessions: int
    events: int
    # Lotes y temporadas que llevaban 30 días o más borrados (HU-204). Las temporadas se borran antes que los lotes, así
    # que `seasons` cuenta todas, también las que se borraron con su lote (tienen su misma hora de borrado).
    lots: int = 0
    seasons: int = 0


def run(db: Db) -> Cleaned:
    """Borra lo vencido y dice cuánto borró. Quien llama confirma la transacción."""
    now = datetime.now(UTC)
    sessions = db.execute(delete(Session).where(Session.expires_at <= now)).rowcount or 0
    events = activity.purge_old(db)
    expired = now - RESTORE_WINDOW
    seasons = db.execute(delete(Season).where(Season.deleted_at <= expired)).rowcount or 0
    lots = db.execute(delete(Lot).where(Lot.deleted_at <= expired)).rowcount or 0
    return Cleaned(sessions=sessions, events=events, lots=lots, seasons=seasons)


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
        lots=cleaned.lots,
        seasons=cleaned.seasons,
        detail=(
            f"Mantenimiento: {cleaned.sessions} sesiones vencidas y {cleaned.events} eventos de más de 180 días borrados; "
            f"{cleaned.lots} lotes y {cleaned.seasons} temporadas borrados hace 30 días o más, borrados para siempre"
        ),
    )


if __name__ == "__main__":
    main()
