"""Datos de muestra de las pantallas, en un solo sitio.

Todas las pantallas cuentan el mismo caso: Rosa, agricultora de Samacá (Boyacá), con cuatro lotes. Lo que una pantalla
muestra tiene que coincidir con lo que muestra otra, así que los valores compartidos viven aquí y los generadores los
importan. Son cifras de muestra, no datos reales: sirven para diseñar, no para decidir.

Reglas que estos datos respetan:
- La señal de heladas del diagnóstico sale del mismo cálculo que el calendario (specs/01-reglas.md): usa el mejor mes
  de siembra del semestre y las etapas sensibles del cultivo, con la serie mensual FROST.
- Las razones de lluvia y oferta dicen siempre el periodo que se evaluó: es historia, no pronóstico (decisión 4).
- La luz que el agricultor «vio al sembrar» en el historial es la del diagnóstico de ese cultivo y semestre.
"""

# ---------- Usuario y cuenta ----------
NAME, USERNAME = "Rosa", "rosa.samaca"
TOWN, TOWN_SHORT = "Samacá, Boyacá", "Samacá"
TODAY_TEXT = "11 de octubre de 2026"
ACCOUNT_SINCE = "20 de enero de 2025"
CONSENT_VERSION = 2
N_LOTS = 4          # El Alto, La Vega, El Bajo y Potrero (finca.py)
N_SEASONS = 13      # 11 de El Alto (historial.py) + maíz de La Vega + arveja de El Bajo

# ---------- Versiones (R4) ----------
DATASET, RULES = "2026.11.0", "1.0.0"
VERSIONS = f"Datos {DATASET} · Reglas {RULES}"

# ---------- Heladas: % de años con al menos una helada en el mes (mínima menor que 2 °C), de enero a diciembre ----------
FROST = (22, 16, 5, 1, 0, 1, 3, 4, 2, 1, 2, 12)
FROST_MODERATE, FROST_UNFAVORABLE = 5, 15   # umbrales de muestra de thresholds.yaml
MONTH_NAMES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def frost_level(pct):
    return "desfavorable" if pct >= FROST_UNFAVORABLE else ("moderado" if pct >= FROST_MODERATE else "favorable")


# ---------- Calendario de la papa en Samacá ----------
# Qué tan bueno es sembrar cada mes. Agosto es el mejor mes del semestre B: sembrando en agosto, la papa se cosecha
# en diciembre y no llega a enero, el mes con más heladas. Marzo y abril son los mejores del semestre A.
FAV, MOD, UNF = "favorable", "moderado", "desfavorable"
SOWING = (UNF, MOD, FAV, FAV, MOD, UNF, MOD, FAV, MOD, MOD, UNF, UNF)
BEST_SOWING = (2, 3, 7)                     # marzo, abril y agosto
BEST_SOWING_TEXT = "Marzo, abril y agosto"

# La papa de El Alto: sembrada el 2 de agosto de 2026; todas sus etapas en campo son sensibles a la helada.
PAPA_SOWING, PAPA_HARVEST = "2 de agosto", "28 de diciembre"
PAPA_CYCLE_MONTHS = (7, 11)                 # de agosto a diciembre
PAPA_FROST_WORST = max(range(PAPA_CYCLE_MONTHS[0], PAPA_CYCLE_MONTHS[1] + 1), key=lambda m: FROST[m])  # diciembre

# ---------- Suelo (SoilGrids, 250 m). El carbono orgánico va en g/kg, como en el contrato (`soc_g_kg`) ----------
SOIL_TOWN = dict(ph="5,2 a 5,8", soc="32 g/kg", soc_class="medio", texture="Franco arcillosa")
SOIL_ALTO = dict(ph="5,4", ph_range="5,0 a 5,9", soc="31 g/kg", soc_class="medio", texture="Franco arcillosa")

# ---------- Diagnósticos de muestra (consulta.py). La luz es la que queda guardada al sembrar (historial.py) ----------
# Papa, semestre B de 2026, Samacá: oferta desfavorable (no crítica) -> amarillo.
RAIN_B = "En 7 de los últimos 10 semestres B la lluvia fue favorable para la papa."
SUPPLY_B = "En 2025 B (último dato) se sembró 35 % más papa que en los tres semestres B anteriores."
FROST_B = f"Sembrando en agosto, heló en el llenado (diciembre) {FROST[11]} de cada 100 años."
LIGHT_AT_SOWING = {("papa", "2026 B"): "amarillo", ("haba", "2026 B"): "no-evaluable"}


# ---------- Consulta de muestra: una ventana de siembra (specs/01-reglas.md, «La ventana de siembra») ----------
# Papa en Samacá, sembrando el 2 de agosto de 2027 (dentro de los próximos doce meses desde el 11 de octubre de 2026),
# sin riego. El clima es el de esa época del año, así que coincide con la papa de El Alto sembrada en agosto de 2026.
QUERY = dict(crop="Papa", town=TOWN, sowing="2 ago 2027", harvest="27 dic 2027", sowing_long="2 de agosto de 2027",
             harvest_long="27 de diciembre de 2027", irrigated=False)
QUERY_KICKER = "PAPA · SIEMBRA 2 AGO 2027 → COSECHA ESTIMADA 27 DIC · SAMACÁ"

SIGNAL_ORDER = ("water", "frost", "heat", "soil", "supply", "market")
SIGNAL_NAME = {"water": "Agua", "frost": "Heladas", "heat": "Calor", "soil": "Suelo", "supply": "Oferta", "market": "Mercado"}
SIGNAL_HINT = {"water": "Que la lluvia alcance", "frost": "Que no hiele en lo sensible", "heat": "Que no haga más calor del que aguanta",
               "soil": "Que el pH le sirva", "supply": "Que no haya demasiado sembrado", "market": "Que el precio suela estar bien"}
CLIMATE = ("water", "frost", "heat")  # sus riesgos graves cuentan siempre, aunque el peso sea 0

# Pesos de muestra (los reales los define HU-198 en weights.yaml, con su porqué).
DEFAULT_WEIGHTS = dict(water=3, frost=3, heat=3, soil=2, supply=3, market=2)
FARMER_WEIGHTS = dict(water=5, frost=3, heat=3, soil=3, supply=0, market=3)  # «la oferta no me importa»

# Calificación de 0 a 100 de cada señal en esa ventana. Nivel: 70-100 favorable, 40-69 moderado, 0-39 desfavorable.
SIGNALS_CASE = {
    "water": dict(score=86, critical=False, reasons=["En 7 de los últimos 10 años la", "lluvia de ago a dic cubrió lo", "que necesita la papa."], note="Sin riego"),
    "frost": dict(score=58, critical=False, reasons=["Heló en el llenado (dic)", f"{FROST[11]} de cada 100 años."], note=None),
    "heat": dict(score=94, critical=False, reasons=["La máxima rara vez pasa de", "22 °C; la papa aguanta", "hasta 28 °C."], note=None),
    "soil": dict(score=80, critical=False, reasons=["pH estimado 5,2 a 5,8: en", "el rango de la papa.", "Estimación de 250 m."], note=None),
    "supply": dict(score=30, critical=False, reasons=["En 2025 B (último dato,", "preliminar) se sembró 35 %", "más papa que antes."], note=None),
    "market": dict(score=None, critical=False, reasons=["Sin datos de precios", "para Samacá."], note=None),
}
SUITABILITY = dict(score=92, reason="La altitud de Samacá (2.660 m) está dentro del rango de la papa (2.000 a 3.500 m).", source="Ficha del cultivo · FAO EcoCrop (por confirmar)")

# Cultivos que en esa ventana salen bien en clima y tienen mejor oferta (`alternatives`).
ALTERNATIVES = (
    dict(crop="Arveja", limiting="Heladas", limiting_score=72, reasons=["Sale bien en clima en esta fecha.", "En 2025 B se sembró menos arveja que antes."]),
    dict(crop="Zanahoria", limiting="Agua", limiting_score=70, reasons=["Sale bien en clima en esta fecha.", "Área sembrada parecida a años anteriores."]),
)


def level_of(score):
    if score is None:
        return "insuficiente"
    return "favorable" if score >= 70 else ("moderado" if score >= 40 else "desfavorable")


def light_for(weights):
    """Semáforo de la ventana con unos pesos (specs/01-reglas.md, «Agregación del semáforo»). Devuelve luz, acción y factor limitante."""
    counts = {k: weights[k] > 0 or (k in CLIMATE and SIGNALS_CASE[k]["critical"]) for k in SIGNAL_ORDER}
    lvl = {}
    for k in SIGNAL_ORDER:
        lv = level_of(SIGNALS_CASE[k]["score"])
        if lv == "moderado" and weights[k] >= 4:
            lv = "desfavorable"
        lvl[k] = lv
    unf = [k for k in SIGNAL_ORDER if counts[k] and lvl[k] == "desfavorable"]
    crit = [k for k in unf if SIGNALS_CASE[k]["critical"]]
    if crit or len(unf) >= 2:
        light = "rojo"
    elif not unf and (lvl["water"] == "favorable" or not counts["water"]):
        light = "verde"
    else:
        light = "amarillo"
    if light == "verde":
        action = "sow"
    elif any(k in ("soil", "supply", "market") for k in unf):
        action = "rotate"
    else:
        action = "other_window"
    scored = [(SIGNALS_CASE[k]["score"], k) for k in SIGNAL_ORDER if counts[k] and SIGNALS_CASE[k]["score"] is not None]
    limiting = min(scored)[1]
    return dict(light=light, action=action, limiting=limiting, counts=counts)
