"""La API de AgroSense (M6): una capa delgada sobre las cuentas y, cuando exista, el motor.

uv run uvicorn backend.api.main:app --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.convertors import Convertor, register_url_convertor
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.api import auth, calculations, catalogs, errors, lots, market, seasons, tickets, version
from backend.api.climate_signals import require_climate_normal
from backend.config.settings import get_settings
from backend.config.thresholds import get_thresholds
from backend.config.weights import get_default_weights
from backend.db.session import get_db
from backend.db.state import accounts_state
from common import logging
from common.region import region_timezone
from common.signal_sources import get_signal_sources

log = logging.get_logger("agrosense.api")

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
DOCS_URL = "/api/docs"
OPENAPI_URL = "/api/openapi.json"
# Lo que es de una cuenta: nunca se guarda en caché.
PRIVATE_PREFIXES = ("/api/v1/auth/", "/api/v1/me", "/api/v1/lots", "/api/v1/seasons")
# La política de las respuestas JSON de la API: no cargan nada ni se muestran dentro de otra página.
API_CSP = "default-src 'none'; frame-ancestors 'none'"
# La de la web (HU-023): su JavaScript, sus estilos y sus imágenes salen del mismo origen. Fuera de él solo el mapa
# (las teselas, las fuentes y los íconos de OpenFreeMap, `web/src/components/map/MapCanvas.tsx`) y las capas de la
# NASA GIBS del mapa del lote (HU-211: el catálogo WMTS, las teselas y la leyenda del NDVI, `web/src/app/config.ts`).
# `'unsafe-inline'` solo en los estilos: React y MapLibre ponen estilos en línea; ningún script va en línea. MapLibre
# arma imágenes y trabajadores con `blob:`.
MAP_ORIGIN = "https://tiles.openfreemap.org"
GIBS_ORIGIN = "https://gibs.earthdata.nasa.gov"
WEB_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    f"img-src 'self' data: blob: {MAP_ORIGIN} {GIBS_ORIGIN}; "
    "font-src 'self' data:; "
    f"connect-src 'self' {MAP_ORIGIN} {GIBS_ORIGIN}; "
    "worker-src 'self' blob:; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


class WebPath(Convertor):
    """Una ruta de la web: cualquiera que no sea de la API. Así `/api/...` nunca cae en la web, y una ruta de la API
    responde igual con la web que sin ella (404, 405 y la redirección de la barra final)."""

    regex = r"(?!api(?:/|$)).*"

    def convert(self, value: str) -> str:
        return value

    def to_string(self, value: str) -> str:
        return value


register_url_convertor("web", WebPath())


def create_app() -> FastAPI:
    settings = get_settings()
    logging.configure(settings.log_level, settings.log_format)
    # Si `weights.yaml`, `thresholds.yaml` o `catalog/sources.yaml` no sirven, la API no arranca y dice por qué (HU-075,
    # HU-122). El motor los recibe ya leídos (R6).
    get_default_weights()
    get_thresholds()
    get_signal_sources()
    # Un dataset publicado sin el periodo normal tampoco: las señales de clima no se evaluarían (Haider, PR #115).
    require_climate_normal()
    # «Hoy» es el día en la región: sin su zona horaria, la API no arranca (`common/region.py`).
    region_timezone()

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
        # La página de la documentación (solo en desarrollo) carga su JavaScript y su estilo de un CDN: no lleva
        # política. La web servida (HU-023) lleva la suya.
        if request.url.path == DOCS_URL:
            pass
        elif getattr(request.app.state, "serves_web", False) and not request.url.path.startswith("/api/"):
            headers.setdefault("Content-Security-Policy", WEB_CSP)
        else:
            headers.setdefault("Content-Security-Policy", API_CSP)
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
    app.include_router(tickets.router)
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

    web_dir = get_settings().web_dir
    if web_dir is not None:
        install_web(app, web_dir)

    return app


class WebGZip:
    """Comprime lo de la web (`web/README.md`, «Qué debe hacer el alojamiento»): Cloud Run no comprime. Las respuestas
    de la API van sin comprimir, como hasta ahora: llevan datos de la cuenta y no hace falta exponerlas a BREACH."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.gzip = GZipMiddleware(app, minimum_size=1000)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not scope["path"].startswith("/api/"):
            await self.gzip(scope, receive, send)
        else:
            await self.app(scope, receive, send)


# Los archivos de `assets/` llevan el hash de su contenido en el nombre: nunca cambian. El HTML sí, en cada despliegue,
# y se revisa siempre, para que no pida trozos que ya no existen.
ASSETS_CACHE = "public, max-age=31536000, immutable"
HTML_CACHE = "no-cache"


def install_web(app: FastAPI, web_dir: Path) -> None:
    """Sirve el build de la web en el mismo origen que la API (HU-023): la cookie de sesión viaja sin CORS, como en
    desarrollo con el puente de Vite. Lo que pide `web/README.md` al alojamiento:

    - un archivo que existe se sirve tal cual, y una página dibujada en el build también (`/entrar` →
      `entrar/index.html`);
    - un archivo que no existe (con extensión, o bajo `assets/`) es un 404: después de un despliegue, una pestaña
      abierta que pide un trozo viejo no recibe HTML en su lugar;
    - cualquier otra ruta recibe `app.html`, el cascarón vacío, y la resuelve React Router.

    Lo que empieza por `/api/` nunca cae aquí (`WebPath`)."""
    root = web_dir.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError(f"AGROSENSE_WEB_DIR no tiene el build de la web (falta {index}).")
    # Sin el cascarón (un build viejo), `index.html`: la aplicación nota que no es su ruta y dibuja de cero.
    shell = root / "app.html" if (root / "app.html").is_file() else index
    app.state.serves_web = True
    app.add_middleware(WebGZip)

    def send(file: Path, path: str) -> FileResponse:
        if path.startswith("assets/"):
            cache = ASSETS_CACHE
        elif file.suffix == ".html":
            cache = HTML_CACHE
        else:
            cache = None
        return FileResponse(file, headers={"Cache-Control": cache} if cache else None)

    @app.api_route("/{path:web}", methods=["GET", "HEAD"], include_in_schema=False)
    def web(path: str) -> FileResponse:
        for candidate in (root / path, root / path / "index.html"):
            resolved = candidate.resolve()
            # Nada fuera de la carpeta del build (`..` en la ruta).
            if resolved.is_file() and resolved.is_relative_to(root):
                return send(resolved, path)
        if path.startswith("assets/") or "." in path.rsplit("/", 1)[-1]:
            raise HTTPException(status_code=404)
        return send(shell, path)


app = create_app()
