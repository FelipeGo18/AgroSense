"""Piezas compartidas de las señales de una ventana de siembra (specs/01-reglas.md y specs/05-frontend.md).

Las usan la consulta, el calendario, las rotaciones y la próxima siembra:
- íconos de las seis señales (agua y calor son nuevos);
- barra de calificación de 0 a 100 con sus tres franjas; sin calificación no hay barra (R1);
- tarjeta de señal con su nota, «Lo que más limita» y «No cuenta para su luz»;
- bloque de dos luces (con sus prioridades y con el criterio de AgroSense);
- resumen plegado de prioridades y panel de los seis pesos con semillas;
- aptitud del cultivo con su nota y cinco semillas, y el letrero «No se da en su zona»;
- tarjetas de cultivos alternativos.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
import muestra  # noqa: E402
from build_kit_svg import seed, shade  # noqa: E402
from consulta import kind as _kind, light, mist, tag  # noqa: E402,F401
from ui import BORDE, D, FONT_TITLE, P, SEC, WHITE, button, chamfer, group, link, paragraph, poly, text, width_of  # noqa: E402

LIGHT_TEXT = {"verde": "Puede sembrar", "amarillo": "Con cuidado", "rojo": "Alto riesgo", "no-evaluable": "No se puede evaluar"}
ACTION_TEXT = {"sow": "Sembrar en esta fecha", "rotate": "Mejor otro cultivo en esta fecha", "other_window": "Mejor otra fecha", "review_data": "Revisar los datos"}
BAND = (("desfavorable", 0, 40, "#F6D9D4"), ("moderado", 40, 70, "#F8E7C2"), ("favorable", 70, 100, "#DCEBC2"))
FILL = {"favorable": P["brote"], "moderado": P["trigo"], "desfavorable": P["rojo"]}
KEY_TO_KIND = {"water": "agua", "frost": "heladas", "heat": "calor", "soil": "suelo", "supply": "oferta", "market": "mercado"}


# ---------- Íconos ----------

def kind(k, x, y):
    """Ícono de 44 × 44 de una señal. Agua y calor son nuevos; los demás vienen de consulta.py."""
    if k == "agua":  # gota facetada sobre un surco
        return [poly([(x + 2, y + 36), (x + 42, y + 36), (x + 38, y + 43), (x + 6, y + 43)], P["tierra"]),
                poly([(x + 22, y + 2), (x + 34, y + 20), (x + 30, y + 32), (x + 14, y + 32), (x + 10, y + 20)], P["cielo"], D["cielo"], 2),
                poly([(x + 22, y + 2), (x + 10, y + 20), (x + 14, y + 32), (x + 22, y + 32)], shade(P["cielo"], 0.18))]
    if k == "calor":  # sol facetado con rayos
        out = []
        cx, cy = x + 22, y + 22
        for i in range(8):
            import math
            a = math.pi / 4 * i
            tip = (cx + 21 * math.cos(a), cy + 21 * math.sin(a))
            l = (cx + 12 * math.cos(a - 0.3), cy + 12 * math.sin(a - 0.3))
            r = (cx + 12 * math.cos(a + 0.3), cy + 12 * math.sin(a + 0.3))
            out.append(poly([l, tip, r], P["calabaza"]))
        out.append(poly(chamfer(cx - 11, cy - 11, 22, 22, 6), P["trigo"], D["calabaza"], 2))
        out.append(poly([(cx - 11, cy - 5), (cx - 5, cy - 11), (cx + 5, cy - 11), (cx - 3, cy + 1)], shade(P["trigo"], 0.2)))
        return out
    return _kind(k, x, y)


# ---------- Calificación ----------

def score_bar(x, y, w, score, h=12, show_number=True):
    """Barra de 0 a 100 con las tres franjas de nivel. Sin calificación, no hay barra (R1)."""
    out = []
    if score is None:
        out += [poly(chamfer(x, y, w, h, 3), WHITE, D["cielo"], 1.5, "3 4"), text(x + w / 2, y + h + 16, "Sin calificación", 12, fill=SEC, anchor="middle")]
        return out
    for _, a, b, col in BAND:
        out.append(f'<rect x="{x + w * a / 100:.1f}" y="{y}" width="{w * (b - a) / 100:.1f}" height="{h}" fill="{col}"/>')
    lv = muestra.level_of(score)
    out.append(f'<rect x="{x}" y="{y}" width="{w * score / 100:.1f}" height="{h}" fill="{FILL[lv]}"/>')
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{P["noche"]}" stroke-width="1.5"/>')
    mx = x + w * score / 100
    out.append(poly([(mx - 6, y - 7), (mx + 6, y - 7), (mx, y + 1)], P["noche"]))
    if show_number:
        out.append(text(x + w, y - 6, f"{score}/100", 13, 700, anchor="end"))
    return out


def seeds(x, y, n, scale=0.5):
    """Escala de cinco semillas, la misma de las prioridades."""
    body = []
    for i in range(5):
        body += seed(i * 50, 0, i < n)
    return [f'<g transform="translate({x:g} {y:g}) scale({scale:g})">{"".join(body)}</g>']


def score_to_seeds(score):
    return max(0, min(5, round(score / 20)))


# ---------- Tarjeta de señal ----------

def signal_card(x, y, w, h, key, weights, limiting=None, compact=False, signals=None):
    """Tarjeta de una señal con su estado (forma y texto), nota de 0 a 100 y razones."""
    case = (signals or muestra.SIGNALS_CASE)[key]
    status = muestra.level_of(case["score"], case.get("status"))
    counts = weights[key] > 0 or (key in muestra.CLIMATE and case.get("critical"))
    ins = status in ("insuficiente", "no-aplica")
    body = [poly(chamfer(0, 6, w, h, 14), BORDE),
            poly(chamfer(0, 0, w, h, 14), WHITE if counts else "#F4F6F8", D["cielo"] if ins else (P["calabaza"] if key == limiting else None),
                 2.5 if (ins or key == limiting) else 0, "3 5" if ins else None)]
    if ins:
        body += mist(w, h)
    body += kind(KEY_TO_KIND[key], w - 60, 14)
    body.append(text(18, 40, muestra.SIGNAL_NAME[key], 21, 600, font=FONT_TITLE))
    if case.get("note"):
        body.append(text(18, 60, case["note"], 13, 700, SEC))
    ty = 70
    body += tag(18, ty, status, min(w - 36, 172), 34, case.get("critical"))
    by = ty + 54
    if status == "no-aplica":
        body.append(text(18, by + 22, "No se califica: no aplica a este cultivo", 12, fill=SEC))
    else:
        body += score_bar(18, by + 12, w - 36, case["score"])
    ry = by + 50
    if key == limiting:
        body += [poly(chamfer(18, ry - 18, 150, 24, 5), P["calabaza"]), text(30, ry - 1, "Lo que más limita", 13, 700)]
        ry += 22
    if not counts and status != "no-aplica":
        body += [poly(chamfer(18, ry - 18, 196, 24, 5), WHITE, D["cielo"], 1.5), text(30, ry - 1, f"No cuenta para su luz (peso 0)", 12, 700, D["cielo"])]
        ry += 22
    body += paragraph(18, ry + 6, case["reasons"], 14 if compact else 15, 20)
    body += link(18, h - 18, "Ver detalle", 14)
    return [group(f"senal-{key}", body, x, y)]


# ---------- Dos luces ----------

def light_block(x, y, w, result, title, primary=True):
    """Una luz con su acción. La principal va más grande. En anchos angostos, la acción baja a otra línea."""
    narrow = w < 420
    sc = (0.46 if primary else 0.34) * (0.7 if narrow else 1)
    body = light(result["light"], 0, 0, sc)
    tx = 340 * sc + 14
    big = 22 if primary else 17
    limit = f"Lo que más limita: {muestra.SIGNAL_NAME[result['limiting']].lower()}"
    body.append(text(tx, 16, title.upper(), 12, 700, SEC))
    if narrow:
        body += [text(tx, 40, LIGHT_TEXT[result["light"]], big - 2, 600, font=FONT_TITLE),
                 text(0, 74 if primary else 66, ACTION_TEXT[result["action"]], 16, 700),
                 text(0, 94 if primary else 86, limit, 13, fill=SEC)]
    else:
        body += [text(tx, 48 if primary else 38, f"{LIGHT_TEXT[result['light']]} · {ACTION_TEXT[result['action']]}", big, 600, font=FONT_TITLE),
                 text(tx, 72 if primary else 58, limit, 14, fill=SEC)]
    return [group("luz-" + ("agricultor" if primary else "agrosense"), body, x, y)]


def two_lights(x, y, w, farmer, default, why):
    """Las dos luces cuando difieren: la del agricultor primero y más grande; la de AgroSense al lado, nunca escondida."""
    narrow = w < 420
    out = light_block(0, 0, w, farmer, "Con sus prioridades", True)
    sep = 112 if narrow else 104
    out += [f'<rect x="0" y="{sep}" width="{w}" height="1" fill="{BORDE}"/>']
    out += light_block(0, sep + 18, w, default, "Con el criterio de AgroSense", False)
    wy = sep + (112 if narrow else 84)
    lines = [why[:why.index(":") + 1], why[why.index(":") + 2:]] if narrow and ":" in why else [why]
    hh = 20 + len(lines) * 20
    out += [poly(chamfer(0, wy, w, hh, 8), "#EEF2E4")] + paragraph(14, wy + 26, lines, 14, 20, weight=700)
    return [group("dos-luces", out, x, y)], wy + hh


# ---------- Prioridades ----------

def priorities_summary(x, y, w, weights, own):
    """Resumen plegado: «Criterio de AgroSense · Ajustar» o «Sus prioridades · Ajustar»."""
    label = "Sus prioridades" if own else "Criterio de AgroSense"
    parts = [f"{muestra.SIGNAL_NAME[k]} {weights[k]}" for k in muestra.SIGNAL_ORDER]
    narrow = w < 420
    rows = [" · ".join(parts[:3]), " · ".join(parts[3:])] if narrow else [" · ".join(parts)]
    hh = 34 + len(rows) * 16
    body = [poly(chamfer(0, 0, w, hh, 10), WHITE, BORDE, 1.5), text(16, 22, label, 15, 700)]
    body += [text(16, 40 + i * 16, r, 12, fill=SEC) for i, r in enumerate(rows)]
    body += link(w - 16, 24, "Ajustar", 15, anchor="end")
    return [group("prioridades-resumen", body, x, y)]


def priority_row(x, y, w, key, value, compact=False):
    """Una fila del panel: nombre, para qué sirve, casilla de 0 y cinco semillas."""
    body = [text(0, 22, muestra.SIGNAL_NAME[key], 17, 700), text(0, 42, muestra.SIGNAL_HINT[key], 13, fill=SEC)]
    sc = 0.62 if not compact else 0.52
    sx = w - 306 * sc
    zero = value == 0
    row = [poly(chamfer(2, 2, 44, 44, 8), P["niebla"] if zero else WHITE, P["noche"] if zero else BORDE, 2.5), text(24, 31, "0", 16, 700, anchor="middle")]
    for i in range(5):
        row += seed(56 + i * 50, 2, i < value)
    body.append(f'<g transform="translate({sx:g} 4) scale({sc:g})">{"".join(row)}</g>')
    if key in muestra.CLIMATE:
        body.append(text(0, 60, "Un riesgo grave cuenta siempre", 12, 700, D["cielo"]))
    return [group(f"peso-{key}", body, x, y)]


def priorities_panel(x, y, w, weights, compact=False):
    """Los seis pesos, de 0 a 5. Qué significa cada valor y cómo volver al criterio de AgroSense."""
    out = [text(0, 0, "¿Qué le importa al elegir la fecha?", 22 if not compact else 19, 600, font=FONT_TITLE)]
    out += paragraph(0, 28, ["0: no cambia la luz · 1 a 3: normal ·", "4 y 5: un «moderado» ya cuenta en contra."] if compact else
                     ["0: no cambia la luz · 1 a 3: importancia normal · 4 y 5: un «moderado» ya cuenta en contra."], 14, 20, fill=SEC)
    yy = 70 if compact else 56
    for k in muestra.SIGNAL_ORDER:
        out += priority_row(0, yy, w, k, weights[k], compact)
        yy += 78 if k in muestra.CLIMATE else 66
    return [group("prioridades", out, x, y)], yy


# ---------- Aptitud ----------

def suitability_line(x, y, w, suit):
    """Aptitud del cultivo en la zona: nota de 0 a 100 y cinco semillas (HU-191)."""
    if w < 420:  # móvil: la razón en dos líneas y las semillas debajo del título
        r = suit["reason"]
        cut = r.index("está")
        body = [poly(chamfer(0, 0, w, 104, 10), "#EEF2E4"), text(16, 26, "Se da en su zona", 16, 700), text(w - 16, 26, f"{suit['score']}/100", 16, 700, anchor="end")]
        body += seeds(14, 34, score_to_seeds(suit["score"]), 0.4)
        body += [text(16, 76, r[:cut].strip(), 13, fill=SEC), text(16, 94, r[cut:], 13, fill=SEC)]
        return [group("aptitud", body, x, y)]
    body = [poly(chamfer(0, 0, w, 56, 10), "#EEF2E4"), text(16, 24, "Se da en su zona", 16, 700), text(16, 44, suit["reason"], 13, fill=SEC)]
    body += seeds(w - 210, 9, score_to_seeds(suit["score"]), 0.48)
    body.append(text(w - 16, 34, f"{suit['score']}/100", 16, 700, anchor="end"))
    return [group("aptitud", body, x, y)]


def not_suitable_sign(x, y, w, crop, town, score, reason, source):
    """Letrero propio, sin semáforo: el cultivo no se da en la zona."""
    body = [poly(chamfer(0, 6, w, 150, 14), BORDE), poly(chamfer(0, 0, w, 150, 14), WHITE, P["noche"], 3)]
    body += [poly([(28, 22), (52, 22), (62, 40), (40, 66), (18, 40)], P["niebla"], P["noche"], 2.5),
             f'<path d="M26 30 l28 28 M54 30 l-28 28" stroke="{P["noche"]}" stroke-width="3"/>']
    body += [text(84, 40, f"{crop} no se da en {town}", 24, 600, font=FONT_TITLE), text(84, 66, reason, 15)]
    body += [text(84, 96, "Aptitud", 14, 700, SEC)] + seeds(150, 80, score_to_seeds(score), 0.44) + [text(290, 98, f"{score}/100", 15, 700)]
    body.append(text(84, 128, f"Fuente: {source}", 13, fill=SEC))
    return [group("no-se-da-en-su-zona", body, x, y)], 156


# ---------- Alternativas ----------

def alternatives(x, y, w, items, compact=False):
    """Cultivos aptos que en esta ventana salen bien en clima y tienen mejor oferta (`alternatives`)."""
    out = [text(0, 0, "Otros cultivos para esta fecha", 22 if not compact else 20, 600, font=FONT_TITLE)]
    out += paragraph(0, 26, ["Se dan en su zona, salen bien en clima", "y hay menos sembrado. Usted decide."] if compact else
                     ["Se dan en su zona, salen bien en clima en esta fecha y hay menos sembrado. Usted decide."], 14, 20, fill=SEC)
    cols = 1 if compact else 2
    cw = (w - (cols - 1) * 20) / cols
    ch = 150
    top = 64 if compact else 44
    for i, it in enumerate(items):
        cx, cy = (i % cols) * (cw + 20), top + (i // cols) * (ch + 16)
        body = [poly(chamfer(0, 6, cw, ch, 12), BORDE), poly(chamfer(0, 0, cw, ch, 12), WHITE)]
        body += [text(18, 34, it["crop"], 20, 600, font=FONT_TITLE), text(cw - 18, 34, f"{it['limiting_score']}/100", 15, 700, anchor="end"),
                 text(cw - 18, 52, f"limita: {it['limiting'].lower()}", 12, fill=SEC, anchor="end")]
        body += paragraph(18, 68, it["reasons"], 14, 20)
        body += link(18, ch - 16, f"Ver diagnóstico de {it['crop'].lower()}", 14)
        out.append(group(f"alternativa-{it['crop'].lower()}", body, cx, cy))
    rows = (len(items) + cols - 1) // cols
    return [group("alternativas", out, x, y)], top + rows * (ch + 16)


# ---------- Mejores fechas ----------

def best_windows(x, y, w, crop, windows, compact=False):
    """Hasta tres ventanas de los próximos doce meses, sin las de alto riesgo (`best_windows`). Puede no haber ninguna."""
    out = [text(0, 0, "Mejores fechas, próximos 12 meses" if compact else "Mejores fechas en los próximos doce meses", 20 if compact else 22, 600, font=FONT_TITLE)]
    out += paragraph(0, 26, ["Según la historia de la zona. No es un", "pronóstico: usted decide."] if compact else
                     ["Ordenadas por lo que más limita cada fecha. Según la historia de la zona; no es un pronóstico: usted decide."], 14, 20, fill=SEC)
    top = 66 if compact else 46
    if not windows:
        body = [poly(chamfer(0, 0, w, 150 if compact else 118, 12), WHITE, D["cielo"], 2, "5 5")]
        body += paragraph(20, 34, [f"En los próximos doce meses no hay una", f"fecha sin riesgo alto para el {crop.lower()}", "en esta zona."] if compact else
                          [f"En los próximos doce meses no hay una fecha sin riesgo alto para el {crop.lower()} en esta zona."], 16, 22, weight=700)
        ly = 112 if compact else 72
        body += link(20, ly, "Ver qué sembrar en su lugar", 15)
        if not compact:
            body += link(300, ly, "Ver el calendario completo", 15)
        out.append(group("sin-fechas", body, 0, top))
        return [group("mejores-fechas", out, x, y)], top + (150 if compact else 118)
    cols = 1 if compact else 3
    cw = (w - (cols - 1) * 16) / cols
    ch = 168
    for i, it in enumerate(windows):
        cx, cy = (i % cols) * (cw + 16), top + (i // cols) * (ch + 14)
        body = [poly(chamfer(0, 6, cw, ch, 12), BORDE), poly(chamfer(0, 0, cw, ch, 12), WHITE, P["calabaza"] if i == 0 else None, 2.5 if i == 0 else 0)]
        body += [text(18, 30, f"Siembra {it['sowing']}", 18, 700), text(18, 52, f"Cosecha estimada {it['harvest']}", 13, fill=SEC)]
        body += [text(18, 86, f"{it['limiting_score']}/100", 24, 600, font=FONT_TITLE), text(90, 86, f"limita: {it['limiting'].lower()}", 14, fill=SEC)]
        body += [text(18, 112, f"Con sus prioridades: {it['weighted']}/100", 13, fill=SEC)]
        body += link(18, ch - 18, "Ver el diagnóstico de esta fecha", 14)
        out.append(group(f"fecha-{i + 1}", body, cx, cy))
    rows = (len(windows) + cols - 1) // cols
    return [group("mejores-fechas", out, x, y)], top + rows * (ch + 14)
