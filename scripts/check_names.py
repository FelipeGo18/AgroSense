"""Revisa que la rama y los commits de un PR digan su HU (docs/revision-de-pr.md, «Alcance, rama y commits»; HU-022).

    python scripts/check_names.py <rama> <rama de destino>

- Rama: `tipo/hu-xxx-descripcion-corta`, o `tipo/sin-hu-descripcion` si de verdad no corresponde a ninguna HU.
- Commit: `tipo(HU-xxx): descripción`, con una o varias HU (`tipo(HU-207, HU-208): …`) o `tipo(sin HU): …`.
- `tipo`: feat, fix, docs, perf, test o chore (en la rama, `feature` en vez de `feat`).

Los commits de merge no se revisan. Los hechos antes del 12 de noviembre de 2026 pueden usar el formato anterior,
`tipo: descripción (HU-xxx)`, que también dice la HU. Solo usa la biblioteca estándar: corre en GitHub Actions sin
instalar nada. Termina con error y dice qué corregir si algo no cumple.
"""

import re
import subprocess
import sys
from datetime import date, datetime

BRANCH_TYPES = ("feature", "fix", "docs", "perf", "test", "chore")
COMMIT_TYPES = ("feat", "fix", "docs", "perf", "test", "chore")
HU = r"HU-\d{3}"

BRANCH = re.compile(rf"^({'|'.join(BRANCH_TYPES)})/(hu-\d{{3}}|sin-hu)-[a-z0-9]+(-[a-z0-9]+)*$")
COMMIT = re.compile(rf"^({'|'.join(COMMIT_TYPES)})\(({HU}(, {HU})*|sin HU)\): \S")
# El formato anterior, que ya decía la HU al final. Vale para los commits de antes del cambio de regla.
LEGACY_COMMIT = re.compile(rf"^({'|'.join(COMMIT_TYPES)}): .*\({HU}(, {HU})*\)\.?$")
NEW_RULE_SINCE = date(2026, 11, 12)

BRANCH_HELP = "La rama debe ser `tipo/hu-xxx-descripcion-corta` (por ejemplo `fix/hu-076-hoy-en-la-region`), o `tipo/sin-hu-…`"
COMMIT_HELP = "El commit debe empezar con `tipo(HU-xxx): descripción` (por ejemplo `fix(HU-076): …`), o `tipo(sin HU): …`"


def branch_ok(name: str) -> bool:
    return bool(BRANCH.match(name))


def commit_ok(subject: str, committed: date) -> bool:
    if COMMIT.match(subject):
        return True
    return committed < NEW_RULE_SINCE and bool(LEGACY_COMMIT.match(subject))


def pr_commits(base: str) -> list[tuple[str, date, str]]:
    """Los commits del PR que no son merges: (hash corto, fecha, primera línea)."""
    # Un comando fijo de git, sin shell: la rama de destino solo elige el rango del log.
    out = subprocess.run(  # noqa: S603
        ["git", "log", "--no-merges", "--format=%h%x09%cI%x09%s", f"origin/{base}..HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    commits = []
    for line in out.splitlines():
        sha, when, subject = line.split("\t", 2)
        commits.append((sha, datetime.fromisoformat(when).date(), subject))
    return commits


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Uso: python scripts/check_names.py <rama> <rama de destino>")
        return 2
    branch, base = argv[1], argv[2]
    problems = []
    if not branch_ok(branch):
        problems.append(f"Rama «{branch}». {BRANCH_HELP}.")
    for sha, committed, subject in pr_commits(base):
        if not commit_ok(subject, committed):
            problems.append(f"Commit {sha} «{subject}». {COMMIT_HELP}.")
    if problems:
        print("La rama o los commits no dicen su HU (docs/revision-de-pr.md, sección 1):")
        for problem in problems:
            print(f"- {problem}")
        print("Para corregir un commit: `git commit --amend` (el último) o `git rebase -i` (los anteriores).")
        return 1
    print(f"Rama y commits con su HU: {branch}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
