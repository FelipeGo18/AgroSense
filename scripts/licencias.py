# ruff: noqa: E501  (textos largos del documento que genera)
"""Genera docs/licencias.md (HU-230): la licencia del código, de los datos y de las librerías y materiales de terceros.

Lee `uv.lock` (con la licencia de cada paquete instalado en el entorno), `web/package-lock.json` y la tabla `sources` del
dataset publicado. Los materiales que no salen de ahí (el mapa, los íconos y el globo) están escritos abajo, en
`OTROS_MATERIALES`: si se agrega uno, se agrega ahí.

La licencia de cada paquete de Python sale de lo instalado (`importlib.metadata`): para que el resultado no dependa del
equipo donde se corre, se corre en Docker, con la imagen `app` reconstruida, y el documento sale por la salida estándar:

    docker compose build app
    docker compose run --rm -T -v ./web/package-lock.json:/app/web/package-lock.json:ro app \
        uv run python scripts/licencias.py --stdout > docs/licencias.md

Sin `--stdout` escribe `docs/licencias.md` directamente (fuera de Docker, con `uv sync`).
"""

import json
import sys
import tomllib
from collections import Counter
from importlib import metadata
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "licencias.md"

# Paquetes cuya metadata no trae la licencia: la de su repositorio. `colorama` y `tzdata` solo se instalan en Windows, así
# que en Docker (Linux) no hay metadata que leer.
FIX_PY = {"uvloop": "MIT OR Apache-2.0", "colorama": "BSD", "tzdata": "Apache-2.0"}
FIX_WEB = {"parse-cache-control": "Sin licencia declarada (solo herramienta de desarrollo, no va en la aplicación)"}
NORMAL = {"MIT License": "MIT", "BSD License": "BSD", "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0"}

OTROS_MATERIALES = [
    (
        "Mapa base de Mi finca",
        "OpenStreetMap, con el estilo «liberty» de OpenFreeMap y el esquema de OpenMapTiles (`web/src/components/map/MapCanvas.tsx`)",
        "Datos: ODbL 1.0 (© colaboradores de OpenStreetMap). Esquema de las teselas: CC BY 4.0 (© OpenMapTiles). El mapa muestra "
        "en pantalla «OpenFreeMap © OpenMapTiles Data from OpenStreetMap»",
    ),
    (
        "Íconos de las redes del equipo",
        "Font Awesome Free 6.5.2, copiados como SVG (`web/src/components/layout/brandIcons.ts`)",
        "CC BY 4.0 (https://fontawesome.com/license/free); la atribución está en el archivo",
    ),
    (
        "Globo de la portada",
        "Contornos de Natural Earth 1:110m y color de NASA Blue Marble: Next Generation (2004) (`web/src/assets/globe.json`)",
        "Natural Earth: dominio público. Blue Marble: imagen de la NASA, uso libre con crédito. La portada muestra el crédito",
    ),
    ("Tipografías", "Atkinson Hyperlegible y Fredoka, por `@fontsource`", "OFL-1.1"),
]


def lic(value: str, fixes: dict[str, str], name: str) -> str:
    value = fixes.get(name, value)
    return NORMAL.get(value, value)


def python_runtime(lock: dict) -> set[str]:
    """Los paquetes que van en la aplicación: las dependencias de `agrosense` y las de ellas, con sus extras
    (`psycopg[binary]`, `uvicorn[standard]`), sin el grupo `dev`."""
    packages = {pkg["name"]: pkg for pkg in lock["package"]}
    seen: set[tuple[str, str | None]] = set()
    pending = [(d["name"], extra) for d in packages["agrosense"].get("dependencies", []) for extra in (None, *d.get("extra", []))]
    while pending:
        name, extra = pending.pop()
        if (name, extra) in seen or name not in packages:
            continue
        seen.add((name, extra))
        pkg = packages[name]
        deps = pkg.get("dependencies", []) if extra is None else pkg.get("optional-dependencies", {}).get(extra, [])
        pending.extend((d["name"], e) for d in deps for e in (None, *d.get("extra", [])))
    return {name for name, _ in seen}


def python_packages() -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """Los de la aplicación y los que solo se usan para probar y revisar el código (grupo `dev`: pytest, ruff, httpx…)."""
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    runtime = python_runtime(lock)
    out = []
    for pkg in lock["package"]:
        name = pkg["name"]
        if name == "agrosense":
            continue
        if name in FIX_PY:
            out.append((name, pkg.get("version", ""), FIX_PY[name]))
            continue
        try:
            md = metadata.metadata(name)
            value = md.get("License-Expression") or ""
            if not value or len(value) > 60:
                classifiers = [c.split(" :: ")[-1] for c in (md.get_all("Classifier") or []) if c.startswith("License ::")]
                value = "; ".join(classifiers) or (md.get("License") or "")[:60]
        except metadata.PackageNotFoundError:
            value = "?"
        out.append((name, pkg.get("version", ""), lic(value.strip(), FIX_PY, name)))
    out.sort()
    return [p for p in out if p[0] in runtime], [p for p in out if p[0] not in runtime]


def web_packages() -> tuple[list[tuple[str, str, str]], Counter]:
    lock = json.loads((ROOT / "web" / "package-lock.json").read_text(encoding="utf-8"))
    prod, dev = [], Counter()
    for path, info in lock["packages"].items():
        if not path:
            continue
        name = path.split("node_modules/")[-1]
        value = lic(info.get("license", "?"), FIX_WEB, name)
        if info.get("dev"):
            dev[value] += 1
        else:
            prod.append((name, info.get("version", ""), value))
    return sorted(prod), dev


def cell(text: str | None) -> str:
    return (text or "").replace("|", "\\|")


def main() -> None:
    sources = (
        pl.read_parquet(ROOT / "data" / "published" / "sources.parquet")
        .select("source_id", "name", "institution", "license")
        .sort("source_id")
    )
    py, py_dev = python_packages()
    web_prod, web_dev = web_packages()
    lines = [
        "# Licencias de AgroSense y de lo que usa",
        "",
        "Documentación de las licencias de terceros que piden los términos de NASA Space Apps 2026 (HU-230; "
        "<https://www.spaceappschallenge.org/legal/>): el contenido original debe ser libre o tener una licencia aprobada por la OSI, "
        "y la NASA no acepta una solución sin la licencia de cada material de terceros. Se genera con `scripts/licencias.py`, en Docker (el comando está al principio del script).",
        "",
        "## El código de AgroSense",
        "",
        "Apache 2.0 (`LICENSE`, en la raíz del repositorio; aprobado por Felipe el 10 de noviembre de 2026). **Apache 2.0 cubre solo el código "
        "escrito por el equipo.** Los datos de `data/` y `catalog/` y los materiales de terceros conservan su propia licencia, la que dice cada "
        "tabla de abajo: el repositorio no los vuelve a licenciar bajo Apache. Por ejemplo, lo que sale de DIVIPOLA sigue siendo CC BY-SA 4.0 y "
        "las fichas de la UPRA siguen siendo de uso no comercial.",
        "",
        "## Lo que hay que saber",
        "",
        "- **GSAP** (`gsap` y `@gsap/react`, las animaciones de la web) no tiene una licencia de la OSI: usa la «Standard no-charge "
        "license» de GreenSock (<https://gsap.com/standard-license>), gratis para todo uso, también el comercial. Es su permiso "
        "documentado (decidido por Felipe el 14 de noviembre de 2026). Solo se carga con movimiento: en modo ligero no se descarga (HU-158).",
        "- **psycopg** (el conector de PostgreSQL) es LGPL-3.0, una licencia de la OSI; AgroSense lo usa como librería, sin modificarlo.",
        "- **Las fuentes sin licencia explícita** («Sin dato; se cita», «por confirmar» o «derechos reservados»): de esas publicaciones "
        "AgroSense solo toma cifras y hechos (temperaturas de daño, días por etapa, rangos de cultivo), con su cita. Los hechos no tienen "
        "derechos de autor, y no se reproduce el texto ni las figuras de ninguna.",
        "- **Las fichas de la UPRA** permiten la «reproducción parcial sin fines comerciales con cita»: AgroSense solo toma sus rangos de "
        "temperatura media, con la cita, y no es comercial.",
        "- **Lo que sale de DIVIPOLA del DANE** (CC BY-SA 4.0), como la tabla `municipalities`, se publica con esa misma licencia.",
        "",
        "## Datos y fuentes (tabla `sources` del dataset publicado)",
        "",
        "Cada dato y cada regla agronómica apunta a una de estas fuentes (R8).",
        "",
        "| Fuente | Institución | Licencia o condición de uso |",
        "|---|---|---|",
    ]
    for sid, name, inst, license_ in sources.iter_rows():
        lines.append(
            f"| `{sid}` · {cell(name)} | {cell(inst)} | {cell(license_ or 'Sin licencia explícita: se usan cifras con su cita')} |"
        )
    lines += [
        "",
        "## Otros materiales de terceros en la web",
        "",
        "No salen de `sources` ni de los lockfiles.",
        "",
        "| Material | De dónde sale | Licencia |",
        "|---|---|---|",
        *[f"| {a} | {b} | {c} |" for a, b, c in OTROS_MATERIALES],
        "",
        "Las imágenes de referencia del moodboard (HU-151) ya no están en el repositorio: eran solo referencia para Figma; su lista y "
        "su licencia quedan en `design/moodboard/FUENTES.md`.",
        "",
        f"## Librerías de Python que van en la aplicación ({len(py)}, de `uv.lock`)",
        "",
        "| Paquete | Versión | Licencia |",
        "|---|---|---|",
        *[f"| {n} | {v} | {cell(kind)} |" for n, v, kind in py],
        "",
        f"## Herramientas de desarrollo de Python ({len(py_dev)}, grupo `dev` de `uv.lock`; no van en la aplicación)",
        "",
        "Solo se usan para probar y revisar el código (pytest, Ruff y el cliente de pruebas de la API).",
        "",
        "| Paquete | Versión | Licencia |",
        "|---|---|---|",
        *[f"| {n} | {v} | {cell(kind)} |" for n, v, kind in py_dev],
        "",
        f"## Librerías de la web que van en la aplicación ({len(web_prod)}, de `web/package-lock.json`)",
        "",
        "| Paquete | Versión | Licencia |",
        "|---|---|---|",
        *[f"| {n} | {v} | {cell(kind)} |" for n, v, kind in web_prod],
        "",
        f"## Herramientas de desarrollo de la web ({sum(web_dev.values())} paquetes; no van en la aplicación)",
        "",
        "Solo se usan para construir y probar la web (Vite, TypeScript, Vitest, ESLint, Playwright…). Por licencia:",
        "",
        "| Licencia | Paquetes |",
        "|---|---|",
        *[f"| {cell(kind)} | {c} |" for kind, c in web_dev.most_common()],
        "",
    ]
    text = "\n".join(lines)
    summary = (
        f"{OUT.relative_to(ROOT)}: {sources.height} fuentes, {len(py)} de Python, {len(py_dev)} de desarrollo de Python, "
        f"{len(web_prod)} de la web y {sum(web_dev.values())} de desarrollo de la web"
    )
    if "--stdout" in sys.argv[1:]:
        sys.stdout.buffer.write(text.encode("utf-8"))
        print(summary, file=sys.stderr)
    else:
        OUT.write_bytes(text.encode("utf-8"))
        print(summary)


if __name__ == "__main__":
    main()
