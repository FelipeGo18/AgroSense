"""Datos de muestra de las pantallas, en un solo sitio.

Todas las pantallas cuentan el mismo caso: Rosa, agricultora de Samacá (Boyacá), con cuatro lotes. Lo que una pantalla
muestra tiene que coincidir con lo que muestra otra, así que los valores compartidos viven aquí y los generadores los
importan. Son cifras de muestra, no datos reales: sirven para diseñar, no para decidir.

Reglas que estos datos respetan:
- La señal de heladas del diagnóstico sale del mismo cálculo que el calendario (specs/01-reglas.md): usa la ventana
  de siembra consultada y las etapas sensibles del cultivo, con la serie mensual FROST.
- Las razones de agua y oferta dicen siempre el periodo que se evaluó: es historia, no pronóstico (decisión 4).
- La luz que el agricultor «vio al sembrar» en el historial es la del diagnóstico de ese cultivo en su fecha de siembra.
- «Hoy» es el 11 de octubre de 2026: las doce ventanas van de noviembre de 2026 a octubre de 2027.
"""

# ---------- Usuario y cuenta ----------
NAME, USERNAME = "Rosa", "rosa.samaca"
TOWN = "Samacá, Boyacá"
ACCOUNT_SINCE = "20 de enero de 2025"
CONSENT_VERSION = 3
CONSENT_ACCEPTED = "11 de octubre de 2026"  # la versión 3 se acepta al publicarse (el «hoy» de la muestra); la cuenta es anterior
N_LOTS = 4          # El Alto, La Vega, El Bajo y Potrero (finca.py)
N_SEASONS = 14      # 12 de El Alto (historial.py) + maíz de La Vega + arveja de El Bajo

# ---------- Versiones (R4) ----------
DATASET, RULES = "2026.11.0", "1.0.0"
VERSIONS = f"Datos {DATASET} · Reglas {RULES}"

# ---------- Heladas: % de años con al menos una helada en el mes (mínima menor que 2 °C), de enero a diciembre ----------
FROST = (22, 16, 5, 1, 0, 1, 3, 4, 2, 1, 2, 12)
FROST_MODERATE, FROST_UNFAVORABLE = 5, 15   # umbrales de muestra de thresholds.yaml


def frost_level(pct):
    return "desfavorable" if pct >= FROST_UNFAVORABLE else ("moderado" if pct >= FROST_MODERATE else "favorable")


# ---------- La papa de El Alto ----------
# Sembrada el 2 de agosto de 2026, con cosecha estimada el 28 de diciembre (unos 147 días). Todas sus etapas en campo
# son sensibles a la helada. Sembrando en agosto se cosecha en diciembre y no llega a enero, el mes con más heladas.
PAPA_CYCLE_MONTHS = (7, 11)                 # de agosto a diciembre

# ---------- Suelo (SoilGrids, 250 m). El carbono orgánico va en g/kg, como en el contrato (`soc_g_kg`) ----------
SOIL_ALTO = dict(ph="5,4", ph_range="5,0 a 5,9", soc="31 g/kg", soc_class="medio", texture="Franco arcillosa")

# ---------- La luz que quedó guardada al sembrar (historial.py), por cultivo y fecha de siembra ----------
# Papa del 2 de agosto de 2026 en El Alto: oferta desfavorable (no crítica) -> amarillo con el criterio de AgroSense y
# verde con las prioridades de Rosa (oferta en 0). Haba del 1 de septiembre: EVA no la registra -> no evaluable.
LIGHT_AT_SOWING = {("papa", "2026-08-02"): "amarillo", ("haba", "2026-09-01"): "no-evaluable"}
LIGHT_AT_SOWING_FARMER = {("papa", "2026-08-02"): "verde"}


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


def level_of(score, status=None):
    if status == "no-aplica":
        return "no-aplica"
    if score is None:
        return "insuficiente"
    return "favorable" if score >= 70 else ("moderado" if score >= 40 else "desfavorable")


def light_for(weights, signals=None):
    """Semáforo de una ventana con unos pesos (specs/01-reglas.md, «Agregación del semáforo»).
    Devuelve luz, acción, factor limitante y qué señales cuentan."""
    signals = signals or SIGNALS_CASE
    counts = {k: weights[k] > 0 or (k in CLIMATE and signals[k].get("critical")) for k in SIGNAL_ORDER}
    lvl = {}
    for k in SIGNAL_ORDER:
        lv = level_of(signals[k]["score"], signals[k].get("status"))
        if lv == "moderado" and weights[k] >= 4:
            lv = "desfavorable"
        lvl[k] = lv
    scored = [(signals[k]["score"], k) for k in SIGNAL_ORDER if counts[k] and signals[k]["score"] is not None]
    limiting = min(scored)[1] if scored else None
    if any(counts[k] and lvl[k] == "insuficiente" for k in ("water", "supply")):
        return dict(light="no-evaluable", action="review_data", limiting=None, counts=counts)  # sin luz no hay factor que limite
    unf = [k for k in SIGNAL_ORDER if counts[k] and lvl[k] == "desfavorable"]
    crit = [k for k in unf if signals[k].get("critical")]
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
    return dict(light=light, action=action, limiting=limiting, counts=counts)


# ---------- Otros casos del resultado (tanda 2 del rediseño) ----------

def _sig(score, reasons, critical=False, status=None, note=None):
    return dict(score=score, reasons=reasons, critical=critical, status=status, note=note)


CASES = {
    "amarillo": dict(crop="Papa", town="Samacá", kicker=QUERY_KICKER, signals=SIGNALS_CASE, suitability=SUITABILITY),
    # Toca está más alto y frío que Samacá: sembrando en marzo, la floración cae en las heladas de junio y julio.
    "rojo": dict(
        crop="Papa", town="Toca", kicker="PAPA · SIEMBRA 1 MAR 2027 → COSECHA ESTIMADA ~26 JUL · TOCA",
        suitability=dict(score=88, reason="La altitud de Toca (2.780 m) está dentro del rango de la papa (2.000 a 3.500 m).", source=SUITABILITY["source"]),
        signals=dict(
            water=_sig(80, ["En 8 de los últimos 10 años la", "lluvia de mar a jul cubrió lo", "que necesita la papa."], note="Sin riego"),
            frost=_sig(18, ["Heló en la floración (jun)", "4 de cada 10 años."], critical=True),
            heat=_sig(96, ["La máxima rara vez pasa de", "19 °C; la papa aguanta", "hasta 28 °C."]),
            soil=_sig(78, ["pH estimado 5,3 a 5,9: en", "el rango de la papa.", "Estimación de 250 m."]),
            supply=_sig(74, ["En 2025 A, área sembrada", "parecida a los tres", "semestres A anteriores."]),
            market=_sig(None, ["Sin datos de precios", "para Toca."]),
        ),
        best_windows=(
            dict(sowing="1 sep 2027", harvest="~25 ene 2028", limiting="Agua", limiting_score=66, weighted=79),
            dict(sowing="15 abr 2027", harvest="~10 sep 2027", limiting="Heladas", limiting_score=58, weighted=74),
            dict(sowing="1 oct 2027", harvest="~24 feb 2028", limiting="Heladas", limiting_score=52, weighted=71),
        ),
    ),
    # Maíz en Toca: en todas las fechas de los próximos doce meses la floración cae en un mes con heladas críticas.
    "rojo-sin-fechas": dict(
        crop="Maíz", town="Toca", kicker="MAÍZ · SIEMBRA 1 MAR 2027 → COSECHA ESTIMADA ~15 SEP · TOCA",
        suitability=dict(score=61, reason="La altitud de Toca (2.780 m) está cerca del límite del maíz (hasta 3.000 m).", source=SUITABILITY["source"]),
        signals=dict(
            water=_sig(76, ["En 7 de los últimos 10 años la", "lluvia de mar a sep cubrió lo", "que necesita el maíz."], note="Sin riego"),
            frost=_sig(9, ["Heló en la floración (jul)", "6 de cada 10 años."], critical=True),
            heat=_sig(90, ["La máxima rara vez pasa de", "19 °C; el maíz aguanta", "hasta 32 °C."]),
            soil=_sig(72, ["pH estimado 5,3 a 5,9: en", "el rango del maíz.", "Estimación de 250 m."]),
            supply=_sig(70, ["En 2025 A, área sembrada", "parecida a los tres", "semestres A anteriores."]),
            market=_sig(None, ["Sin datos de precios", "para Toca."]),
        ),
        best_windows=(),
    ),
    # Haba en Samacá: EVA no la registra, así que la oferta no tiene datos y el semáforo no se puede dar.
    "no-evaluable": dict(
        crop="Haba", town="Samacá", kicker="HABA · SIEMBRA 2 AGO 2027 → COSECHA ESTIMADA ~10 ENE 2028 · SAMACÁ",
        suitability=dict(score=90, reason="La altitud de Samacá (2.660 m) está dentro del rango del haba (2.200 a 3.600 m).", source=SUITABILITY["source"]),
        signals=dict(
            water=_sig(82, ["En 7 de los últimos 10 años la", "lluvia de ago a ene cubrió lo", "que necesita el haba."], note="Sin riego"),
            frost=_sig(None, ["La ficha del haba no tiene", "etapas sensibles a la", "helada."], status="no-aplica"),
            heat=_sig(95, ["La máxima rara vez pasa de", "22 °C; el haba aguanta", "hasta 27 °C."]),
            soil=_sig(55, ["pH estimado 5,2 a 5,8: en", "el límite de lo que tolera.", "Estimación de 250 m."]),
            supply=_sig(None, ["EVA no registra haba en", "Samacá en los últimos", "semestres."]),
            market=_sig(None, ["Sin datos de precios", "para Samacá."]),
        ),
    ),
}

# Papa en un municipio cálido: no es apta para la zona y no se evalúa ninguna ventana (HU-191, HU-194).
NOT_SUITABLE = dict(crop="Papa", town="Puerto Boyacá", score=0, kicker="PAPA · PUERTO BOYACÁ, BOYACÁ",
                    reason="Puerto Boyacá está a 125 m; la papa se da entre 2.000 y 3.500 m.",
                    source="Ficha del cultivo · FAO EcoCrop (por confirmar)",
                    alternatives=(
                        dict(crop="Maíz", limiting="Agua", limiting_score=78, reasons=["Se da a esta altitud y sale", "bien en clima en esta fecha."]),
                        dict(crop="Yuca", limiting="Calor", limiting_score=81, reasons=["Aguanta el calor de la zona", "y sale bien en esta fecha."]),
                        dict(crop="Plátano", limiting="Agua", limiting_score=74, reasons=["Se da a esta altitud; pide", "riego en los meses secos."]),
                    ))


# ---------- Series del panel de señales (GET /trends con la ventana; muestra) ----------
# Agua: por año, lluvia de agosto a diciembre frente a lo que la papa habría necesitado en esos meses (mm).
# En 3 de los 10 años la lluvia no alcanzó (2018, 2019 y 2022): es el «7 de 10» de la razón de la señal.
WATER_YEARS = ((2016, 462, 430), (2017, 518, 430), (2018, 371, 430), (2019, 418, 430), (2020, 540, 430),
               (2021, 497, 430), (2022, 356, 430), (2023, 470, 430), (2024, 488, 430), (2025, 452, 430))
# Calor: temperatura máxima que se supera uno de cada diez días (`tmax_p90_c`), de agosto a diciembre, frente a lo que aguanta.
TMAX_P90 = (("Ago", 21.4), ("Sep", 21.9), ("Oct", 21.2), ("Nov", 20.6), ("Dic", 20.9))
HEAT_MAX_PAPA = 28
# Oferta: papa sembrada en Samacá en el semestre B, por año (EVA), y la fuente de contraste (siembras registradas en AgroSense).
AREA_B = ((2019, 790), (2020, 820), (2021, 805), (2022, 840), (2023, 860), (2024, 830), (2025, 1138))
AREA_B_AVG3 = 843
AGROSENSE_SUPPLY = dict(accounts=14, ha=38, date="11 oct 2026")


# ---------- Ventanas de los próximos doce meses: papa en Samacá, sin riego (POST /calendar, «Planear una siembra») ----------
# Hoy es 11 de octubre de 2026: la primera ventana es noviembre de 2026 y la última, octubre de 2027.
# La papa dura unos 147 días: sembrando el día 1 de un mes se cosecha a finales del cuarto mes siguiente (ago -> dic).
# Sembrando de octubre a diciembre, la floración cae en enero y febrero, los meses con más heladas: riesgo grave (alto riesgo).
# Oferta: las siembras de julio a diciembre caen en el semestre B de EVA, con mucha papa sembrada (30); las de enero a junio, en el A (68).
_W = (  # mes, año, cosecha estimada, agua, heladas, calor, suelo, oferta, helada crítica
    ("Nov", 2026, "mar 2027", 55, 9, 96, 80, 30, True),
    ("Dic", 2026, "abr 2027", 40, 16, 96, 80, 30, True),
    ("Ene", 2027, "may 2027", 48, 64, 95, 80, 68, False),
    ("Feb", 2027, "jun 2027", 70, 74, 95, 80, 68, False),
    ("Mar", 2027, "jul 2027", 84, 80, 94, 80, 68, False),
    ("Abr", 2027, "ago 2027", 82, 72, 94, 80, 68, False),
    ("May", 2027, "sep 2027", 66, 70, 94, 80, 68, False),
    ("Jun", 2027, "oct 2027", 58, 60, 94, 80, 68, False),
    ("Jul", 2027, "nov 2027", 74, 52, 94, 80, 30, False),
    ("Ago", 2027, "dic 2027", 86, 58, 94, 80, 30, False),
    ("Sep", 2027, "ene 2028", 78, 34, 94, 80, 30, False),
    ("Oct", 2027, "feb 2028", 62, 12, 95, 80, 30, True),
)
WINDOW_MONTHS = tuple((mon, yr) for mon, yr, *_ in _W)  # los doce meses de siembra que se pueden elegir, en orden


def window_summary(scores, weights=None, critical=()):
    """Factor que más limita, su nota y el promedio ponderado de una ventana con unos pesos. Cuentan las señales con
    peso mayor que 0 y los riesgos graves de clima (`critical`), que cuentan siempre (specs/01-reglas.md)."""
    weights = weights or DEFAULT_WEIGHTS
    counted = {k: v for k, v in scores.items() if v is not None and (weights[k] > 0 or k in critical)}
    lim = min(counted, key=lambda k: counted[k])
    wsum = sum(weights[k] for k in counted)
    weighted = round(sum(counted[k] * weights[k] for k in counted) / wsum) if wsum else None
    return lim, counted[lim], weighted


def windows(weights=None):
    """Las doce ventanas con sus calificaciones, factor limitante, promedio ponderado, alto riesgo y orden (specs/01-reglas.md)."""
    out = []
    for mon, yr, harvest, water, frost, heat, soil, supply, crit in _W:
        scores = dict(water=water, frost=frost, heat=heat, soil=soil, supply=supply, market=None)
        lim, lim_score, weighted = window_summary(scores, weights, ("frost",) if crit else ())
        out.append(dict(month=mon, year=yr, harvest=harvest, scores=scores, limiting=lim, limiting_score=lim_score,
                        weighted=weighted, high_risk=crit))
    chrono = list(out)
    ranked = sorted(out, key=lambda w: (w["high_risk"], -(w["limiting_score"] // 10), -w["weighted"], chrono.index(w)))
    for i, w in enumerate(ranked):
        w["rank"] = i + 1
    return chrono, ranked


# Semanas de agosto de 2027 (al abrir el mes): el dato semanal afina dentro de un mes, pero es más variable.
AUG_WEEKS = (
    dict(label="2 al 8 ago", harvest="~27 dic", scores=dict(water=86, frost=58, heat=94, soil=80, supply=30, market=None)),
    dict(label="9 al 15 ago", harvest="~3 ene", scores=dict(water=84, frost=52, heat=94, soil=80, supply=30, market=None)),
    dict(label="16 al 22 ago", harvest="~10 ene", scores=dict(water=82, frost=46, heat=94, soil=80, supply=30, market=None)),
    dict(label="23 al 29 ago", harvest="~17 ene", scores=dict(water=80, frost=41, heat=94, soil=80, supply=30, market=None)),
    dict(label="30 ago al 5 sep", harvest="~24 ene", scores=dict(water=79, frost=38, heat=94, soil=80, supply=30, market=None)),
)
