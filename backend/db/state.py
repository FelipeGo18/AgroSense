"""Si las cuentas se pueden usar ahora mismo, y por qué no cuando no se puede.

Las cuentas (y todo lo que necesite la base de datos) solo se atienden si la base responde **y** su esquema está en la
última migración que trae el código. Si no, se apagan con un 503 que dice el motivo, en vez de fallar de formas raras
contra tablas que no son las que el código espera. Lo que no usa la base de datos sigue funcionando.
"""

import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

Reason = Literal["ok", "database_down", "migration_pending"]


@dataclass(frozen=True)
class AccountsState:
    reason: Reason
    # En qué migración está la base de datos (nulo si no responde o no tiene ninguna) y cuál espera el código.
    current: str | None
    expected: str

    @property
    def available(self) -> bool:
        return self.reason == "ok"

    @property
    def explanation(self) -> str:
        """El motivo, para el log y para quien opera. No se le muestra al agricultor."""
        if self.reason == "database_down":
            return "la base de datos está apagada o no responde"
        if self.reason == "migration_pending":
            return f"la migración {self.expected} no se completó; la base de datos está en la {self.current or 'ninguna (vacía)'}"
        return "disponibles"


# Cuando la base de datos no responde, se recuerda durante estos segundos. Mientras tanto se responde «no disponible»
# de inmediato, sin volver a intentar conectarse: cada intento cuesta unos 3 segundos de espera.
DOWN_MEMORY_SECONDS = 10.0
_down_until = 0.0


def remember_down() -> None:
    """Anota que la base de datos acaba de fallar."""
    global _down_until
    _down_until = time.monotonic() + DOWN_MEMORY_SECONDS


def forget_down() -> None:
    global _down_until
    _down_until = 0.0


def recently_down() -> bool:
    return time.monotonic() < _down_until


@lru_cache
def expected_revision() -> str:
    """La última migración que trae el código."""
    head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    return head or ""


def accounts_state(db: Session) -> AccountsState:
    expected = expected_revision()
    if recently_down():
        # Falló hace un momento: no se vuelve a esperar a la base de datos en cada petición.
        return AccountsState("database_down", None, expected)
    try:
        current = db.scalar(text("select version_num from alembic_version"))
    except OperationalError:
        db.rollback()
        remember_down()
        return AccountsState("database_down", None, expected)
    except SQLAlchemyError:
        # La base responde pero no tiene la tabla de versiones: nunca se migró.
        db.rollback()
        return AccountsState("migration_pending", None, expected)
    return AccountsState("ok" if current == expected else "migration_pending", current, expected)
