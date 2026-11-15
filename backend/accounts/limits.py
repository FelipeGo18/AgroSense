"""Límite por conexión (IP) para entrar, crear cuenta y todo lo que verifica una contraseña (specs/02-contratos.md,
«Cómo viaja la credencial»; revisión de seguridad del 15 de octubre de 2026).

Vive en la memoria del proceso, nunca en la base de datos ni en el log: la IP no se guarda (R9). Ni siquiera en
memoria queda la IP tal cual: se guarda su hash con una sal aleatoria que cambia cada vez que arranca la API, así
que no se puede volver a la IP ni unir con nada. Un reinicio borra estos límites; el tope general por usuario, que
sí vive en la base (`login_attempts`), sobrevive.

Detrás de un proxy, Uvicorn debe recibir la IP real: `FORWARDED_ALLOW_IPS` con la dirección del proxy.
"""

import hashlib
import math
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

_SALT = secrets.token_bytes(16)
# Si se acumulan más llaves que esto, se barren las que ya no tienen nada dentro de su ventana.
_MAX_KEYS = 50_000


@dataclass(frozen=True)
class Rule:
    name: str
    limit: int
    window_s: float


# Cualquier petición de entrar o de crear cuenta desde una misma conexión, salga bien o mal.
LOGIN_PER_IP = Rule("login_ip", 30, 15 * 60)
REGISTER_PER_IP = Rule("register_ip", 10, 60 * 60)
# Contraseñas que no coincidieron para un mismo usuario desde una misma conexión: el bloqueo es de esa conexión, no
# de la cuenta. Así nadie deja sin entrar a otra persona equivocándose a propósito desde su casa.
FAILED_PER_IP_AND_USER = Rule("failed_ip_user", 5, 15 * 60)


@dataclass(frozen=True)
class Hit:
    key: str
    at: float


class Limiter:
    """Ventana deslizante por llave. Seguro con varios hilos: FastAPI atiende las rutas síncronas en paralelo."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(rule: Rule, parts: tuple[str, ...]) -> str:
        digest = hashlib.sha256(_SALT + "\0".join(parts).encode()).hexdigest()
        return f"{rule.name}:{digest}"

    def take(self, rule: Rule, *parts: str) -> Hit | float:
        """Anota una petición y devuelve su marca; si ya no cabe, no la anota y devuelve los segundos que faltan."""
        key = self._key(rule, parts)
        now = self.clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - rule.window_s:
                hits.popleft()
            if len(hits) >= rule.limit:
                return max(hits[0] + rule.window_s - now, 1.0)
            hits.append(now)
            if len(self._hits) > _MAX_KEYS:
                self._sweep(now)
            return Hit(key, now)

    def release(self, hit: Hit) -> None:
        """Esa petición no cuenta (la contraseña era la buena)."""
        with self._lock:
            hits = self._hits.get(hit.key)
            if hits is not None and hit.at in hits:
                hits.remove(hit.at)

    def clear(self, rule: Rule, *parts: str) -> None:
        with self._lock:
            self._hits.pop(self._key(rule, parts), None)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def _sweep(self, now: float) -> None:
        longest = max(LOGIN_PER_IP.window_s, REGISTER_PER_IP.window_s, FAILED_PER_IP_AND_USER.window_s)
        for key in [key for key, hits in self._hits.items() if not hits or hits[-1] <= now - longest]:
            del self._hits[key]


LIMITER = Limiter()


def retry_after(seconds: float) -> str:
    """Para la cabecera `Retry-After`: segundos enteros, hacia arriba."""
    return str(math.ceil(seconds))
