"""Caché de las fuentes compartida (HU-237, parte 1): cada carpeta de `data/raw/` se guarda como un archivo en la
*release* `cache-datos` del repositorio, y `pipeline/raw_cache.json` (en git) dice cuál usa cada fuente.

Así cualquiera reconstruye el dataset desde la misma caché, sin pedírsela a nadie (R4):

    uv run python -m pipeline.raw_cache estado            # qué carpetas están al día
    uv run python -m pipeline.raw_cache traer [carpetas]   # baja lo que falte o sea distinto
    uv run python -m pipeline.raw_cache subir <carpeta>    # empaqueta, sube y anota en raw_cache.json

- **Paquete determinista:** los archivos van en orden, con fecha, dueño y permisos fijos, y el gzip sin fecha: el mismo
  contenido da el mismo archivo byte a byte. El nombre lleva la huella del contenido (`cache-<carpeta>-<huella>.tar.gz`),
  así que un archivo subido nunca se reemplaza: otro contenido es otro archivo.
- **Huella:** el sha256 de la lista ordenada de rutas con el sha256 de cada archivo. Los `.part` de una descarga a
  medias no cuentan.
- **Traer:** baja con los límites de tiempo y tamaño de `pipeline/sources/fetch.py`, verifica el sha256 del archivo,
  extrae en una carpeta aparte con el filtro `data` de `tarfile` (nada sale de la carpeta) y verifica la huella. Solo
  entonces reemplaza la carpeta. Si algo no coincide, falla y la carpeta queda como estaba (R1).
- **Licencias:** solo se suben las carpetas de `FOLDERS`, y cada una de sus fuentes debe tener su fila en
  `docs/licencias.md`: la *release* es pública.
- **Secretos:** no se sube un `.env` ni un archivo que contenga el token de Earthdata o el de GitHub de quien sube.
  Los tokens nunca van al log.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from common.logging import configure, get_logger
from pipeline.settings import get_settings
from pipeline.sources.fetch import fetch

log = get_logger("agrosense.pipeline.raw_cache")

RAW = Path("data/raw")
LOCK = Path("pipeline/raw_cache.json")
LICENSES = Path("docs/licencias.md")
RELEASE_TAG = "cache-datos"
API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"
PART_SUFFIX = ".part"

# Las carpetas de `data/raw/` que se pueden compartir, con las fuentes (`source_id`) que salen de cada una. Una carpeta
# nueva (por ejemplo, la de una fuente que trae un PR) se agrega aquí, con su licencia en `docs/licencias.md`.
FOLDERS: dict[str, tuple[str, ...]] = {
    "dane": ("dane_divipola", "dane_mgn_2025"),
    "eva": ("eva",),
    "imerg": ("imerg",),
    "modis_ndvi": ("modis_ndvi",),
    "nasa_power": ("nasa_power",),
    "nasadem": ("nasadem",),
    "sipsa": ("dane_sipsa",),
    "soilgrids": ("soilgrids",),
}


class CacheError(RuntimeError):
    """La caché no se pudo subir o traer: el porqué va en el mensaje, sin tokens."""


@dataclass(frozen=True)
class Entry:
    """Una carpeta de la caché tal como la anota `raw_cache.json`."""

    folder: str
    asset: str
    sha256: str
    tree: str
    bytes: int
    files: int
    source_ids: tuple[str, ...]
    uploaded_at: str


# ---------- huella y paquete ----------


def _files(folder: Path) -> list[Path]:
    """Los archivos de la carpeta, en orden y sin los `.part` de una descarga a medias."""
    return sorted(
        (path for path in folder.rglob("*") if path.is_file() and not path.name.endswith(PART_SUFFIX)),
        key=lambda path: path.relative_to(folder).as_posix(),
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_digest(folder: Path) -> str | None:
    """La huella del contenido de una carpeta, o None si no existe o está vacía."""
    if not folder.is_dir():
        return None
    files = _files(folder)
    if not files:
        return None
    digest = hashlib.sha256()
    for path in files:
        digest.update(f"{path.relative_to(folder).as_posix()}\0{_sha256_file(path)}\n".encode())
    return digest.hexdigest()


def _secrets() -> list[bytes]:
    settings = get_settings()
    tokens = (settings.earthdata_token, settings.cache_token)
    return [token.get_secret_value().encode() for token in tokens if token is not None and token.get_secret_value()]


def check_shareable(name: str, folder: Path, licenses: Path = LICENSES, secrets: Sequence[bytes] | None = None) -> None:
    """Falla si la carpeta no se puede publicar: fuera de `FOLDERS`, una fuente sin fila en `docs/licencias.md`, un
    `.env` o un archivo con un token adentro."""
    if name not in FOLDERS:
        raise CacheError(f"`{name}` no está en la lista de carpetas que se comparten (`FOLDERS` en pipeline/raw_cache.py)")
    text = licenses.read_text(encoding="utf-8") if licenses.is_file() else ""
    if missing := [source for source in FOLDERS[name] if f"| `{source}` ·" not in text]:
        raise CacheError(f"{name}: falta la licencia de {', '.join(missing)} en {licenses}: la caché sería pública")
    tokens = _secrets() if secrets is None else list(secrets)
    for path in _files(folder):
        if path.name == ".env" or path.name.startswith(".env."):
            raise CacheError(f"{name}: {path.relative_to(folder)} es un archivo de configuración y no se sube")
        data = path.read_bytes()
        if any(token in data for token in tokens):
            raise CacheError(f"{name}: {path.relative_to(folder)} contiene un token y no se sube")


def pack(name: str, folder: Path, out_dir: Path) -> tuple[Path, str]:
    """Empaqueta la carpeta en `out_dir`, determinista. Devuelve el archivo y la huella del contenido."""
    tree = tree_digest(folder)
    if tree is None:
        raise CacheError(f"{name}: la carpeta {folder} no existe o está vacía")
    target = out_dir / f"cache-{name}-{tree[:16]}.tar.gz"
    # Directo al archivo, sin armarlo en memoria (SIPSA son unos 300 MB). `filename=""` y `mtime=0` dejan la cabecera del
    # gzip sin nombre ni fecha: el mismo contenido da el mismo archivo.
    with (
        target.open("wb") as out,
        gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=0) as gz,
        tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar,
    ):
        for path in _files(folder):
            info = tarfile.TarInfo(path.relative_to(folder).as_posix())
            info.size = path.stat().st_size
            info.mtime, info.mode, info.uid, info.gid, info.uname, info.gname = 0, 0o644, 0, 0, "", ""
            with path.open("rb") as handle:
                tar.addfile(info, handle)
    return target, tree


# ---------- raw_cache.json ----------


def load_lock(lock: Path = LOCK) -> dict[str, Entry]:
    if not lock.is_file():
        return {}
    raw = json.loads(lock.read_text(encoding="utf-8"))
    return {name: Entry(folder=name, **{**item, "source_ids": tuple(item["source_ids"])}) for name, item in raw["folders"].items()}


def save_lock(entries: dict[str, Entry], lock: Path = LOCK) -> None:
    folders = {name: {k: v for k, v in asdict(entry).items() if k != "folder"} for name, entry in sorted(entries.items())}
    body = {"release": RELEASE_TAG, "folders": folders}
    lock.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------- GitHub ----------

Requester = Callable[[str, str, str | None, bytes | None, dict[str, str]], tuple[int, bytes]]


def _request(method: str, url: str, token: str | None, data: bytes | None, headers: dict[str, str]) -> tuple[int, bytes]:
    """Una llamada a la API de GitHub. Devuelve el estado y el cuerpo; los errores HTTP también (sin el token)."""
    request = urllib.request.Request(url, data=data, method=method)  # noqa: S310
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    for key, value in headers.items():
        request.add_header(key, value)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    timeout = get_settings().cache_timeout_s
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def _release(repo: str, token: str, request: Requester) -> dict:
    """La *release* de la caché; la crea si no existe (como prerelease, para que no sea «la última versión»)."""
    status, body = request("GET", f"{API}/repos/{repo}/releases/tags/{RELEASE_TAG}", token, None, {})
    if status == 200:
        return json.loads(body)
    if status != 404:
        raise CacheError(f"GitHub respondió {status} al buscar la release {RELEASE_TAG}")
    payload = {
        "tag_name": RELEASE_TAG,
        "name": "Caché de las fuentes del pipeline (HU-237)",
        "body": "Una carpeta de data/raw/ por archivo. Cuál usa cada fuente lo dice pipeline/raw_cache.json; cada fuente "
        "conserva su licencia (docs/licencias.md). No es una versión de AgroSense.",
        "prerelease": True,
    }
    status, body = request(
        "POST", f"{API}/repos/{repo}/releases", token, json.dumps(payload).encode(), {"Content-Type": "application/json"}
    )
    if status != 201:
        raise CacheError(f"GitHub respondió {status} al crear la release {RELEASE_TAG}")
    return json.loads(body)


def upload(path: Path, repo: str, token: str, request: Requester = _request) -> bool:
    """Sube el archivo a la *release*. Devuelve False si ya estaba (mismo nombre, mismo contenido)."""
    release = _release(repo, token, request)
    if any(asset.get("name") == path.name for asset in release.get("assets", [])):
        return False
    url = f"{UPLOADS}/repos/{repo}/releases/{release['id']}/assets?{urllib.parse.urlencode({'name': path.name})}"
    status, _ = request("POST", url, token, path.read_bytes(), {"Content-Type": "application/gzip"})
    if status != 201:
        raise CacheError(f"GitHub respondió {status} al subir {path.name}")
    return True


def asset_url(repo: str, asset: str) -> str:
    return f"https://github.com/{repo}/releases/download/{RELEASE_TAG}/{asset}"


def _download(url: str, dest: Path) -> Path:
    settings = get_settings()
    return fetch(urllib.request.Request(url), dest, settings.cache_timeout_s, int(settings.cache_max_mb * 2**20))  # noqa: S310


# ---------- subir, traer y estado ----------


def push(name: str, raw: Path = RAW, lock: Path = LOCK, request: Requester = _request) -> Entry:
    """Empaqueta `data/raw/<name>`, lo sube y lo anota en `raw_cache.json`."""
    settings = get_settings()
    if settings.cache_token is None or not settings.cache_token.get_secret_value():
        raise CacheError("Subir pide un token de GitHub con permiso de escritura: AGROSENSE_CACHE_TOKEN o GH_TOKEN")
    folder = raw / name
    check_shareable(name, folder)
    with tempfile.TemporaryDirectory() as tmp:
        path, tree = pack(name, folder, Path(tmp))
        sha = _sha256_file(path)
        size = path.stat().st_size
        fresh = upload(path, settings.cache_repo, settings.cache_token.get_secret_value(), request)
    entry = Entry(name, path.name, sha, tree, size, len(_files(folder)), FOLDERS[name], datetime.now(UTC).isoformat(timespec="seconds"))
    entries = load_lock(lock)
    previous = entries.get(name)
    if previous is not None and previous.asset == entry.asset:
        entry = previous  # mismo contenido: la entrada no cambia (R4)
    entries[name] = entry
    save_lock(entries, lock)
    log.info(
        "raw_cache_pushed",
        folder=name,
        asset=entry.asset,
        uploaded=fresh,
        detail=f"Caché de {name}: {entry.asset} ({entry.bytes / 2**20:.1f} MB, {entry.files} archivos)"
        + ("" if fresh else ", ya estaba en la release"),
    )
    return entry


def _safe_extract(archive: Path, dest: Path) -> None:
    """Extrae con el filtro `data`: nada fuera de la carpeta, ni enlaces, ni rutas absolutas."""
    try:
        with tarfile.open(archive, mode="r:gz") as tar:
            tar.extractall(dest, filter="data")
    except (tarfile.TarError, OSError) as error:
        raise CacheError(f"{archive.name} no se pudo extraer: {error}") from error


def pull(
    names: Iterable[str] | None = None, raw: Path = RAW, lock: Path = LOCK, download: Callable[[str, Path], Path] = _download
) -> list[str]:
    """Trae de la *release* las carpetas que no estén al día. Devuelve las que trajo."""
    entries = load_lock(lock)
    wanted = list(entries) if names is None else list(names)
    if unknown := [name for name in wanted if name not in entries]:
        raise CacheError(f"{', '.join(unknown)} no tiene entrada en {lock}")
    repo = get_settings().cache_repo
    pulled = []
    for name in wanted:
        entry = entries[name]
        folder = raw / name
        if tree_digest(folder) == entry.tree:
            log.info("raw_cache_current", folder=name, detail=f"Caché de {name}: al día")
            continue
        raw.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=raw) as tmp:
            try:
                archive = download(asset_url(repo, entry.asset), Path(tmp) / entry.asset)
            except OSError as error:  # red, tiempo o tamaño (`fetch`): un mensaje claro, no una traza
                raise CacheError(f"{entry.asset} no se pudo bajar: {error}; {folder} queda como estaba") from error
            if _sha256_file(archive) != entry.sha256:
                raise CacheError(f"{entry.asset}: el sha256 no coincide con {lock}; {folder} queda como estaba")
            staged = Path(tmp) / name
            _safe_extract(archive, staged)
            if tree_digest(staged) != entry.tree:
                raise CacheError(f"{entry.asset}: el contenido no coincide con su huella; {folder} queda como estaba")
            old = Path(tmp) / f"{name}.anterior"
            if folder.exists():
                folder.replace(old)
            try:
                staged.replace(folder)
            except OSError:
                if old.exists():
                    old.replace(folder)  # la carpeta vuelve a quedar como estaba
                raise
        pulled.append(name)
        log.info("raw_cache_pulled", folder=name, asset=entry.asset, detail=f"Caché de {name}: traída ({entry.asset})")
    return pulled


def status(raw: Path = RAW, lock: Path = LOCK) -> dict[str, str]:
    """Por carpeta: `al_dia`, `distinta`, `falta` (anotada y sin carpeta) o `sin_entrada` (carpeta sin anotar)."""
    entries = load_lock(lock)
    local = {path.name for path in raw.iterdir() if path.is_dir()} if raw.is_dir() else set()
    result = {}
    for name in sorted(set(entries) | (local & set(FOLDERS))):
        if name not in entries:
            result[name] = "sin_entrada"
            continue
        digest = tree_digest(raw / name)
        result[name] = "falta" if digest is None else "al_dia" if digest == entries[name].tree else "distinta"
    return result


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Caché compartida de las fuentes del pipeline (HU-237).")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("estado", help="Dice qué carpetas de data/raw/ están al día con pipeline/raw_cache.json.")
    bring = commands.add_parser("traer", help="Baja de la release las carpetas que no estén al día.")
    bring.add_argument("carpetas", nargs="*", help="Por defecto, todas las de raw_cache.json.")
    send = commands.add_parser("subir", help="Empaqueta, sube y anota en raw_cache.json.")
    send.add_argument("carpetas", nargs="+", choices=sorted(FOLDERS))
    args = parser.parse_args(argv)
    settings = get_settings()
    configure(settings.log_level, settings.log_format)
    try:
        if args.command == "estado":
            for name, state in status().items():
                log.info("raw_cache_status", folder=name, state=state, detail=f"{name}: {state.replace('_', ' ')}")
        elif args.command == "traer":
            pull(args.carpetas or None)
        else:
            for name in args.carpetas:
                push(name)
    except (CacheError, OSError) as error:
        log.error("raw_cache_failed", detail=str(error))
        sys.exit(1)


if __name__ == "__main__":
    main()
