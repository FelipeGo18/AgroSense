"""Cómo se numeran las migraciones (backend/README.md, «Cómo se numeran»). Solo la biblioteca estándar de Python: así
`python -m backend.db.renumber` corre en cualquier computador, sin Docker ni las dependencias del proyecto (HU-229).

Dos números: `1.1`, `1.2` … `1.9` y después `2.1`. El primer número es la carpeta: `1/` guarda de la `1.1` a la `1.9` y
`2/` empieza otra vez en `2.1`.
"""

import re
from pathlib import Path

VERSIONS = Path(__file__).parent / "migrations" / "versions"
FILE = re.compile(r"^(\d+)\.([1-9])_.+\.py$")
# Cada carpeta guarda nueve migraciones: de la .1 a la .9.
PER_FOLDER = 9

Number = tuple[int, int]


def existing(versions_dir: Path = VERSIONS) -> list[Number]:
    """Las migraciones que hay, como (carpeta, número), en orden."""
    found = []
    for folder in versions_dir.iterdir() if versions_dir.exists() else []:
        if not (folder.is_dir() and folder.name.isdigit()):
            continue
        for file in folder.glob("*.py"):
            match = FILE.match(file.name)
            if match and match[1] == folder.name:
                found.append((int(match[1]), int(match[2])))
    return sorted(found)


def after(number: Number) -> Number:
    """La que sigue: de 1.1 a 1.9 sube el segundo número; después de 1.9 viene 2.1."""
    folder, position = number
    return (folder, position + 1) if position < PER_FOLDER else (folder + 1, 1)


def next_revision(found: list[Number]) -> tuple[str, str]:
    """La carpeta y el identificador de la migración que toca crear."""
    folder, position = after(found[-1]) if found else (1, 1)
    return str(folder), f"{folder}.{position}"
