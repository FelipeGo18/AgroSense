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
