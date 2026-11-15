"""Logs de la terminal (HU-177; specs/02-contratos.md, «Logs de la terminal»).

`structlog` a la salida estándar: líneas legibles con color en desarrollo y una línea JSON por evento en producción.
Se configura una vez; lo usan la API, las migraciones, los avisos de Uvicorn, el pipeline y las actualizaciones de
precios. No hay archivos de log. Vive fuera de `backend/` y de `pipeline/` para que ninguno importe al otro.

    log = get_logger()
    log.warning("accounts_unavailable", reason="database_down")
"""

import logging
import re
import sys
from typing import Any

import structlog

# Llaves que nunca llegan al log, vengan de donde vengan (R9).
SECRET_KEYS = frozenset({"password", "current_password", "new_password", "password_hash", "token", "cookie", "authorization", "geometry"})
REDACTED = "[borrado]"


def redact(_logger: Any, _method: str, event: dict[str, Any]) -> dict[str, Any]:
    """Borra del evento las llaves prohibidas, también dentro de diccionarios anidados."""

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: REDACTED if str(key).lower() in SECRET_KEYS else clean(item) for key, item in value.items()}
        if isinstance(value, list | tuple):
            return [clean(item) for item in value]
        return value

    return clean(event)


# Caracteres de control (C0, DEL y C1): un texto que llega de afuera con ellos podría partir una línea en dos o, con
# secuencias de escape, cambiar lo que muestra la terminal.
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def escape_control(_logger: Any, _method: str, event: dict[str, Any]) -> dict[str, Any]:
    """Escribe los caracteres de control de cualquier texto del evento como `\\x1b`, para que se vean y no actúen.
    La traza de un error se agrega después y conserva sus saltos de línea."""

    def clean(value: Any) -> Any:
        if isinstance(value, str):
            return _CONTROL.sub(lambda match: f"\\x{ord(match.group()):02x}", value)
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        if isinstance(value, list | tuple):
            return [clean(item) for item in value]
        return value

    return clean(event)


def headline(_logger: Any, _method: str, event: dict[str, Any]) -> dict[str, Any]:
    """Solo en la consola: la explicación (`detail`) pasa a ser lo primero que se lee, y el nombre técnico del evento
    queda al lado como `evento=`. En JSON no se toca: ahí `event` y `detail` van cada uno en su llave."""
    detail = event.pop("detail", None)
    if detail:
        event["evento"] = event.get("event")
        event["event"] = detail
    return event


RESET, BOLD, DIM = "[0m", "[1m", "[2m"
GREEN, YELLOW, RED, BLUE, MAGENTA, CYAN, WHITE = (f"[{code}m" for code in (32, 33, 31, 34, 35, 36, 97))


def _status_column(_key: str, value: object) -> str:
    """El código de la respuesta, con el color de lo que significa: verde si salió bien, amarillo si se rechazó, rojo si falló."""
    code = int(value) if str(value).isdigit() else 0
    color = GREEN if code < 400 else YELLOW if code < 500 and code != 0 else RED
    return f"{BOLD}{color}{value}{RESET}"


def console_renderer() -> structlog.dev.ConsoleRenderer:
    """La consola en colores, para ver de un vistazo qué pasó. Cada parte de la línea tiene el suyo:

    - **Nivel**: `debug` gris (detalle para depurar), `info` verde (salió bien), `warning` amarillo (se rechazó algo o
      no está disponible: 400 a 499 y 503), `error` rojo (falló la API: 500), `critical` rojo intenso.
    - **Mensaje**: blanco intenso. Es la explicación de lo que pasó.
    - **Código de la respuesta**: verde, amarillo o rojo según el caso.
    - **Endpoint**: azul claro. Qué función atendió la petición.
    - **Lo demás** (método, ruta, duración, identificador): atenuado, para que no distraiga.

    Los colores se escriben siempre, también dentro de Docker (`docker compose logs` los muestra). Con
    `AGROSENSE_LOG_FORMAT=json` no hay colores: es una línea JSON por evento, para que la lea una máquina.
    """
    from structlog.dev import Column, KeyValueColumnFormatter, LogLevelColumnFormatter

    levels = {"debug": DIM, "info": GREEN, "warning": YELLOW, "error": RED, "critical": BOLD + RED, "notset": RESET}
    plain = str

    def value_only(style: str) -> KeyValueColumnFormatter:
        return KeyValueColumnFormatter(key_style=None, value_style=style, reset_style=RESET, value_repr=plain)

    def pair(value_style: str) -> KeyValueColumnFormatter:
        return KeyValueColumnFormatter(key_style=DIM, value_style=value_style, reset_style=RESET, value_repr=plain)

    return structlog.dev.ConsoleRenderer(
        columns=[
            Column("level", LogLevelColumnFormatter(levels, reset_style=RESET)),
            Column("event", value_only(BOLD + WHITE)),
            Column("status", _status_column),
            Column("endpoint", value_only(BOLD + CYAN)),
            Column("method", value_only(MAGENTA)),
            Column("route", value_only(BLUE)),
            # Todo lo demás, con su nombre delante y atenuado.
            Column("", pair(DIM)),
        ]
    )


def configure(level: str = "INFO", fmt: str = "console") -> None:
    """`level`: DEBUG (solo desarrollo), INFO, WARNING o ERROR. `fmt`: `console` o `json`."""
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
        redact,
        escape_control,
    ]
    renderer = structlog.processors.JSONRenderer(ensure_ascii=False) if fmt == "json" else console_renderer()
    structlog.configure(
        processors=[*shared, structlog.processors.format_exc_info, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping().get(level.upper(), logging.INFO)),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
    # Lo que escriben Uvicorn, Alembic y SQLAlchemy con la librería estándar sale con el mismo formato.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, *([] if fmt == "json" else [headline]), renderer],
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error", "alembic"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    # De Uvicorn solo interesan los avisos y los errores: el arranque y el apagado los anuncia la propia API, en español.
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    # Lo mismo con Alembic: qué se migró lo cuenta `backend.db.migrate`.
    logging.getLogger("alembic").setLevel(logging.WARNING)
    # El log de acceso de Uvicorn se apaga: cada petición deja su propia línea, con los campos del contrato.
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False


def get_logger(name: str = "agrosense") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
