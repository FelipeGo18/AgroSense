"""Errores de la API con una sola forma, identificador de petición y la línea de log de cada petición.

Errores: `{"error": {"code", "message", "request_id"}}` (specs/02-contratos.md, «Errores»).
Log: una línea por petición con los campos de «Logs de la terminal» (HU-177).
"""

import time
import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.accounts.security import ServerBusy
from backend.db.state import remember_down
from common.logging import get_logger

log = get_logger("agrosense.api")

REQUEST_ID_HEADER = "X-Request-ID"
# Lo que dice el log en `route` cuando la petición no llegó a ninguna ruta de la API.
NO_ROUTE = "[sin ruta]"
SERVER_BUSY = "AgroSense está atendiendo a mucha gente en este momento. Intente de nuevo en unos segundos."
ACCOUNTS_UNAVAILABLE = "Las cuentas no están disponibles en este momento. Puede seguir consultando sin cuenta."


class ApiError(Exception):
    """Un error que la API sabe explicar. `message` es para la persona: en español y sin detalles internos."""

    def __init__(self, status_code: int, code: str, message: str, log: str | None = None, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        # Cabeceras que van con la respuesta, como `Retry-After` en un 429.
        self.headers = headers or {}
        self.status_code = status_code
        self.code = code
        self.message = message
        # Lo que se escribe en la terminal del servidor: puede decir más que el mensaje para la persona
        # (por ejemplo, si falló el usuario o la contraseña). Nunca sale en la respuesta.
        self.log = log or message


def request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def error_response(request: Request, status_code: int, code: str, message: str, headers: dict[str, str] | None = None) -> JSONResponse:
    request_id = request_id_of(request)
    return JSONResponse(
        {"error": {"code": code, "message": message, "request_id": request_id}},
        status_code=status_code,
        headers={**(headers or {}), REQUEST_ID_HEADER: request_id},
    )


_HTTP_CODES = {401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}


def explain(request: Request, detail: str) -> None:
    """Deja escrito, para la línea de log de esta petición, qué pasó en palabras."""
    request.state.detail = detail


# Qué significa que cada endpoint haya respondido bien. Lo que salió mal lo explica quien lo rechazó.
DONE = {
    "auth.register": "Cuenta creada y sesión abierta",
    "auth.login": "Inicio de sesión correcto",
    "auth.logout": "Sesión cerrada",
    "auth.me": "Perfil consultado",
    "auth.update_me": "Perfil actualizado",
    "auth.change_password": "Contraseña cambiada; las demás sesiones del usuario quedaron cerradas",
    "auth.my_activity": "Actividad de la cuenta consultada",
    "auth.delete_me": "Cuenta borrada con todos sus datos",
    "main.health": "Estado de la API consultado",
}
BY_STATUS = {
    401: "Petición rechazada: hace falta iniciar sesión",
    403: "Petición rechazada: sin permiso",
    404: "No existe esa dirección en la API",
    405: "Ese método no se puede usar en esa dirección",
    422: "Petición rechazada: datos inválidos",
    429: "Petición rechazada: demasiados intentos",
    500: "Fallo interno de la API",
    503: "Servicio no disponible",
}


def _endpoint(request: Request) -> str | None:
    """El nombre del endpoint que atendió la petición, como `auth.login`. Solo sale en la terminal del servidor."""
    function = request.scope.get("endpoint")
    return f"{function.__module__.rsplit('.', 1)[-1]}.{function.__name__}" if function else None


def _detail(request: Request, endpoint: str | None, status: int) -> str:
    explained = getattr(request.state, "detail", None)
    if explained:
        return explained
    if status < 400:
        return DONE.get(endpoint or "", "Petición atendida")
    return BY_STATUS.get(status, f"La petición respondió {status}")


def _level(status: int) -> str:
    """`error` para los fallos internos; `warning` para lo que se rechazó (400 a 499) o no está disponible (503); lo demás, `info`."""
    if status >= 500 and status != 503:
        return "error"
    return "warning" if status >= 400 else "info"


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_log(request: Request, call_next):
        # Se respeta el identificador que trae la petición si es un UUID válido; si no, se crea uno.
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        try:
            request.state.request_id = str(uuid.UUID(incoming))
        except ValueError:
            request.state.request_id = str(uuid.uuid4())
        # Todo lo que se escriba al log durante esta petición lleva su identificador.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request.state.request_id)
        started = time.perf_counter()
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        # La plantilla de la ruta, no la URL: sin parámetros ni identificadores. Nunca el cuerpo (R9). Las rutas propias de
        # FastAPI (la documentación) no dejan plantilla, pero son fijas: va su dirección. Una dirección que no existe no
        # se escribe: puede traer cualquier cosa, hasta secuencias que cambian lo que muestra la terminal.
        route = request.scope.get("route")
        endpoint = _endpoint(request)
        fields = {
            "detail": _detail(request, endpoint, response.status_code),
            "method": request.method,
            "route": getattr(route, "path", None) or (request.url.path if endpoint else NO_ROUTE),
            "status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000),
        }
        # Qué función la atendió, como `auth.login`. Solo existe en la terminal del servidor: la respuesta no lo lleva.
        if endpoint:
            fields["endpoint"] = endpoint
        # Quién fue, si había sesión: el identificador y el rol; nunca el usuario ni el nombre.
        if getattr(request.state, "user_id", None):
            fields |= {"user_id": request.state.user_id, "role": request.state.role}
        getattr(log, _level(response.status_code))("request", **fields)
        return response

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        explain(request, exc.log)
        return error_response(request, exc.status_code, exc.code, exc.message, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError):
        # Se dice qué campo falló, sin devolver el valor que llegó (podría ser una contraseña).
        fields = sorted({".".join(str(part) for part in error["loc"][1:]) for error in exc.errors()} - {""})
        detail = f" Revise: {', '.join(fields)}." if fields else ""
        # Se nombran los campos que fallaron, nunca lo que traían.
        explain(request, f"Petición rechazada: datos inválidos en {', '.join(fields) or 'el cuerpo'}")
        return error_response(request, 422, "invalid_input", f"Hay datos que no son válidos.{detail}")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return error_response(request, exc.status_code, _HTTP_CODES.get(exc.status_code, "error"), str(exc.detail))

    @app.exception_handler(OperationalError)
    async def database_down(request: Request, exc: OperationalError):
        # La base de datos se cayó a mitad de una petición. Lo que no la usa sigue funcionando.
        remember_down()
        explain(request, "Cuentas no disponibles (503) porque la base de datos dejó de responder a mitad de la petición")
        log.warning(
            "accounts_unavailable",
            reason="database_down",
            detail="Cuentas no disponibles (503) porque la base de datos está apagada o no responde",
        )
        return error_response(request, 503, "accounts_database_down", ACCOUNTS_UNAVAILABLE)

    @app.exception_handler(ServerBusy)
    async def busy(request: Request, exc: ServerBusy):
        # Demasiadas contraseñas calculándose a la vez: se responde en vez de dejar crecer la memoria sin tope.
        explain(request, "Servicio ocupado (503): todos los cálculos de contraseña están en uso")
        return error_response(request, 503, "server_busy", SERVER_BUSY, {"Retry-After": "5"})

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        explain(request, f"Fallo interno de la API: {type(exc).__name__}")
        log.error("internal_error", detail=f"Fallo interno de la API: {type(exc).__name__}. La traza va debajo.", exc_info=exc)
        return error_response(request, 500, "internal_error", "Algo falló de nuestro lado. Intente de nuevo en un momento.")
