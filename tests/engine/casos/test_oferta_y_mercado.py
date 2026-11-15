"""Casos de referencia de la oferta y el mercado en el diagnóstico y las estrategias (HU-121; decisión 17, HU-072, HU-073 y
HU-241). Casos de EJEMPLO (R5): los años por encima del promedio de su año (`market_month`), el área sembrada (`supply_semester`) y
el clima salen de tablas de ejemplo armadas con `publicar_ejemplo`; el catálogo de cultivos y las reglas de rotación son los reales.

Qué dicen la spec y la decisión 17: `supply` y `market` con dato son `available` sin calificar, así que nunca cambian la luz, la
acción ni el factor limitante, ni excluyen una estrategia (R2, R3). El ingreso de una estrategia (HU-241) es el promedio, ciclo por
ciclo, de 100 x `years_above` / `years` del mes de la cosecha; un abono verde o un descanso vale 0 siempre; un cultivo sin historia
no cuenta y se dice; si ninguno tiene, `income` es nulo y no entra al total. Es historia, no un pronóstico de ingreso.
"""

import pytest

from backend.engine.rotations.ranking import NO_CRITERION
from common.region import region_today
from tests.engine.casos.conftest import EJEMPLO_FRIO, diagnostico, rotacion

# Heladas de ejemplo por mes (años de 30, como en `test_diagnostico.py`): críticas de junio a agosto, moderadas en abril, mayo y
# septiembre y ninguna en el resto. Sembrar la papa en julio da `red` con `other_window`; en noviembre, `green` con `sow`.
HELADAS = {4: 9, 5: 9, 6: 24, 7: 24, 8: 24, 9: 9}
BASE = {"imerg_en": (EJEMPLO_FRIO,), "lluvia_mm": 200.0, "helada_anios": HELADAS, "ph": 5.5, "reglas": True}
# Con historia de precio: los cultivos con producto en SIPSA. La haba y el maíz no tienen (como en el dataset publicado).
TODOS_ARRIBA = {"papa": 5, "arveja": 5, "zanahoria": 5, "cebolla": 5}
TODOS_ABAJO = {"papa": 0, "arveja": 0, "zanahoria": 0, "cebolla": 0}
# Años de 5 por encima del promedio de su año, igual en todos los meses (así el esperado no depende del mes de la cosecha).
PRECIOS = {"papa": 2, "arveja": 5, "zanahoria": 4, "cebolla": 1}
CONOCIDOS = {"rule", "not_suitable", "soil_ph", "high_risk"}
LUCES = ("light", "light_default", "limiting_signal", "high_risk")


@pytest.fixture
def datasets(armar_ejemplos):
    """`sin` (ni precios ni oferta), `buena` (todo por encima, área +90 %) y `mala` (todo por debajo, área -90 %)."""
    return armar_ejemplos(
        sin=BASE,
        buena={**BASE, "precios": TODOS_ARRIBA, "oferta_cambio_pct": 90.0},
        mala={**BASE, "precios": TODOS_ABAJO, "oferta_cambio_pct": -90.0},
    )


def fecha_de_siembra(mes: int) -> str:
    hoy = region_today()
    return hoy.isoformat() if mes == hoy.month else f"{hoy.year + (mes < hoy.month)}-{mes:02d}-03"


def luces(cuerpo: dict) -> dict:
    """Lo que no puede cambiar con la oferta ni el mercado: las dos luces, su acción y factor limitante, y las señales de clima y suelo."""
    return {
        **{
            clave: {k: cuerpo[clave][k] for k in ("light", "action", "limiting_signal", "high_risk")}
            for clave in ("overall", "overall_default")
        },
        **{
            n: {k: cuerpo["signals"][n][k] for k in ("status", "level", "score", "critical", "counts")}
            for n in ("water", "frost", "heat", "soil")
        },
    }


@pytest.mark.parametrize("mes, luz, accion", [(7, "red", "other_window"), (10, "green", "sow")])
@pytest.mark.parametrize(
    "pesos",
    [None, {"water": 3, "frost": 3, "heat": 3, "soil": 3, "supply": 5, "market": 5}],
    ids=["pesos_de_agrosense", "supply_y_market_en_5"],
)
def test_ejemplo_la_oferta_y_el_mercado_no_cambian_la_luz_la_accion_ni_el_factor_limitante(datasets, mes, luz, accion, pesos):
    # Papa en Samacá. Julio: helada crítica (24 de 30 años) -> `red`; octubre (la cosecha termina en marzo): sin heladas y con
    # lluvia de sobra -> `green`.
    # Lo esperado se escribe a mano: las dos luces dan lo mismo con ningún dato, con todo bueno y con todo malo, también con
    # peso 5 en `supply` y `market` (el peso 5 solo ordena ventanas, nunca cambia la luz).
    extra = {} if pesos is None else {"priorities": pesos}
    cuerpos = {n: diagnostico(datasets(n), sowing_date=fecha_de_siembra(mes), **extra) for n in ("sin", "buena", "mala")}
    base = luces(cuerpos["sin"])
    assert (base["overall"]["light"], base["overall"]["action"]) == (luz, accion)
    assert (base["overall_default"]["light"], base["overall_default"]["action"]) == (luz, accion)
    for nombre in ("buena", "mala"):
        assert luces(cuerpos[nombre]) == base, nombre
        for senal in ("supply", "market"):  # con dato se muestran, pero sin nivel ni calificación (decisión 17)
            dato = cuerpos[nombre]["signals"][senal]
            esperado = ("available", None, None, False)
            assert (dato["status"], dato["level"], dato["score"], dato["critical"]) == esperado, (nombre, senal)
    assert cuerpos["sin"]["signals"]["market"]["status"] == cuerpos["sin"]["signals"]["supply"]["status"] == "insufficient_data"
    if pesos is None:  # con los mismos pesos, las mejores ventanas también son las mismas (R4)
        mejores = {
            n: [(v["sowing_start"], v["limiting_signal"], v["limiting_score"], v["high_risk"]) for v in c.get("best_windows") or []]
            for n, c in cuerpos.items()
        }
        assert mejores["buena"] == mejores["mala"] == mejores["sin"]


def test_ejemplo_la_oferta_y_el_mercado_no_cambian_la_luz_de_los_ciclos_de_una_estrategia(datasets):
    # El mismo ciclo, con y sin datos: misma `light`, misma `light_default` y mismo factor limitante, y la misma helada crítica.
    # Con `previous_crop_ids` y la rotación actual escrita a mano se evalúa una secuencia concreta (arveja, zanahoria, papa).
    actual = ["arveja", "zanahoria", "papa"]
    ciclos = {
        n: rotacion(datasets(n), cycles=3, current_crop_ids=actual, sowing_date=fecha_de_siembra(5))["current_strategy"]["cycles"]
        for n in ("sin", "buena", "mala")
    }
    assert [c["crop_id"] for c in ciclos["sin"]] == actual
    for nombre in ("buena", "mala"):
        assert [{k: c[k] for k in LUCES} for c in ciclos[nombre]] == [{k: c[k] for k in LUCES} for c in ciclos["sin"]], nombre
    assert any(c["high_risk"] for c in ciclos["sin"])  # hay un ciclo de alto riesgo por la helada: ninguna oferta lo arregla


def test_ejemplo_una_oferta_o_un_mercado_muy_desfavorables_no_excluyen_una_estrategia(datasets):
    # `mala`: todos los cultivos con el mes de cosecha por debajo del promedio de su año en los 5 años y el área sembrada -90 %.
    # Las exclusiones (por regla, de la helada) son las mismas que sin datos, ninguna es por `supply` ni `market`, y con el ingreso
    # en 0 de prioridad el ranking es el mismo, con los mismos `rank`.
    sin_ingreso = {"water": 3, "soil": 3, "income": 0, "risk": 3}
    sin, mala = (rotacion(datasets(n), cycles=2, priorities=sin_ingreso) for n in ("sin", "mala"))
    assert sin["excluded"], "sin exclusiones el caso no prueba nada"
    assert mala["excluded"] == sin["excluded"] and mala["excluded_counts"] == sin["excluded_counts"]
    assert set(mala["excluded_counts"]) == CONOCIDOS
    assert all(e["kind"] in CONOCIDOS and e.get("signal") not in ("supply", "market") for e in mala["excluded"])
    assert [(s["crop_ids"], s["rank"]) for s in mala["strategies"]] == [(s["crop_ids"], s["rank"]) for s in sin["strategies"]]
    # Hay estrategias de cultivos con el peor mercado posible (ingreso 0) y siguen en el ranking, con su `rank`.
    cero = [s for s in mala["strategies"] if s["scores"]["income"] == 0 and set(s["crop_ids"]) & set(TODOS_ABAJO)]
    assert cero and all(s["rank"] is not None for s in cero)
    # Con el ingreso en 3 (el criterio ya cuenta) tampoco cambian las exclusiones: el ingreso baja el total, nunca excluye.
    con_ingreso = rotacion(datasets("mala"), cycles=2)
    assert con_ingreso["excluded"] == sin["excluded"]
    assert all(s["rank"] is not None for s in con_ingreso["strategies"])


# ---------- El ingreso con la historia del precio (HU-241) ----------
# Esperados a mano. income = promedio por ciclo de 100 x years_above / years (years = 5), con abono verde y descanso en 0, y los
# cultivos sin historia (haba, maíz) fuera del promedio. Se redondea a entero (mitades hacia arriba). PRECIOS: arveja 5/5 = 100,
# zanahoria 4/5 = 80, papa 2/5 = 40.


@pytest.mark.parametrize(
    "actual, esperado, cuenta",
    [
        # (100 + 0 + 80) / 3 = 60: el abono verde cuenta como 0.
        (["arveja", "avena_vicia", "zanahoria"], 60, "100 + 0 + 80"),
        # (40 + 0 + 100) / 3 = 46,67 -> 47.
        (["papa", "avena_vicia", "arveja"], 47, "40 + 0 + 100"),
        # Arveja, zanahoria, arveja: (100 + 80 + 100) / 3 = 93,33 -> 93: sin abono verde el ingreso es alto.
        (["arveja", "zanahoria"], 93, "100 + 80 + 100"),
        # Descanso, abono verde, descanso: ningún cultivo, todo vale 0 aunque no haya historia (HU-241, decidido el 15 nov 2026).
        (["descanso", "avena_vicia"], 0, "0 + 0 + 0"),
    ],
)
def test_ejemplo_el_ingreso_sale_de_los_anos_con_mejor_precio_del_mes_de_la_cosecha(armar_ejemplos, actual, esperado, cuenta):
    # HU-241: «`income` es el promedio, ciclo por ciclo, de 100 x `years_above` / `years` del mes de la cosecha estimada de cada
    # ciclo ... Un abono verde o un descanso vale 0». Aquí: `cuenta` / 3.
    api = armar_ejemplos(a={**BASE, "precios": PRECIOS})("a")
    # Se evalúa como rotación actual (se arma y se evalúa igual que las sugeridas, con `rank` nulo): así la secuencia es la pedida
    # y no depende de cuáles caben entre las 10 primeras.
    estrategia = rotacion(api, cycles=3, current_crop_ids=actual, sowing_date=fecha_de_siembra(11))["current_strategy"]
    assert len(estrategia["crop_ids"]) == 3
    assert estrategia["scores"]["income"] == esperado, cuenta
    assert NO_CRITERION["income"] not in estrategia["limitations"]
    # El ingreso es historia de precios: no un pronóstico de lo que se va a ganar.
    assert estrategia["scores"]["income"] == round(sum(map(float, cuenta.split(" + "))) / 3 + 1e-9)


def test_ejemplo_un_cultivo_sin_historia_no_cuenta_en_el_ingreso_y_se_dice(armar_ejemplos):
    # Arveja (100), maíz (sin producto en SIPSA: no cuenta) y descanso (0): (100 + 0) / 2 = 50, no / 3.
    api = armar_ejemplos(a={**BASE, "precios": PRECIOS})("a")
    actual = ["arveja", "maiz", "descanso"]
    estrategia = rotacion(api, cycles=3, current_crop_ids=actual, sowing_date=fecha_de_siembra(11))["current_strategy"]
    assert estrategia["crop_ids"] == ["arveja", "maiz", "descanso"]
    assert estrategia["scores"]["income"] == 50
    assert any(t.startswith("El ciclo 2 no tiene historia del precio") for t in estrategia["limitations"]), estrategia["limitations"]


def test_ejemplo_sin_historia_de_precio_el_ingreso_no_califica_no_entra_al_total_y_se_dice(armar_ejemplos):
    # Haba y maíz no tienen historia: `income` nulo y limitación (HU-241, R1). Con la oferta publicada y buena tampoco: la oferta no
    # entra al ingreso mientras no califique. El total sale de agua, suelo y riesgo, así que no cambia con el peso del ingreso.
    usar = armar_ejemplos(sin={**BASE}, oferta={**BASE, "oferta_cambio_pct": 90.0}, precios={**BASE, "precios": PRECIOS})
    cuerpos = {}
    for nombre in ("sin", "oferta"):
        for peso in (0, 5):
            prioridades = {"water": 3, "soil": 3, "income": peso, "risk": 3}
            cuerpos[nombre, peso] = rotacion(
                usar(nombre), cycles=3, current_crop_ids=["haba", "maiz"], priorities=prioridades, sowing_date=fecha_de_siembra(11)
            )["current_strategy"]
    for clave, estrategia in cuerpos.items():
        assert estrategia["crop_ids"] == ["haba", "maiz", "haba"], clave
        assert estrategia["scores"]["income"] is None, clave
        assert NO_CRITERION["income"] in estrategia["limitations"], clave
        otros = [estrategia["scores"][k] for k in ("water", "soil", "risk")]
        assert None not in otros
        assert estrategia["total_score"] == pytest.approx(sum(otros) / 3, abs=1), clave  # pesos iguales: el promedio de los tres
    assert len({e["total_score"] for e in cuerpos.values()}) == 1  # el peso del ingreso no mueve un total en el que no entra
    # Con la oferta publicada, los ciclos traen `supply` disponible y sin calificar; no hay nada que lo vuelva ingreso.
    ciclo = cuerpos["oferta", 5]["cycles"][0]["diagnosis"]["signals"]["supply"]
    assert (ciclo["status"], ciclo["score"]) == ("available", None)
