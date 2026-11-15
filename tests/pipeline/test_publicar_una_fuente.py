"""Publicar una sola fuente: `pipeline.build --solo catalogo` (HU-238, parte 1).

Interfaz fijada: `build.publish_one(source, *, published=build.PUBLISHED)` y `--solo <fuente>` en `main()`. Todos los
errores son `build.ValidationError` (o `CatalogError` si lo lanza la validación del catálogo). Sin red: el dataset de
prueba sale de `rebuild` con las cachés de ejemplo; el catálogo se cambia en memoria, nunca en `catalog/crops.yaml`.
Datos de ejemplo, inventados.
"""

import copy
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import polars as pl
import pytest
import yaml
from structlog.testing import capture_logs

from pipeline import build, schema
from pipeline import catalog as crops_catalog
from tests.pipeline.test_reconstruir import REGION, caches, rebuild  # noqa: F401  (`caches` es un fixture)

FUENTES = ("catalogo", "municipios", "relieve", "suelo", "clima", "lluvia", "ndvi", "oferta", "precios")
ERRORES_DE_CATALOGO = (build.ValidationError, crops_catalog.CatalogError)
VERSION_NUEVA = "0.0.1-pruebas"
REGLAS_NUEVAS = "9.9.9-pruebas"
MUNICIPIO = "15407"  # uno de los municipios de ejemplo de `tests/conftest.py`


@pytest.fixture
def publicado(tmp_path, caches):  # noqa: F811
    return rebuild(tmp_path, caches)


def sha_de_tablas(folder):
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.glob("*.parquet"))}


def sha_de_todo(folder):
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.iterdir())}


def manifiesto(folder):
    return json.loads((folder / "manifest.json").read_text(encoding="utf-8"))


def fuentes_por_id(folder):
    return {row["source_id"]: row for row in pl.read_parquet(folder / "sources.parquet").to_dicts()}


def cambiar_catalogo(monkeypatch, editar, version=None):
    """El catálogo real, copiado y editado en memoria; opcionalmente con otra `dataset_version`."""
    real = crops_catalog.load()
    catalogo = copy.deepcopy(real)
    editar(catalogo)
    monkeypatch.setattr(build.crops_catalog, "load", lambda *_args, **_kwargs: catalogo)
    if version is not None:
        monkeypatch.setattr(build, "load_region", lambda: {**REGION, "dataset_version": version})


def con_nota(fuente_id, nota):
    def editar(catalogo):
        next(s for s in catalogo["sources"] if s["source_id"] == fuente_id)["notes"] = nota

    return editar


def fuente_nueva(catalogo):
    copia = dict(catalogo["sources"][0])
    copia |= {"source_id": "ejemplo_fuente_nueva", "name": "Ejemplo: fuente agregada en la prueba", "notes": "Ejemplo."}
    catalogo["sources"].append(copia)


def escribir_manifiesto(folder, manifest):
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def con_tabla(folder, name, table):
    """Lo publicado con una tabla más (o reemplazada), escrita como la escribe el pipeline y nombrada en el manifiesto."""
    table = schema.typed(name, table)
    schema.check(name, table)
    table.write_parquet(folder / f"{name}.parquet")
    manifest = manifiesto(folder)
    manifest["tables"][name] = {"rows": table.height, "coverage": "Ejemplo: tabla armada por la prueba."}
    escribir_manifiesto(folder, manifest)


def tabla_de(name, rows):
    return pl.DataFrame(rows, schema={column: spec.dtype for column, spec in schema.TABLES[name].columns.items()})


def con_fuentes(folder, *source_ids):
    """Lo publicado con filas más en `sources`, rotuladas como ejemplo (R5)."""
    nuevas = [{"source_id": source_id, "name": f"Ejemplo: {source_id}", "notes": "Ejemplo de la prueba."} for source_id in source_ids]
    table = build.sources_table(pl.concat([pl.read_parquet(folder / "sources.parquet"), pl.DataFrame(nuevas)], how="diagonal_relaxed"))
    con_tabla(folder, "sources", table)


def fila_de_oferta(crop_id, source_id, year=2024):
    return {
        "municipality_id": MUNICIPIO, "crop_id": crop_id, "year": year, "semester": "A", "source_id": source_id,
        "planted_ha": 10.0, "harvested_ha": 10.0, "production_t": 100.0, "yield_t_ha": 10.0, "planted_change_pct": 0.0,
        "dept_share_pct": None, "preliminary": False, "quality": "ok",
    }  # fmt: skip


def fila_de_mercado(crop_id, source_id):
    return {
        "crop_id": crop_id, "market_id": "ejemplo", "month": 1, "product_id": crop_id, "price_cop_kg": 1000, "price_year": 2025,
        "volume_t": 1.0, "seasonal_index": 1.0, "years": 3, "years_above": 1, "years_below": 1, "first_year": 2023,
        "last_year": 2025, "quality": "ok", "source_id": source_id,
    }  # fmt: skip


def sin_cultivo(crop_id):
    def editar(catalogo):
        catalogo["crops"] = [c for c in catalogo["crops"] if c["crop_id"] != crop_id]

    return editar


def cultivo_nuevo(catalogo):
    copia = copy.deepcopy(next(c for c in catalogo["crops"] if c["crop_id"] == "papa"))
    copia["crop_id"] = "ejemplo_cultivo_nuevo"
    catalogo["crops"].append(copia)


def primera_fuente_del_catalogo():
    return crops_catalog.load()["sources"][0]["source_id"]


# 1. Solo cambian las tablas del catálogo


def test_cambiar_una_nota_del_catalogo_cambia_solo_sources_y_el_manifiesto(publicado, monkeypatch):
    fuente_id = primera_fuente_del_catalogo()
    antes, manifiesto_antes = sha_de_tablas(publicado), manifiesto(publicado)
    cambiar_catalogo(monkeypatch, con_nota(fuente_id, "Ejemplo: nota nueva de la prueba."), VERSION_NUEVA)

    build.publish_one("catalogo", published=publicado)

    despues = sha_de_tablas(publicado)
    assert set(despues) == set(antes)
    assert {name for name in antes if antes[name] != despues[name]} == {"sources.parquet"}
    assert fuentes_por_id(publicado)[fuente_id]["notes"] == "Ejemplo: nota nueva de la prueba."
    manifiesto_despues = manifiesto(publicado)
    assert manifiesto_despues["dataset_version"] == VERSION_NUEVA
    assert manifiesto_despues["rules_version"] == manifiesto_antes["rules_version"]
    for tabla, info in manifiesto_antes["tables"].items():
        assert manifiesto_despues["tables"][tabla] == info, tabla
    build.verify(publicado, VERSION_NUEVA)


def test_cambiar_un_valor_de_una_ficha_cambia_solo_crops(publicado, monkeypatch):
    def editar(catalogo):
        papa = next(c for c in catalogo["crops"] if c["crop_id"] == "papa")
        papa["tmean_max_c"]["v"] = papa["tmean_max_c"]["v"] + 1

    antes = sha_de_tablas(publicado)
    cambiar_catalogo(monkeypatch, editar, VERSION_NUEVA)

    build.publish_one("catalogo", published=publicado)

    despues = sha_de_tablas(publicado)
    assert {name for name in antes if antes[name] != despues[name]} == {"crops.parquet"}
    build.verify(publicado, VERSION_NUEVA)


def test_la_version_de_las_reglas_del_manifiesto_sigue_a_la_del_catalogo(publicado, monkeypatch):
    """`rules_version` es la del catálogo y la de las reglas (decisión 16): si suben, el manifiesto las sigue."""
    assert manifiesto(publicado)["rules_version"] != REGLAS_NUEVAS
    load_reglas = build.rotation_rules.load

    def editar(catalogo):
        catalogo["version"] = REGLAS_NUEVAS
        con_nota(primera_fuente_del_catalogo(), "Ejemplo: nota nueva de la prueba.")(catalogo)

    cambiar_catalogo(monkeypatch, editar, VERSION_NUEVA)
    monkeypatch.setattr(build.rotation_rules, "load", lambda *a, **k: {**load_reglas(*a, **k), "version": REGLAS_NUEVAS})

    build.publish_one("catalogo", published=publicado)

    assert manifiesto(publicado)["rules_version"] == REGLAS_NUEVAS
    build.verify(publicado, VERSION_NUEVA)


def test_al_publicar_created_at_cambia_y_si_nada_cambia_no(publicado, monkeypatch):
    viejo = "2000-01-01T00:00:00+00:00"
    escribir_manifiesto(publicado, {**manifiesto(publicado), "created_at": viejo})

    build.publish_one("catalogo", published=publicado)  # nada cambió: el manifiesto queda como estaba
    assert manifiesto(publicado)["created_at"] == viejo

    cambiar_catalogo(monkeypatch, con_nota(primera_fuente_del_catalogo(), "Ejemplo: nota nueva."), VERSION_NUEVA)
    build.publish_one("catalogo", published=publicado)

    despues = manifiesto(publicado)["created_at"]
    assert despues != viejo and datetime.fromisoformat(despues) > datetime.fromisoformat(viejo)


# 2. `sources` sin perder ni duplicar


def test_las_fuentes_que_no_son_del_catalogo_quedan_iguales_y_ninguna_se_repite(publicado, monkeypatch):
    del_catalogo = {s["source_id"] for s in crops_catalog.load()["sources"]}
    antes = fuentes_por_id(publicado)
    ajenas = {source_id: row for source_id, row in antes.items() if source_id not in del_catalogo}
    assert ajenas, "el dataset de prueba debe traer fuentes que no son del catálogo (DIVIPOLA, límites, SIPSA)"
    cambiar_catalogo(monkeypatch, con_nota(primera_fuente_del_catalogo(), "Ejemplo: otra nota."), VERSION_NUEVA)

    build.publish_one("catalogo", published=publicado)

    ids = pl.read_parquet(publicado / "sources.parquet")["source_id"].to_list()
    assert len(ids) == len(set(ids))
    despues = fuentes_por_id(publicado)
    assert {source_id: despues[source_id] for source_id in ajenas} == ajenas
    assert set(despues) == set(antes)


def test_una_fuente_que_se_quita_del_catalogo_desaparece_de_sources(tmp_path, caches, monkeypatch):  # noqa: F811
    real = crops_catalog.load
    cambiar_catalogo(monkeypatch, fuente_nueva)
    folder = rebuild(tmp_path, caches)
    assert "ejemplo_fuente_nueva" in fuentes_por_id(folder)
    antes = fuentes_por_id(folder)

    monkeypatch.setattr(build.crops_catalog, "load", real)  # vuelve el catálogo real, sin la fuente
    monkeypatch.setattr(build, "load_region", lambda: {**REGION, "dataset_version": VERSION_NUEVA})
    build.publish_one("catalogo", published=folder)

    despues = fuentes_por_id(folder)
    assert "ejemplo_fuente_nueva" not in despues
    assert set(despues) == set(antes) - {"ejemplo_fuente_nueva"}
    build.verify(folder, VERSION_NUEVA)


# 3. Determinista (R4)


def test_dos_corridas_iguales_dan_los_mismos_archivos_y_las_mismas_tablas_del_manifiesto(tmp_path, caches, monkeypatch):  # noqa: F811
    a, b = rebuild(tmp_path / "a", caches), rebuild(tmp_path / "b", caches)
    cambiar_catalogo(monkeypatch, con_nota(primera_fuente_del_catalogo(), "Ejemplo: nota nueva."), VERSION_NUEVA)

    build.publish_one("catalogo", published=a)
    build.publish_one("catalogo", published=b)

    assert sha_de_tablas(a) == sha_de_tablas(b)
    assert manifiesto(a)["tables"] == manifiesto(b)["tables"]
    assert manifiesto(a)["rules_version"] == manifiesto(b)["rules_version"]


@pytest.mark.parametrize("que_cambia", ["nota", "cultivo_nuevo"])
def test_solo_catalogo_da_lo_mismo_que_la_construccion_completa(tmp_path, caches, monkeypatch, que_cambia):  # noqa: F811
    """Lo publicado sale de un solo camino (R4): `--solo` y `build()` dan las mismas tablas y el mismo manifiesto."""
    solo = rebuild(tmp_path / "solo", caches)
    antes = manifiesto(solo)["tables"]
    editar = con_nota(primera_fuente_del_catalogo(), "Ejemplo: nota nueva.") if que_cambia == "nota" else cultivo_nuevo
    cambiar_catalogo(monkeypatch, editar, VERSION_NUEVA)
    completo = rebuild(tmp_path / "completo", caches)

    build.publish_one("catalogo", published=solo)

    assert sha_de_tablas(solo) == sha_de_tablas(completo)
    tablas = manifiesto(solo)["tables"]
    assert tablas == manifiesto(completo)["tables"]  # filas y cobertura de cada tabla
    cambiaron = {name for name in tablas if tablas[name] != antes[name]}
    assert cambiaron == (set() if que_cambia == "nota" else {"crops", "crop_stages"})
    for campo in ("dataset_version", "rules_version"):
        assert manifiesto(solo)[campo] == manifiesto(completo)[campo]


# 4. Misma versión con cambios


def test_misma_version_con_cambios_falla_y_no_escribe_nada(publicado, monkeypatch):
    antes = sha_de_todo(publicado)
    cambiar_catalogo(monkeypatch, con_nota(primera_fuente_del_catalogo(), "Ejemplo: nota nueva."))  # misma versión

    with pytest.raises(build.ValidationError, match="dataset_version"):
        build.publish_one("catalogo", published=publicado)

    assert sha_de_todo(publicado) == antes


def fechas_de(folder):
    return {path.name: path.stat().st_mtime_ns for path in sorted(folder.iterdir())}


def test_si_nada_cambio_no_escribe(publicado):
    antes = sha_de_todo(publicado)
    for path in publicado.iterdir():
        os.utime(path, ns=(10**18, 10**18))  # una fecha vieja: reescribir los mismos bytes la cambiaría
    fechas = fechas_de(publicado)

    build.publish_one("catalogo", published=publicado)

    assert sha_de_todo(publicado) == antes  # ni las tablas ni el manifiesto (`created_at` incluido)
    assert fechas_de(publicado) == fechas  # ni siquiera tocó los archivos


def test_si_nada_cambio_pero_la_version_es_otra_no_escribe(publicado, monkeypatch):
    """Sin cambios en los bytes de las tablas no hay nada que publicar, aunque `region.yaml` diga otra versión."""
    antes = sha_de_todo(publicado)
    monkeypatch.setattr(build, "load_region", lambda: {**REGION, "dataset_version": VERSION_NUEVA})

    build.publish_one("catalogo", published=publicado)

    assert sha_de_todo(publicado) == antes


# 5 y 6. Valores de `<fuente>`


def test_un_valor_desconocido_falla_con_la_lista_de_valores_validos(publicado):
    antes = sha_de_todo(publicado)

    with pytest.raises(build.ValidationError) as error:
        build.publish_one("inventado", published=publicado)

    for fuente in FUENTES:
        assert fuente in str(error.value)
    assert sha_de_todo(publicado) == antes


@pytest.mark.parametrize("fuente", [f for f in FUENTES if f != "catalogo"])
def test_una_fuente_sin_implementar_falla_y_no_escribe(publicado, fuente):
    antes = sha_de_todo(publicado)

    with pytest.raises(build.ValidationError, match="no implementado en este PR"):
        build.publish_one(fuente, published=publicado)

    assert sha_de_todo(publicado) == antes


def test_por_la_linea_de_comandos_un_valor_desconocido_sale_con_error_y_dice_los_validos(publicado, monkeypatch, capsys):
    monkeypatch.setattr(build, "PUBLISHED", publicado)
    monkeypatch.setattr(sys, "argv", ["pipeline.build", "--solo", "inventado"])
    monkeypatch.setattr(build, "configure", lambda *_args, **_kwargs: None)
    with capture_logs() as logs, pytest.raises(SystemExit) as salida:
        build.main()
    assert salida.value.code != 0
    # El mensaje puede salir por el log (nuestro error) o por argparse (`choices`, en stderr): en los dos dice los valores.
    mensaje = " ".join([line.get("detail", "") for line in logs] + [capsys.readouterr().err])
    assert all(fuente in mensaje for fuente in FUENTES)


def test_por_la_linea_de_comandos_solo_catalogo_publica_y_revisa(publicado, monkeypatch):
    monkeypatch.setattr(build, "PUBLISHED", publicado)
    cambiar_catalogo(monkeypatch, con_nota(primera_fuente_del_catalogo(), "Ejemplo: nota nueva."), VERSION_NUEVA)
    monkeypatch.setattr(sys, "argv", ["pipeline.build", "--solo", "catalogo"])
    monkeypatch.setattr(build, "configure", lambda *_args, **_kwargs: None)
    build.main()
    assert manifiesto(publicado)["dataset_version"] == VERSION_NUEVA
    build.verify(publicado, VERSION_NUEVA)


@pytest.mark.parametrize("opcion", ["--descargar", "--traer-cache", "--verificar"])
def test_solo_no_se_combina_con_otras_opciones_y_no_escribe(publicado, monkeypatch, capsys, opcion):
    monkeypatch.setattr(build, "PUBLISHED", publicado)
    cambiar_catalogo(monkeypatch, con_nota(primera_fuente_del_catalogo(), "Ejemplo: nota nueva."), VERSION_NUEVA)
    monkeypatch.setattr(sys, "argv", ["pipeline.build", "--solo", "catalogo", opcion])
    monkeypatch.setattr(build, "configure", lambda *_args, **_kwargs: None)
    antes = sha_de_todo(publicado)

    with pytest.raises(SystemExit) as salida:
        build.main()

    assert salida.value.code not in (0, None)
    assert "raw_cache traer" in capsys.readouterr().err
    assert sha_de_todo(publicado) == antes


def test_si_falla_el_segundo_reemplazo_todo_queda_como_estaba(publicado, monkeypatch):
    """Cambian `crops`, `crop_stages` y el manifiesto (cultivo nuevo): si el reemplazo falla a la mitad, ningún archivo cambia."""
    cambiar_catalogo(monkeypatch, cultivo_nuevo, VERSION_NUEVA)
    antes = sha_de_todo(publicado)
    reemplazar = Path.replace
    reemplazos = []

    def falla_el_segundo(self, target):
        if self.name.endswith(".tmp"):  # los `.bak` que se restauran no cuentan
            reemplazos.append(self.name)
            if len(reemplazos) == 2:
                raise OSError("disco lleno (simulado en la prueba)")
        return reemplazar(self, target)

    monkeypatch.setattr(Path, "replace", falla_el_segundo)

    with pytest.raises(OSError, match="simulado"):
        build.publish_one("catalogo", published=publicado)

    assert len(reemplazos) == 2  # el primero se reemplazó de verdad y el segundo falló
    assert sha_de_todo(publicado) == antes  # los mismos archivos, con los mismos bytes: sin `.tmp` ni `.bak`
    assert not [p.name for p in publicado.iterdir() if p.suffix in (".tmp", ".bak")]


# 7. Sin lo publicado


def test_sin_la_carpeta_publicada_falla(tmp_path):
    with pytest.raises(build.ValidationError, match="pipeline.build"):
        build.publish_one("catalogo", published=tmp_path / "no-existe")
    assert not (tmp_path / "no-existe").exists()


def test_sin_manifiesto_falla_y_no_escribe(publicado):
    (publicado / "manifest.json").unlink()
    antes = sha_de_todo(publicado)

    with pytest.raises(build.ValidationError, match="pipeline.build"):
        build.publish_one("catalogo", published=publicado)

    assert sha_de_todo(publicado) == antes


# 8. Las validaciones cruzadas siguen corriendo


def test_un_catalogo_con_una_fuente_inexistente_falla_sin_escribir(publicado, monkeypatch):
    def editar(catalogo):
        next(c for c in catalogo["crops"] if c["crop_id"] == "papa")["family"]["s"] = "fuente_que_no_existe"

    antes = sha_de_todo(publicado)
    cambiar_catalogo(monkeypatch, editar, VERSION_NUEVA)

    with pytest.raises(ERRORES_DE_CATALOGO, match="fuente_que_no_existe"):
        build.publish_one("catalogo", published=publicado)

    assert sha_de_todo(publicado) == antes


def test_quitar_un_cultivo_que_las_reglas_usan_falla_sin_escribir(publicado, monkeypatch):
    """Las reglas de rotación y las fichas dependen de la papa: sin ella el catálogo no es válido y no se publica nada (R8)."""
    antes = sha_de_todo(publicado)
    cambiar_catalogo(monkeypatch, sin_cultivo("papa"), VERSION_NUEVA)

    with pytest.raises(ERRORES_DE_CATALOGO):
        build.publish_one("catalogo", published=publicado)

    assert sha_de_todo(publicado) == antes


# 9. Lo que añade `publish_one` al catálogo: las validaciones del conjunto completo (R7, R8)


def test_quitar_un_cultivo_que_usa_la_oferta_publicada_falla_sin_escribir(publicado, monkeypatch):
    """El catálogo solo es válido (las reglas no usan la zanahoria), pero `supply_semester` publicada la cita: la valida
    `validate_dataset` sobre el conjunto completo."""
    con_tabla(publicado, "supply_semester", tabla_de("supply_semester", [fila_de_oferta("zanahoria", "dane_divipola")]))
    antes = sha_de_todo(publicado)
    cambiar_catalogo(monkeypatch, sin_cultivo("zanahoria"), VERSION_NUEVA)

    with pytest.raises(build.ValidationError, match="supply_semester.*cultivos que no están en el catálogo"):
        build.publish_one("catalogo", published=publicado)

    assert sha_de_todo(publicado) == antes


def test_quitar_un_cultivo_que_usa_el_mercado_publicado_falla_sin_escribir(publicado, monkeypatch):
    """`market_month` no la valida `validate_dataset` con lo publicado: lo comprueba `publish_one` contra `crops`."""
    con_tabla(publicado, "market_month", tabla_de("market_month", [fila_de_mercado("zanahoria", "dane_divipola")]))
    antes = sha_de_todo(publicado)
    cambiar_catalogo(monkeypatch, sin_cultivo("zanahoria"), VERSION_NUEVA)

    with pytest.raises(build.ValidationError, match="market_month. trae cultivos que no están en el catálogo"):
        build.publish_one("catalogo", published=publicado)

    assert sha_de_todo(publicado) == antes


def test_una_tabla_publicada_mal_formada_falla_con_el_esquema_sin_escribir(publicado, monkeypatch):
    """Dos filas con la misma llave: `validate_dataset` no lo mira en `supply_semester`, `schema.check` sí."""
    filas = [fila_de_oferta("papa", "dane_divipola")] * 2
    con_tabla_sin_revisar = tabla_de("supply_semester", filas)
    con_tabla_sin_revisar.write_parquet(publicado / "supply_semester.parquet")
    manifest = manifiesto(publicado)
    manifest["tables"]["supply_semester"] = {"rows": 2, "coverage": "Ejemplo: con una llave repetida."}
    escribir_manifiesto(publicado, manifest)
    antes = sha_de_todo(publicado)
    cambiar_catalogo(monkeypatch, con_nota(primera_fuente_del_catalogo(), "Ejemplo: nota nueva."), VERSION_NUEVA)

    with pytest.raises(build.ValidationError, match="supply_semester"):
        build.publish_one("catalogo", published=publicado)

    assert sha_de_todo(publicado) == antes


def test_una_fuente_por_senal_que_no_existe_falla_sin_escribir(publicado, monkeypatch, tmp_path):
    """`check_signal_sources` corre sobre las fuentes del conjunto publicado (HU-122, R8)."""
    config = yaml.safe_load(build.SIGNAL_SOURCES_FILE.read_text(encoding="utf-8"))
    config["regions"][REGION["region"]["id"]]["market"] = {"used": "fuente_inventada"}
    archivo = tmp_path / "sources-mal.yaml"
    archivo.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(build, "SIGNAL_SOURCES_FILE", archivo)
    antes = sha_de_todo(publicado)
    cambiar_catalogo(monkeypatch, con_nota(primera_fuente_del_catalogo(), "Ejemplo: nota nueva."), VERSION_NUEVA)

    with pytest.raises(build.ValidationError, match="fuente_inventada"):
        build.publish_one("catalogo", published=publicado)

    assert sha_de_todo(publicado) == antes


# 10. Qué filas de `sources` se conservan (R8)


def publicar_con_otra_nota(publicado, monkeypatch):
    cambiar_catalogo(monkeypatch, con_nota(primera_fuente_del_catalogo(), "Ejemplo: nota nueva."), VERSION_NUEVA)
    build.publish_one("catalogo", published=publicado)
    return fuentes_por_id(publicado)


def test_la_fila_de_un_adaptador_que_nadie_cita_se_conserva_y_una_huerfana_se_borra(publicado, monkeypatch):
    con_fuentes(publicado, "eva", "ejemplo_huerfana")  # `eva` es un adaptador; ninguna tabla cita ninguna de las dos
    antes = fuentes_por_id(publicado)

    despues = publicar_con_otra_nota(publicado, monkeypatch)

    assert despues["eva"] == antes["eva"]
    assert "ejemplo_huerfana" not in despues


def test_la_fila_del_gradiente_termico_de_region_yaml_se_conserva(publicado, monkeypatch):
    fuente = REGION["temperature_lapse_rate"]["source"]["source_id"]
    if fuente not in fuentes_por_id(publicado):
        con_fuentes(publicado, fuente)
    antes = fuentes_por_id(publicado)[fuente]
    assert fuente not in {s["source_id"] for s in crops_catalog.load()["sources"]}

    despues = publicar_con_otra_nota(publicado, monkeypatch)

    assert despues[fuente] == antes


def test_una_fuente_que_el_catalogo_ya_no_trae_pero_otra_tabla_cita_se_conserva(tmp_path, caches, monkeypatch):  # noqa: F811
    real = crops_catalog.load
    cambiar_catalogo(monkeypatch, fuente_nueva)
    folder = rebuild(tmp_path, caches)
    con_tabla(folder, "supply_semester", tabla_de("supply_semester", [fila_de_oferta("papa", "ejemplo_fuente_nueva")]))
    antes = fuentes_por_id(folder)["ejemplo_fuente_nueva"]

    monkeypatch.setattr(build.crops_catalog, "load", real)  # el catálogo real ya no trae la fuente
    cambiar_catalogo(monkeypatch, con_nota(primera_fuente_del_catalogo(), "Ejemplo: nota nueva."), VERSION_NUEVA)
    build.publish_one("catalogo", published=folder)

    assert fuentes_por_id(folder)["ejemplo_fuente_nueva"] == antes
    build.verify(folder, VERSION_NUEVA)
