"""Tanda 11 · Estrategias de rotación (decisión 12): la entrada, las estrategias, las descartadas y el estado vacío.

EP-10 (HU-214, HU-101, HU-102) sobre `specs/01-reglas.md`, «Estrategias de rotación». Una estrategia es una secuencia
de 2 o 3 ciclos sobre un mismo terreno; cada ciclo es un cultivo, un abono verde o un descanso con su ventana.
Reemplaza, para el MVP, a «Qué sembrar después» de dos ciclos (rotaciones.py), que queda como referencia.

- **Entrada (HU-214).** Sin cuenta: municipio, área, qué había antes (de 0 a 3 cultivos), qué viene sembrando (su
  rotación de siempre, de 2 a 3 cultivos, opcional), cuándo sembrar el primer ciclo, riego y número de ciclos. Con
  cuenta se entra desde el lote y esos datos ya vienen de él y de su historial.
- **La rotación actual (HU-223, decisión 14).** Va primero, rotulada «Lo que usted siembra hoy», evaluada igual que
  las demás y sin puesto en el orden. Cada sugerida dice cuánto gana o pierde frente a ella.
- **Estrategias (HU-102).** Cada tarjeta trae sus ciclos en orden con su luz (forma y texto), el desglose por
  criterio (agua, suelo, ingreso y riesgo) y el bloque «Salud del suelo» con sus cinco criterios (con la erosión,
  HU-224), cada uno con su nivel, su razón y su regla con fuente. Un criterio sin datos se ve «Sin datos
  suficientes», nunca como malo (R1).
- **Descartadas, a pedido.** La regla que violan, «No se da en su zona» o «Alto riesgo en el ciclo 2» (R2, R3).
- **Sin estrategias válidas.** Estado vacío con las descartadas a la vista y qué cambiar.

Qué hace cada control: las semillas reordenan al instante (POST /rotations con `priorities`); «Cambiar» vuelve a la
entrada; tocar un ciclo abre su detalle (HU-215, ciclo.py); «Ver suelo» abre el detalle de la señal de suelo;
«Ver por qué» despliega las descartadas; «¿Cómo se arma este orden?» abre «¿Cómo funciona?».

El puntaje total se calcula aquí igual que en el motor: promedio de los criterios ponderado por las prioridades
(0 a 5). El criterio de suelo es el promedio de los criterios de salud del suelo que tienen dato (favorable 100,
moderado 50, desfavorable 0). Los nombres y las cifras son de muestra.

    python design/pantallas/estrategias.py     # escribe svg/estrategias-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402
import muestra  # noqa: E402
import senales as sg  # noqa: E402
from build_kit_svg import STATUS, facets, icon  # noqa: E402
from diagnostico import MONTHS, CHOSEN_MONTH, chip, options  # noqa: E402
from rotaciones import PRIORITIES, bar, priorities_panel, wrap  # noqa: E402
from ui import (BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, field, frame, group, link, mascot,  # noqa: E402
                paragraph, poly, scene, text, topbar, width_of)

TOWN, AREA, SOWING = muestra.TOWN, "1,26", muestra.QUERY["sowing_long"]
NOT_FORECAST = "Compara estrategias según reglas con fuente. No predice cuánto va a mejorar su suelo."
YOUR_CALL = "Es información para decidir. La decisión es suya."
SOIL_USED = "pH 5,2 a 5,8 · carbono orgánico 31 g/kg (medio)"

# ---------- Datos de muestra ----------
# Samacá, después de una papa, sembrando el primer ciclo el 2 de agosto de 2027, sin riego y con tres ciclos.
# Cada ciclo: (cultivo, tipo, siembra, cosecha estimada, luz, qué limita). Tipo: cultivo, abono (abono verde) o descanso.
# Cada ciclo siguiente se siembra el lunes de la semana siguiente a la cosecha del anterior (specs/01-reglas.md).
FAV, MOD, UNF, NOD = "favorable", "moderado", "desfavorable", "insuficiente"
RULE_N = "Regla: leguminosas en la rotación · catálogo de rotación"
RULE_OC = "Regla: materia orgánica según el carbono del suelo · SoilGrids, 250 m"
RULE_COVER = "Sin regla con fuente todavía para este criterio"
RULE_PEST = "Regla: no repetir la familia · catálogo de rotación"
COVER_NODATA = (NOD, "Aún no hay una regla con fuente que diga cuántos meses bastan.", RULE_COVER)
RULE_EROSION = "Regla: suelo descubierto en pendiente · NASADEM, 30 m"
SLOPE = "pendiente de 9 %"  # la del municipio de muestra, de NASADEM (HU-206)

STRATEGIES = (
    dict(cycles=(("Arveja", "cultivo", "2 ago 2027", "~29 nov 2027", "verde", None),
                 ("Avena con vicia", "abono", "6 dic 2027", "~5 mar 2028", "amarillo", "heladas"),
                 ("Papa", "cultivo", "13 mar 2028", "~7 ago 2028", "verde", None)),
         scores=dict(water=74, income=55, risk=58),
         health=dict(nitrogen=(FAV, "La arveja y la vicia son leguminosas: fijan nitrógeno.", RULE_N),
                     organic_carbon=(FAV, "La avena con vicia se incorpora como abono verde.", RULE_OC),
                     soil_cover=COVER_NODATA,
                     pest_break=(FAV, "La papa vuelve después de dos ciclos de otras familias.", RULE_PEST),
                     erosion=(FAV, f"Con {SLOPE}, el suelo queda cubierto casi todo el plan.", RULE_EROSION)),
         reasons=["Papa, avena y arveja: la rotación evaluada por Agrosavia en Tibaitatá.", "El abono verde no deja cosecha en su ciclo."]),
    dict(cycles=(("Descanso", "descanso", "2 ago 2027", "hasta el 28 nov 2027", None, None),
                 ("Arveja", "cultivo", "29 nov 2027", "~27 mar 2028", "amarillo", "heladas"),
                 ("Papa", "cultivo", "3 abr 2028", "~28 ago 2028", "verde", None)),
         scores=dict(water=80, income=25, risk=64),
         health=dict(nitrogen=(FAV, "La arveja es leguminosa: fija nitrógeno.", RULE_N),
                     organic_carbon=(FAV, "El descanso deja rastrojo sobre el suelo.", RULE_OC),
                     soil_cover=COVER_NODATA,
                     pest_break=(FAV, "El descanso y la arveja cortan el ciclo de plagas de la papa.", RULE_PEST),
                     erosion=(MOD, f"El descanso deja el suelo descubierto 4 meses, con {SLOPE}.", RULE_EROSION)),
         reasons=["El terreno descansa el primer ciclo y corta las plagas de la papa.", "No deja ingreso hasta la cosecha de la arveja."]),
    dict(cycles=(("Avena con vicia", "abono", "2 ago 2027", "~31 oct 2027", "verde", None),
                 ("Papa", "cultivo", "8 nov 2027", "~3 abr 2028", "amarillo", "agua"),
                 ("Arveja", "cultivo", "10 abr 2028", "~7 ago 2028", "verde", None)),
         scores=dict(water=70, income=60, risk=55),
         health=dict(nitrogen=(FAV, "La vicia y la arveja son leguminosas: fijan nitrógeno.", RULE_N),
                     organic_carbon=(FAV, "La avena con vicia se incorpora como abono verde.", RULE_OC),
                     soil_cover=COVER_NODATA,
                     pest_break=(MOD, "La papa vuelve después de un solo ciclo de otra familia.", RULE_PEST),
                     erosion=(FAV, f"Con {SLOPE}, el abono verde cubre el suelo en los meses de lluvia.", RULE_EROSION)),
         reasons=["El abono verde prepara el suelo para la papa.", "La papa de noviembre arranca en meses de poca lluvia."]),
    dict(cycles=(("Zanahoria", "cultivo", "2 ago 2027", "~29 nov 2027", "verde", None),
                 ("Arveja", "cultivo", "6 dic 2027", "~3 abr 2028", "amarillo", "heladas"),
                 ("Maíz", "cultivo", "10 abr 2028", "~23 oct 2028", "amarillo", "agua")),
         scores=dict(water=62, income=72, risk=52),
         health=dict(nitrogen=(FAV, "La arveja es leguminosa: fija nitrógeno.", RULE_N),
                     organic_carbon=(MOD, "Ningún ciclo devuelve materia orgánica; su carbono es medio.", RULE_OC),
                     soil_cover=COVER_NODATA,
                     pest_break=(FAV, "Tres familias distintas, ninguna repite.", RULE_PEST),
                     erosion=(MOD, f"Entre cosechas el suelo queda descubierto 2 meses, con {SLOPE}.", RULE_EROSION)),
         reasons=["Tres cosechas con ingreso en cada ciclo.", "No incluye abono verde ni descanso."]),
)
# La rotación actual (HU-223): lo que viene sembrando, papa y arveja, repetida hasta completar los tres ciclos.
CURRENT = dict(
    cycles=(("Papa", "cultivo", "2 ago 2027", "~27 dic 2027", "amarillo", "heladas"),
            ("Arveja", "cultivo", "3 ene 2028", "~1 may 2028", "verde", None),
            ("Papa", "cultivo", "8 may 2028", "~2 oct 2028", "amarillo", "agua")),
    scores=dict(water=68, income=70, risk=50),
    health=dict(nitrogen=(MOD, "Solo la arveja fija nitrógeno.", RULE_N),
                organic_carbon=(MOD, "Ningún ciclo devuelve materia orgánica; su carbono es medio.", RULE_OC),
                soil_cover=COVER_NODATA,
                pest_break=(UNF, "La papa vuelve después de un solo ciclo: sus plagas se quedan en el terreno.", RULE_PEST),
                erosion=(MOD, f"Entre cosechas el suelo queda descubierto 2 meses, con {SLOPE}.", RULE_EROSION)),
    reasons=["Es lo que usted viene sembrando: las demás se comparan contra ella.", "Deja ingreso en los tres ciclos."])
CURRENT_LABEL = "Papa → Arveja (se repite)"
HEALTH_ORDER = (("nitrogen", "Nitrógeno"), ("organic_carbon", "Carbono orgánico"), ("soil_cover", "Suelo cubierto"), ("pest_break", "Corte de plagas"),
                ("erosion", "Erosión"))
HEALTH_VALUE = {FAV: 100, MOD: 50, UNF: 0}

EXCLUDED = (
    ("Papa → Arveja → Maíz", "Misma familia que el cultivo anterior (solanáceas): repite plagas y enfermedades.", "Regla: no repetir la familia · catálogo de rotación"),
    ("Arveja → Papa → Maíz", "Alto riesgo en el ciclo 2: heladas. Sembrando papa en diciembre, heló en su floración 22 de cada 100 años.", "Riesgo grave de clima (R2) · NASA POWER, 1981–2024"),
    ("Arveja → Yuca → Papa", "No se da en su zona: Samacá está a 2.660 m y la yuca se da hasta 1.800 m.", "Aptitud del cultivo (R3) · ficha del cultivo"),
    ("Cebolla → Arveja → Papa", "La cebolla tolera pH de 6,0 a 7,5 y su suelo estimado es de 5,2 a 5,8: queda fuera en todo el intervalo.", "pH fuera del rango (R3) · SoilGrids, 250 m"),
)
# Para el estado vacío: maíz en Toca, donde en todas las fechas la floración cae en heladas críticas (muestra.CASES).
EXCLUDED_EMPTY = (
    ("Maíz → Arveja → Papa", "Alto riesgo en el ciclo 1: heladas. Sembrando maíz en marzo, heló en su floración 6 de cada 10 años.", "Riesgo grave de clima (R2) · NASA POWER, 1981–2024"),
    ("Arveja → Maíz → Papa", "Alto riesgo en el ciclo 2: heladas. El maíz de agosto florece en los meses con más heladas.", "Riesgo grave de clima (R2) · NASA POWER, 1981–2024"),
    ("Descanso → Maíz → Arveja", "Alto riesgo en el ciclo 2: heladas. El maíz de septiembre florece en enero.", "Riesgo grave de clima (R2) · NASA POWER, 1981–2024"),
)

LIGHT = {"verde": ("favorable", "octagon", "Luz verde"), "amarillo": ("moderado", "triangle", "Luz amarilla"), "rojo": ("desfavorable", "square", "Luz roja")}
KIND_LABEL = {"abono": "Abono verde", "descanso": "Descanso"}


def soil_score(health):
    """El criterio de suelo: promedio de los criterios de salud del suelo que tienen dato (R1: lo que no tiene dato no entra)."""
    values = [HEALTH_VALUE[level] for level, _, _ in health.values() if level in HEALTH_VALUE]
    return round(sum(values) / len(values)) if values else None


def scores_of(s):
    return dict(s["scores"], soil=soil_score(s["health"]))


def total(s):
    scores, weights = scores_of(s), {k: v for k, _, v, _ in PRIORITIES}
    counted = {k: v for k, v in scores.items() if v is not None}
    return round(sum(counted[k] * weights[k] for k in counted) / sum(weights[k] for k in counted))


def ranked():
    return sorted(STRATEGIES, key=lambda s: (-total(s), s["cycles"][0][0]))  # desempate determinista por nombre


def title_of(s):
    return " → ".join(c[0] for c in s["cycles"])


# ---------- Piezas ----------

def mark(x, y, level, size=16):
    """La forma de un nivel (octágono, triángulo o cuadro) con su color; sin datos, un signo de pregunta punteado."""
    if level == NOD:
        return [poly(chamfer(x, y, size, size, 4), WHITE, D["cielo"], 1.5, "3 3"), text(x + size / 2, y + size - 3, "?", size - 3, 700, D["cielo"], anchor="middle")]
    st = STATUS[level]
    return icon(LIGHT_SHAPE[level], x, y, st["stroke"], size)


LIGHT_SHAPE = {FAV: "octagon", MOD: "triangle", UNF: "square"}
LEVEL_TEXT = {FAV: "Favorable", MOD: "Moderado", UNF: "Desfavorable", NOD: "Sin datos suficientes"}


def light_chip(x, y, light, limiting=None, w=None):
    """La luz de un ciclo con forma y texto, nunca solo color. `limiting`: lo que más limita ese ciclo."""
    level, shape, label = LIGHT[light]
    st = STATUS[level]
    full = label + (f" · limita: {limiting}" if limiting else "")
    w = w or width_of(full, 13, True) + 40
    c = 0 if level == UNF else 7
    body = [poly(chamfer(0, 0, w, 26, c), st["fill"])] + facets(0, 0, w, 26, c, st["fill"]) + [poly(chamfer(0, 0, w, 26, c), "none", st["stroke"], 2)]
    body += icon(shape, 8, 6, st["ink"], 14) + [text(28, 18, full, 13, 700, st["ink"])]
    return [group(f"luz-{light}", body, x, y)]


def cycle_box(x, y, w, n, cycle, compact=False):
    """Un ciclo de la estrategia: número, cultivo, siembra, cosecha estimada con su base y su luz. Tocarlo abre su detalle."""
    crop, kind_, sow, harvest, light, limiting = cycle
    h = 132 if compact else 150
    body = [poly(chamfer(0, 0, w, h, 10), "#F6F8F3" if kind_ != "descanso" else WHITE, BORDE, 1.5, None if kind_ != "descanso" else "5 4")]
    body += [text(14, 24, f"CICLO {n}", 12, 700, SEC)]
    if kind_ in KIND_LABEL and kind_ != "descanso":
        body += [poly(chamfer(w - 104, 10, 92, 20, 5), WHITE, D["oliva"], 1.5), text(w - 58, 24, KIND_LABEL[kind_], 11, 700, D["oliva"], anchor="middle")]
    body.append(text(14, 50, crop, 19 if not compact else 18, 600, font=FONT_TITLE))
    if kind_ == "descanso":
        body += [text(14, 72, f"Desde el {sow}", 13), text(14, 90, harvest, 13), text(14, 116 if not compact else 112, "Sin semáforo: no se siembra", 12, 700, SEC)]
    else:
        last = "Se incorpora" if kind_ == "abono" else "Cosecha"
        body += [text(14, 72, f"Siembra {sow}", 13), text(14, 90, f"{last} {harvest}", 13)]
        if compact:
            body += light_chip(14, 100, light, limiting, w - 28)
        else:  # en la tarjeta angosta de escritorio, lo que más limita va debajo de la luz
            body += light_chip(14, 100, light)
            if limiting:
                body.append(text(14, 141, f"Limita: {limiting}", 12, 700, SEC))
    return [group(f"ciclo-{n}", body, x, y)], h


def health_block(x, y, w, health, compact=False):
    """«Salud del suelo»: cinco criterios con nivel (forma y texto), razón y regla con fuente."""
    out = [text(0, 0, "Salud del suelo", 17, 700), text(w, 0, "Comparación, no predicción", 12, 700, D["cielo"], anchor="end")]
    yy = 14
    limit = 40 if compact else int((w - 190) / 6.6)
    for key, label in HEALTH_ORDER:
        level, reason, rule = health[key]
        rows = wrap(reason, limit)
        rule_rows = wrap(rule, 46) if compact else [rule]
        rh = max(46, 24 + len(rows) * 17 + 18) if not compact else 61 + len(rows) * 17 + len(rule_rows) * 15 + 12
        out.append(f'<rect x="0" y="{yy}" width="{w}" height="1" fill="{BORDE}"/>')
        out += mark(0, yy + 12, level)
        out.append(text(24, yy + 25, label, 14, 700))
        if compact:
            out.append(text(24, yy + 43, LEVEL_TEXT[level], 12, 700, D["cielo"] if level == NOD else P["noche"]))
            out += paragraph(24, yy + 61, rows, 13, 17)
            out += paragraph(24, yy + 61 + len(rows) * 17 + 2, rule_rows, 11, 15, fill=SEC)
        else:
            out.append(text(24, yy + 42, LEVEL_TEXT[level], 12, 700, D["cielo"] if level == NOD else P["noche"]))
            out += paragraph(170, yy + 25, rows, 13, 17)
            out.append(text(170, yy + 25 + len(rows) * 17 + 1, rule, 11, fill=SEC))
        yy += rh
    return [group("salud-del-suelo", out, x, y)], yy


def versus_current(x, y, delta, anchor="end"):
    """Cuánto gana o pierde frente a lo que siembra hoy (`vs_current`), con forma y texto: nunca solo color."""
    up = delta >= 0
    label = f"{'+' if up else '−'}{abs(delta)} frente a lo de hoy"
    tw = width_of(label, 13, True)
    x0 = x - tw - 20 if anchor == "end" else x
    shape = [(x0, y - 2), (x0 + 12, y - 2), (x0 + 6, y - 12)] if up else [(x0, y - 12), (x0 + 12, y - 12), (x0 + 6, y - 2)]
    return [poly(shape, D["oliva"] if up else D["cielo"]), text(x0 + 18, y, label, 13, 700, D["oliva"] if up else D["cielo"])]


def strategy_card(x, y, w, rank, s, mobile=False):
    """Una estrategia. `rank` nulo es la rotación actual (HU-223): sin puesto, rotulada «Lo que usted siembra hoy»."""
    current = rank is None
    scores = scores_of(s)
    body = []
    if current:
        body += [poly(chamfer(14, 18, 44, 32, 6), D["cielo"]), text(36, 39, "HOY", 13, 700, WHITE, anchor="middle")]
    else:
        body += [poly([(34, 14), (54, 34), (34, 54), (14, 34)], P["calabaza"] if rank == 1 else P["niebla"], P["noche"], 2), text(34, 41, f"{rank}", 20, 700, anchor="middle")]
    title = ("Lo que siembra hoy: " if current and not mobile else "") + title_of(s)
    if mobile:
        rows = wrap(title, 22)
        body += paragraph(70, 36, rows, 18, 24, weight=600, font=FONT_TITLE)
        yy = 36 + len(rows) * 24
    else:
        body.append(text(70, 42, title, 24 if len(title) < 34 else 21, 600, font=FONT_TITLE))
        yy = 62
    body += [text(w - 24, 44, f"{total(s)}", 34, 600, P["noche"], FONT_TITLE, anchor="end"), text(w - 24, 64, "de 100", 13, fill=SEC, anchor="end")]
    if current:
        note = "Se evalúa igual que las demás y no entra al orden." if not mobile else "Se evalúa igual, sin puesto."
        body.append(text(70 if not mobile else 24, yy + 8 if not mobile else yy + 4, note, 13, 700, D["cielo"]))
        yy += 18
    elif mobile:  # en el celular va debajo del título, para no chocar con él
        body += versus_current(24, yy + 12, total(s) - total(CURRENT), anchor="start")
        yy += 22
    else:
        body += versus_current(w - 24, 86, total(s) - total(CURRENT))
        yy = max(yy, 92)
    # ciclos
    yy += 18
    if mobile:
        for i, cycle in enumerate(s["cycles"]):
            cb, ch = cycle_box(24, yy, w - 48, i + 1, cycle, compact=True)
            body += cb
            yy += ch + 10
    else:
        gap = 12
        cw = (w - 48 - 2 * gap) / 3
        for i, cycle in enumerate(s["cycles"]):
            cb, ch = cycle_box(24 + i * (cw + gap), yy, cw, i + 1, cycle)
            body += cb
            if i:
                ax = 24 + i * (cw + gap) - gap / 2
                body.append(poly([(ax - 5, yy + ch / 2 - 7), (ax + 5, yy + ch / 2), (ax - 5, yy + ch / 2 + 7)], P["noche"]))
        yy += ch + 6
    body.append(text(24, yy + 16, "Cosecha estimada por calendario, con la duración de la ficha. Toque un ciclo para ver su diagnóstico." if not mobile else
                     "Cosecha estimada por calendario. Toque un ciclo.", 12, fill=SEC))
    yy += 40
    # desglose
    bw = (w - 220) if not mobile else (w - 190)
    for i, (k, label, weight, _) in enumerate(PRIORITIES):
        body += bar(24, yy + i * 26, bw, label, scores[k], weight)
    yy += 4 * 26 + 14
    lines = [ln for r in s["reasons"] for ln in wrap("· " + r, 42 if mobile else 76)]
    body += paragraph(24, yy + 6, lines, 14, 20)
    yy += len(lines) * 20 + 20
    hb, hh = health_block(24, yy, w - 48, s["health"], compact=mobile)
    body += hb
    yy += hh + 14
    first = s["cycles"][0]
    label = f"Ver el ciclo 1: {first[0].lower()}"
    body += button(24, yy, min(w - 48, 330), label, "secondary", h=44)
    h = yy + 70
    edge = D["cielo"] if current else (P["calabaza"] if rank == 1 else None)
    frame_ = [poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE, edge, 3 if edge else 0)]
    return [group("estrategia-actual" if current else f"estrategia-{rank}", frame_ + body, x, y)], h


def excluded_box(x, y, w, items, opened, mobile, always=False):
    """Las descartadas y su motivo. Plegadas por defecto; en el estado vacío van siempre a la vista (`always`)."""
    title = f"{len(items)} descartadas, con su motivo" if mobile else f"{len(items)} estrategias descartadas, cada una con su regla o motivo"
    if not opened:
        body = [poly(chamfer(0, 0, w, 64, 12), WHITE, D["cielo"], 2, "4 4"), text(24, 39, title, 17, 700)]
        body += link(w - 24, 39, "Ver por qué", 16, anchor="end")
        return [group("descartadas", body, x, y)], 64
    rows, yy = [], 70
    for seq, why, rule in items:
        lines = wrap(why, 38 if mobile else 118)
        rh = 50 + len(lines) * 19 + (22 if mobile else 6)
        rows += [f'<rect x="24" y="{yy}" width="{w - 48}" height="1" fill="{BORDE}"/>',
                 poly(chamfer(24, yy + 14, 22, 22, 0), WHITE, P["noche"], 2), f'<path d="M29 {yy + 19} l12 12 M41 {yy + 19} l-12 12" stroke="{P["noche"]}" stroke-width="2.5"/>',
                 text(58, yy + 32, seq, 17, 700)]
        rows += paragraph(58, yy + 54, lines, 14, 19)
        if mobile:
            rows.append(text(58, yy + 54 + len(lines) * 19 + 2, rule, 12, 700, SEC))
        else:
            rows.append(text(w - 24, yy + 32, rule, 13, 700, SEC, anchor="end"))
        yy += rh
    h = yy + 10
    body = [poly(chamfer(0, 0, w, h, 12), WHITE, D["cielo"], 2, "4 4"), text(24, 40, title, 17, 700)]
    if not always:
        body += link(w - 24, 40, "Ocultar", 16, anchor="end")
    return [group("descartadas", body + rows, x, y)], h


def label_strip(x, y, w, rows, kind_="info"):
    """Rótulo fijo y visible: lo que la pantalla es y lo que no es."""
    fill, stroke = {"info": ("#E6F0F5", D["cielo"]), "call": ("#EEF2E4", D["oliva"])}[kind_]
    h = 22 + len(rows) * 21
    return [group("rotulo", [poly(chamfer(0, 0, w, h, 10), fill, stroke, 1.5)] + paragraph(16, 27, rows, 15, 21, weight=700), x, y)], h


def context_rows(x, y, w, rows):
    """Lo que se usó para armar las estrategias, con el enlace para cambiarlo."""
    out = []
    for i, (label, value, action) in enumerate(rows):
        ry = y + i * 62
        out += [poly(chamfer(x, ry, w, 52, 10), P["niebla"]), text(x + 18, ry + 22, label, 13, fill=SEC), text(x + 18, ry + 42, value, 16, 700)]
        if action:
            out += link(x + w - 16, ry + 22, action, 14, anchor="end")
    return out, len(rows) * 62


# ---------- Entrada (HU-214) ----------

PREVIOUS = ("Papa",)  # de 0 a 3 cultivos del catálogo; «Nada» deja la lista vacía


def entry(mobile=False, lot=False):
    """Sin cuenta se llena todo a mano; con cuenta se entra desde el lote y esos datos ya vienen de él."""
    w = MOBILE[0] if mobile else DESKTOP[0]
    x, y, cw, pad = (12, 92, 366, 20) if mobile else (96, 120, 720, 36)
    fw = cw - 2 * pad
    c = [text(pad, 50, "ESTRATEGIAS DE ROTACIÓN" + (" · EL ALTO" if lot else ""), 15, 700, SEC)]
    title = ["¿Qué sembrar en los", "próximos ciclos?"] if mobile else ["¿Qué sembrar en los próximos ciclos?"]
    c += paragraph(pad, 92, title, 27 if mobile else 38, 34, weight=600, font=FONT_TITLE)
    yy = 92 + (len(title) - 1) * 34 + 24
    intro = (["Planes de 2 o 3 ciclos que cumplen las", "reglas de rotación, comparados por agua,", "suelo, ingreso y riesgo."] if mobile else
             ["Planes de 2 o 3 ciclos que cumplen las reglas de rotación,", "comparados por agua, suelo, ingreso y riesgo."])
    c += paragraph(pad, yy, intro, 15, 21, fill=SEC)
    yy += len(intro) * 21 + 16
    if lot:
        # Con cuenta: el lote, su riego y lo que había antes salen del lote y de su historial (`lot_id`, `follows_season_ids`).
        rows = (("Lote", "El Alto · Samacá, Boyacá", None), ("Riego del lote", "Sin riego", "Cambiar en el lote"),
                ("Terreno que va a sembrar", "Donde estuvo la papa · 1,26 ha", "Elegir otra parte"), ("Lo que había antes, según su historial", "Papa · cosechada el 22 dic 2026", None),
                ("Lo que viene sembrando, según su historial", "Papa → Arveja → Papa", "Corregir"))
        cr, chh = context_rows(pad, yy, fw, rows)
        c += cr
        yy += chh + 30
    else:
        c += [poly(chamfer(pad, yy, fw, 48, 10), P["niebla"]), poly([(pad + 22, yy + 12), (pad + 30, yy + 24), (pad + 22, yy + 36), (pad + 14, yy + 24)], D["brote"]),
              text(pad + 42, yy + 31, TOWN, 18, 700)] + link(pad + fw - 16, yy + 31, "Cambiar", 16, anchor="end")
        yy += 84
        half = fw if mobile else (fw - 16) / 2
        c += field(pad, yy, half, "Área que va a sembrar (ha)", AREA, name="campo-area", hint="Solo se usa en este navegador, para el agua del plan.")
        yy += 136
        # qué había antes
        c += [text(pad, yy, "¿Qué había antes en este terreno?", 18, 700), text(pad, yy + 22, "Hasta tres cultivos, del más reciente al más antiguo.", 14, fill=SEC)]
        cx = pad
        for crop in PREVIOUS:
            cwid = width_of(crop, 16, True) + 62
            c += [poly(chamfer(cx, yy + 38, cwid, 44, 9), "#E3EECF", D["oliva"], 2.5), text(cx + 16, yy + 66, crop, 16, 700),
                  f'<path d="M{cx + cwid - 30} {yy + 53} l12 12 M{cx + cwid - 18} {yy + 53} l-12 12" stroke="{P["noche"]}" stroke-width="2.5" stroke-linecap="round"/>']
            cx += cwid + 10
        add = "+ Agregar otro"
        c += [poly(chamfer(cx, yy + 38, width_of(add, 16, True) + 32, 44, 9), WHITE, BORDE, 2, "5 4"), text(cx + 16, yy + 66, add, 16, 700, D["oliva"])]
        yy += 100
        c += ui.checkbox(pad, yy, False, name="casilla-nada") + [text(pad + 44, yy + 22, "Nada: es la primera siembra aquí", 16)]
        yy += 62
        # la rotación actual (HU-223): su rotación de siempre, en el orden en que la siembra; se compara con las sugeridas
        c += [text(pad, yy, "¿Qué viene sembrando en este terreno?", 18, 700)]
        hint = (["Su rotación de siempre, en orden. Las", "estrategias se comparan contra ella."] if mobile else
                ["Su rotación de siempre, en el orden en que la siembra. Las estrategias se comparan contra ella."])
        c += paragraph(pad, yy + 22, hint, 14, 19, fill=SEC)
        cy = yy + 22 + (len(hint) - 1) * 19 + 16
        cx = pad
        for i, crop in enumerate(("Papa", "Arveja")):
            if i:
                c.append(text(cx, cy + 28, "→", 18, 700))
                cx += 24
            cwid = width_of(crop, 16, True) + 62
            c += [poly(chamfer(cx, cy, cwid, 44, 9), "#E6F0F5", D["cielo"], 2.5), text(cx + 16, cy + 28, crop, 16, 700),
                  f'<path d="M{cx + cwid - 30} {cy + 15} l12 12 M{cx + cwid - 18} {cy + 15} l-12 12" stroke="{P["noche"]}" stroke-width="2.5" stroke-linecap="round"/>']
            cx += cwid + 10
        add = "+ Agregar"
        aw = width_of(add, 16, True) + 32
        if cx + aw > pad + fw:  # no cabe en la fila: baja a la siguiente
            cx, cy = pad, cy + 54
        c += [poly(chamfer(cx, cy, aw, 44, 9), WHITE, BORDE, 2, "5 4"), text(cx + 16, cy + 28, add, 16, 700, D["cielo"])]
        yy = cy + 62
        c += ui.checkbox(pad, yy, False, name="casilla-sin-rotacion") + [text(pad + 44, yy + 22, "No tengo una rotación fija", 16)]
        yy += 62
    # cuándo sembrar el primer ciclo
    c += [text(pad, yy, "¿Cuándo sembrar el primer ciclo?", 18, 700), text(pad, yy + 22, "Un mes de los próximos doce. Los demás ciclos salen de él.", 14, fill=SEC)]
    mc = 4 if mobile else 6
    mw, mh = (fw - (mc - 1) * 8) / mc, 50
    for i, (mon, yr) in enumerate(MONTHS):
        c += chip(pad + (i % mc) * (mw + 8), yy + 38 + (i // mc) * (mh + 8), mw, mh, mon, i == CHOSEN_MONTH, yr or None)
    yy += 38 + ((12 + mc - 1) // mc) * (mh + 8) + 26
    if not lot:
        c += [text(pad, yy, "¿Tiene riego?", 18, 700), text(pad, yy + 22, "Con riego, que no llueva no es un riesgo.", 14, fill=SEC)]
        c += options(pad, yy + 36, fw, ("Sí", "No", "No sé"), 1)
        yy += 112
    c += [text(pad, yy, "¿Cuántos ciclos quiere planear?", 18, 700), text(pad, yy + 22, "Un ciclo es un cultivo, un abono verde o un descanso.", 14, fill=SEC)]
    c += options(pad, yy + 36, fw if mobile else 320, ("2 ciclos", "3 ciclos"), 1)
    yy += 116
    # las dos clases de prioridades, plegadas
    c.append(text(pad, yy, "Sus prioridades", 18, 700))
    rot = "Rotación: " + " · ".join(f"{label} {value}" for _, label, value, _ in PRIORITIES)
    prio = [poly(chamfer(0, 0, fw, 50, 10), WHITE, BORDE, 1.5), text(16, 22, "¿Qué busca en la rotación?", 15, 700), text(16, 40, rot, 12, fill=SEC)] + link(fw - 16, 24, "Ajustar", 15, anchor="end")
    c.append(group("prioridades-rotacion", prio, pad, yy + 14))
    c += sg.priorities_summary(pad, yy + 74, fw, muestra.DEFAULT_WEIGHTS, own=False)
    yy += 74 + (88 if mobile else 72)
    c += button(pad, yy, fw, "Ver estrategias")
    yy += 84
    if lot:
        c += link(pad, yy + 6, "‹ Volver a El Alto", 16)
    else:
        c += paragraph(pad, yy + 6, ["Sin cuenta, nada de esto se guarda.", "Con cuenta, se usa el historial de su lote."] if mobile else
                       ["Sin cuenta, nada de esto se guarda. Con cuenta, se usan el historial y el suelo de su lote."], 14, 20, fill=SEC)
        yy += 20 if mobile else 0
    ch = yy + 34
    h = max(900, y + ch + 60)
    b = scene("a5-municipio", w, h, "recorte-entrada-estrategias" + ("-m" if mobile else "") + ("-l" if lot else ""), 0.1)
    b += topbar(w, "Mi finca" if lot else "Consultar", user="Rosa" if lot and not mobile else None)
    b += card(x, y, cw, ch) + [group("contenido", c, x, y)]
    if not mobile:
        b += mascot(920, 220, 1.3, "guia", "germinada")
    return frame((w, h), b)


# ---------- Estrategias (HU-101, HU-102) ----------

def strategies(mobile=False, opened=False, empty=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    header_h = 560 if mobile else 470
    tagname = ("-m" if mobile else "") + ("-d" if opened else "") + ("-v" if empty else "")
    b = scene("a5-municipio", w, header_h, "recorte-estrategias" + tagname, 0.12)
    b += topbar(w, "Consultar")  # sin cuenta: barra del invitado
    x, y, cw, pad = (12, 92, 366, 22) if mobile else (96, 116, 1248, 36)
    fw = cw - 2 * pad
    town = "Toca, Boyacá" if empty else TOWN
    c = [text(pad, 44, "ESTRATEGIAS · " + (town.split(",")[0].upper() if mobile else town.upper()), 14, 700, SEC)]
    title = ["Estrategias para", "los próximos 3 ciclos"] if mobile else ["Estrategias para los próximos 3 ciclos"]
    c += paragraph(pad, 86 if mobile else 92, title, 26 if mobile else 32, 32, weight=600, font=FONT_TITLE)
    cy0 = (86 + len(title) * 32 - 8) if mobile else 120
    ctx_w = fw if mobile else 540
    rows = (("Terreno y lo que había antes", ("1,26 ha · antes: maíz" if empty else "1,26 ha · antes: papa") + (" · sin cuenta" if not mobile else ""), "Cambiar"),
            ("Lo que viene sembrando", "Maíz → Papa" if empty else CURRENT_LABEL, "Cambiar"),
            ("Primer ciclo y riego", ("1 de marzo de 2027 · sin riego" if empty else f"{SOWING} · sin riego"), "Cambiar"),
            (f"Suelo estimado de {town.split(',')[0]} · 250 m", "pH 5,3 a 5,9 · carbono medio" if empty else ("pH 5,2 a 5,8 · carbono medio" if mobile else SOIL_USED), "Ver suelo"))
    cr, chh = context_rows(pad, cy0, ctx_w, rows)
    c += cr
    note_y = cy0 + chh + 12
    c += paragraph(pad, note_y, ["El suelo es una estimación de un mapa de", "250 m, no una medición de su lote."] if mobile else
                   ["El suelo es una estimación de un mapa de 250 m, no una medición de su lote.", "Un análisis de suelo le da el dato real."], 14, 20, fill=SEC)
    if mobile:
        pp_y = note_y + 62
        c += priorities_panel(pad, pp_y, fw, True)
        ch = pp_y + 52 + 4 * 66 + 20
    else:
        c += priorities_panel(pad + 660, 74, fw - 660, False)
        ch = max(note_y + 56, 440)
    b += card(x, y, cw, ch) + [group("contexto", c, x, y)]
    top = max(header_h, y + ch + 40)
    pad2 = 16 if mobile else 96
    iw = w - 2 * pad2
    s, yy = [], 10
    lb, lh = label_strip(pad2, yy, iw, wrap(NOT_FORECAST, 38) if mobile else [NOT_FORECAST])
    s += lb
    yy += lh + 34
    if empty:
        # Sin estrategias válidas: se dice, se propone qué cambiar y las descartadas quedan a la vista.
        eh = 300 if mobile else 190
        e = [poly(chamfer(0, 8, iw, eh, 16), BORDE), poly(chamfer(0, 0, iw, eh, 16), WHITE, D["cielo"], 2, "6 5")]
        etitle = ["Ninguna estrategia cumple", "las reglas con estos datos"] if mobile else ["Ninguna estrategia cumple las reglas con estos datos"]
        e += paragraph(24, 46, etitle, 21 if mobile else 26, 28, weight=600, font=FONT_TITLE)
        ey = 46 + len(etitle) * 28
        why = (["En Toca, sembrando en marzo, el maíz y lo", "que le sigue caen en meses de heladas", "graves. No es que su terreno sea malo:", "pruebe otra fecha o menos ciclos."] if mobile else
               ["En Toca, sembrando el primer ciclo en marzo, todas las secuencias pasan por meses de heladas graves.",
                "No es que su terreno sea malo: pruebe con otra fecha de siembra o con dos ciclos en vez de tres."])
        e += paragraph(24, ey, why, 15, 22)
        ey += len(why) * 22 + 12
        if mobile:
            e += button(24, ey, iw - 48, "Cambiar la fecha") + button(24, ey + 62, iw - 48, "Probar con 2 ciclos", "secondary")
        else:
            e += button(24, ey, 260, "Cambiar la fecha") + button(300, ey, 260, "Probar con 2 ciclos", "secondary")
            e += mascot(iw - 210, 16, 0.5, "sin-datos")
        s.append(group("sin-estrategias", e, pad2, yy))
        yy += eh + 36
        box, bh = excluded_box(pad2, yy, iw, EXCLUDED_EMPTY, True, mobile, always=True)
        s += box
        yy += bh
    else:
        # la rotación actual va primero, como referencia (HU-223); no entra al orden
        s.append(text(pad2, yy + 26, "Lo que usted siembra hoy", 24 if mobile else 32, 600, font=FONT_TITLE))
        s += paragraph(pad2, yy + 56, ["Su rotación de siempre, evaluada igual.", "Las demás dicen cuánto ganan o pierden."] if mobile else
                       ["Su rotación de siempre, evaluada con los mismos criterios. Cada estrategia de abajo dice cuánto gana o pierde frente a ella."], 16, 22, fill=SEC)
        yy += 110 if mobile else 92
        cc, chc = strategy_card(pad2, yy, iw, None, CURRENT, mobile)
        s += cc
        yy += chc + 44
        s.append(text(pad2, yy + 26, "Ordenadas por lo que le importa" if mobile else "Estrategias ordenadas por lo que le importa", 24 if mobile else 32, 600, font=FONT_TITLE))
        s += paragraph(pad2, yy + 56, ["Solo las que cumplen las reglas. Puntaje", "de 0 a 100 por criterio."] if mobile else
                       ["Solo las que cumplen las reglas de rotación. Puntaje de 0 a 100 por criterio, ponderado por sus prioridades."], 16, 22, fill=SEC)
        yy += 110 if mobile else 92
        order = ranked()
        if mobile:
            for i, st in enumerate(order):
                sc, sh = strategy_card(pad2, yy, iw, i + 1, st, True)
                s += sc
                yy += sh + 24
        else:
            ow = (iw - 24) / 2
            for r in range(0, len(order), 2):
                heights = []
                for k, st in enumerate(order[r:r + 2]):
                    sc, sh = strategy_card(pad2 + k * (ow + 24), yy, ow, r + k + 1, st)
                    s += sc
                    heights.append(sh)
                yy += max(heights) + 30
        box, bh = excluded_box(pad2, yy + 4, iw, EXCLUDED, opened, mobile)
        s += box
        yy += bh + 4
    yy += 30
    cb, chh2 = label_strip(pad2, yy, iw, YOUR_CALL.split(". ", 1) if mobile else [YOUR_CALL], "call")
    s += cb
    vy = yy + chh2 + 40
    s.append(text(pad2, vy, f"{muestra.VERSIONS} · Cifras de muestra", 15, fill=SEC))
    s += link(pad2 if mobile else w - pad2, vy + (30 if mobile else 0), "¿Cómo se arma este orden?", 15, anchor="start" if mobile else "end")
    h = top + vy + 70
    b = [f'<rect y="{header_h}" width="{w}" height="{h - header_h}" fill="{P["niebla"]}"/>'] + b + [group("estrategias", s, 0, top)]
    foot, fh = ui.footer(w, h, mobile, above=P["niebla"])
    return frame((w, h + fh), b + foot)


SCREENS = {
    "estrategias-01-entrada-escritorio": lambda: entry(),
    "estrategias-01-entrada-movil": lambda: entry(mobile=True),
    "estrategias-01-entrada-desde-el-lote-escritorio": lambda: entry(lot=True),
    "estrategias-02-ranking-escritorio": lambda: strategies(),
    "estrategias-02-ranking-movil": lambda: strategies(mobile=True),
    "estrategias-03-descartadas-escritorio": lambda: strategies(opened=True),
    "estrategias-03-descartadas-movil": lambda: strategies(mobile=True, opened=True),
    "estrategias-04-sin-opciones-escritorio": lambda: strategies(empty=True),
    "estrategias-04-sin-opciones-movil": lambda: strategies(mobile=True, empty=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
    for st in ranked():
        print(f"  {' > '.join(c[0] for c in st['cycles'])}: {total(st)} {scores_of(st)}")
