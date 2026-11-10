"""`python -m backend.db.renumber`: cuando dos ramas crean la misma migración, la propia pasa detrás de la de la rama de
destino, con su número, su archivo y su carpeta (HU-229). Con migraciones de ejemplo en una carpeta temporal (R5)."""

from pathlib import Path

import pytest

from backend.db import renumber


def write(versions: Path, revision: str, down: str | None, slug: str) -> Path:
    folder = versions / revision.split(".")[0]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{revision}_{slug}.py"
    down_text = "None" if down is None else f'"{down}"'
    path.write_text(
        f'"""{slug}\n\nMigración {revision} · va después de {down}\nCreada el 2026-11-10\n"""\n\n'
        f'revision: str = "{revision}"\ndown_revision: str | None = {down_text}\n'
        "branch_labels = None\ndepends_on = None\n\n\ndef upgrade() -> None:\n    pass\n",
        encoding="utf-8",
    )
    return path


def test_la_propia_pasa_detras_de_la_que_ya_se_fusiono(tmp_path):
    theirs = [renumber.read(write(tmp_path, f"1.{n}", f"1.{n - 1}" if n > 1 else None, f"base_{n}")) for n in range(1, 5)]
    mine = [renumber.read(write(tmp_path, "1.4", "1.3", "mi_cambio"))]
    moves = renumber.plan(theirs, mine)
    assert [(m.migration.revision, m.revision, m.down_revision) for m in moves] == [("1.4", "1.5", "1.4")]

    created = renumber.apply(moves, tmp_path)
    assert [p.name for p in created] == ["1.5_mi_cambio.py"]
    text = created[0].read_text(encoding="utf-8")
    assert 'revision: str = "1.5"' in text
    assert 'down_revision: str | None = "1.4"' in text
    assert "Migración 1.5 · va después de 1.4" in text
    # La de la rama de destino queda intacta.
    assert 'revision: str = "1.4"' in (tmp_path / "1" / "1.4_base_4.py").read_text(encoding="utf-8")


def test_varias_propias_siguen_en_cadena_y_saltan_de_carpeta_despues_de_la_9(tmp_path):
    theirs = [renumber.read(write(tmp_path, f"1.{n}", f"1.{n - 1}" if n > 1 else None, f"base_{n}")) for n in range(1, 9)]
    mine = [
        renumber.read(write(tmp_path, "1.8", "1.7", "primera")),
        renumber.read(write(tmp_path, "1.9", "1.8", "segunda")),
    ]
    moves = renumber.plan(theirs, mine)
    assert [(m.migration.path.name, m.revision, m.down_revision) for m in moves] == [
        ("1.8_primera.py", "1.9", "1.8"),
        ("1.9_segunda.py", "2.1", "1.9"),
    ]
    created = renumber.apply(moves, tmp_path)
    assert [p.relative_to(tmp_path).as_posix() for p in created] == ["1/1.9_primera.py", "2/2.1_segunda.py"]


def test_si_ya_van_detras_no_hay_nada_que_renumerar(tmp_path):
    theirs = [renumber.read(write(tmp_path, "1.1", None, "base"))]
    mine = [renumber.read(write(tmp_path, "1.2", "1.1", "mia"))]
    assert renumber.plan(theirs, mine) == []
    assert renumber.plan(theirs, []) == []


def test_si_las_propias_no_forman_una_cadena_no_adivina(tmp_path):
    theirs = [renumber.read(write(tmp_path, "1.1", None, "base"))]
    mine = [renumber.read(write(tmp_path, "1.2", "1.1", "una")), renumber.read(write(tmp_path, "1.3", "1.1", "otra"))]
    with pytest.raises(renumber.RenumberError, match="cadena"):
        renumber.plan(theirs, mine)


def test_un_archivo_que_no_escribio_el_comando_se_rechaza(tmp_path):
    path = tmp_path / "1" / "1.1_raro.py"
    path.parent.mkdir()
    path.write_text("revision = '1.1'\n", encoding="utf-8")
    with pytest.raises(renumber.RenumberError, match="revision"):
        renumber.read(path)
