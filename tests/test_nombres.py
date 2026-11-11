"""La rama y los commits de un PR dicen su HU (`scripts/check_names.py`, HU-022; docs/revision-de-pr.md, sección 1)."""

import importlib.util
from datetime import date
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("check_names", Path("scripts/check_names.py"))
check_names = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_names)

AHORA = date(2026, 11, 12)
ANTES = date(2026, 11, 10)


@pytest.mark.parametrize(
    "rama",
    ["fix/hu-076-hoy-en-la-region", "feature/hu-207-lluvia-por-satelite-con-gpm-imerg", "docs/hu-122-fuentes", "chore/sin-hu-prueba-lenta"],
)
def test_ramas_que_dicen_su_hu(rama):
    assert check_names.branch_ok(rama)


@pytest.mark.parametrize(
    "rama",
    [
        "fix/hoy-en-la-region",
        "feat/hu-076-hoy",
        "fix/HU-076-hoy",
        "fix/hu-76-hoy",
        "fix/hu-076",
        "fix/hu-076-Hoy",
        "hu-076-hoy",
        "desarrollo",
    ],
)
def test_ramas_sin_su_hu_o_mal_escritas(rama):
    assert not check_names.branch_ok(rama)


@pytest.mark.parametrize(
    "commit",
    [
        "fix(HU-076): «hoy» es el día en la región, no el del servidor",
        "feat(HU-207, HU-208): lluvia de IMERG y verdor por municipio",
        "chore(sin HU): la prueba de entrar deja de ser lenta",
    ],
)
def test_commits_que_empiezan_con_su_hu(commit):
    assert check_names.commit_ok(commit, AHORA)


@pytest.mark.parametrize(
    "commit",
    [
        "fix: «hoy» es el día en la región (HU-076)",  # el formato anterior, ya no
        "fix: «hoy» es el día en la región",
        "fix(HU-76): algo",
        "fix(hu-076): algo",
        "feature(HU-076): algo",
        "fix(HU-076):sin espacio",
        "Update README.md",
    ],
)
def test_commits_sin_su_hu_al_principio(commit):
    assert not check_names.commit_ok(commit, AHORA)


def test_los_commits_de_antes_del_cambio_pueden_tener_la_hu_al_final():
    assert check_names.commit_ok("feat: lluvia mensual de IMERG (HU-207)", ANTES)
    assert check_names.commit_ok("docs: cierra HU de cuentas (HU-160, HU-161)", ANTES)
    # Pero tienen que decir la HU igual.
    assert not check_names.commit_ok("feat: lluvia mensual de IMERG", ANTES)
