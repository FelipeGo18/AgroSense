"""La API de AgroSense (M6): una capa delgada sobre las cuentas y, cuando exista, el motor.

uv run uvicorn backend.api.main:app --reload
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from sqlalchemy.orm import Session

from backend.api import auth, calculations, catalogs, errors, lots, market, seasons, version
from backend.config.settings import get_settings
from backend.config.thresholds import get_thresholds
from backend.config.weights import get_default_weights
from backend.db.session import get_db
from backend.db.state import accounts_state
from common import logging

log = logging.get_logger("agrosense.api")

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
DOCS_URL = "/api/docs"
OPENAPI_URL = "/api/openapi.json"
# Lo que es de una cuenta: nunca se guarda en caché.
PRIVATE_PREFIXES = ("/api/v1/auth/", "/api/v1/me", "/api/v1/lots", "/api/v1/seasons")


def create_app() -> FastAPI:
    settings = get_settings()
    logging.configure(settings.log_level, settings.log_format)
    # Si `weights.yaml` o `thresholds.yaml` no sirven, la API no arranca y dice por qué (HU-075).
    get_default_weights()
    get_thresholds()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        log.info("api_started", detail="La API de AgroSense arrancó y ya atiende peticiones")
        yield
        log.info("api_stopped", detail="La API de AgroSense se apagó")

    docs = settings.api_docs
    app = FastAPI(
        title="AgroSense",
        version="0.0.0",
        docs_url=DOCS_URL if docs else None,
        openapi_url=OPENAPI_URL if docs else None,
        redoc_url=None,
        lifespan=lifespan,
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

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        """Cabeceras de seguridad en toda respuesta, también en las que rechaza la protección contra CSRF.

        La API solo responde JSON: nada de lo suyo se interpreta como otro tipo, se muestra dentro de otra página ni
        carga recursos. Lo de la cuenta no se guarda en ninguna caché (ni del navegador ni de un proxy).
        """
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "no-referrer")
        # La página de la documentación (solo en desarrollo) carga su JavaScript y su estilo: no lleva esta política.
        if request.url.path != DOCS_URL:
            headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        if request.url.scheme == "https":
            headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith(PRIVATE_PREFIXES):
            headers["Cache-Control"] = "no-store"
        return response

    # El último middleware que se registra es el primero que corre: el identificador de petición envuelve a todos.
    errors.install(app)
    app.include_router(auth.router)
    app.include_router(version.router)
    app.include_router(catalogs.router)
    app.include_router(lots.router)
    app.include_router(seasons.router)
    app.include_router(calculations.router)
    app.include_router(market.router)

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
