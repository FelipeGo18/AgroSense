"""La API de AgroSense (M6): una capa delgada sobre las cuentas y, cuando exista, el motor.

uv run uvicorn backend.api.main:app --reload
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from sqlalchemy.orm import Session

from backend.api import auth, errors
from backend.config import logging
from backend.config.settings import get_settings
from backend.db.session import get_db
from backend.db.state import accounts_state

log = logging.get_logger("agrosense.api")

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def create_app() -> FastAPI:
    settings = get_settings()
    logging.configure(settings.log_level, settings.log_format)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        log.info("api_started", detail="La API de AgroSense arrancó y ya atiende peticiones")
        yield
        log.info("api_stopped", detail="La API de AgroSense se apagó")

    app = FastAPI(
        title="AgroSense", version="0.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None, lifespan=lifespan
    )

    @app.middleware("http")
    async def same_origin_only(request: Request, call_next):
        """Protección contra CSRF: una petición que cambia datos solo se acepta si viene de la web.

        Los navegadores mandan `Origin` en toda petición que cambia datos. Si llega y no es el origen de la propia API
        ni uno de `WEB_ORIGINS`, se rechaza. Sin `Origin` no es un navegador (curl, pruebas) y no hay cookie que robar.
        """
        origin = request.headers.get("origin")
        if request.method not in SAFE_METHODS and origin is not None:
            own = f"{request.url.scheme}://{request.url.netloc}"
            if origin.rstrip("/") not in get_settings().allowed_origins | {own}:
                # Un middleware responde directo: los manejadores de errores solo ven lo que pasa dentro de las rutas.
                errors.explain(request, f"Petición rechazada: viene de {origin}, que no es la web de AgroSense (protección contra CSRF)")
                return errors.error_response(request, 403, "forbidden_origin", "Esta petición no viene de la web de AgroSense.")
        return await call_next(request)

    # El último middleware que se registra es el primero que corre: el identificador de petición envuelve a todos.
    errors.install(app)
    app.include_router(auth.router)

    @app.get("/api/v1/health", tags=["estado"])
    def health(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
        """La API responde aunque la base de datos no: `accounts` dice si las cuentas están disponibles y, si no, por qué."""
        state = accounts_state(db)
        errors.explain(request, f"Estado de la API consultado: cuentas {state.explanation}")
        return {
            "status": "ok",
            "accounts": {
                "available": state.available,
                "reason": state.reason,
                "current_migration": state.current,
                "expected_migration": state.expected,
            },
        }

    return app


app = create_app()
