"""Calendario «Planear una siembra» por ventanas (rediseño, tanda 3; HU-180, HU-192). Escritorio y móvil.

Las doce ventanas de los próximos doce meses para un cultivo, ordenadas como dice specs/01-reglas.md: primero el
factor que más limita cada fecha y, entre fechas parecidas, el promedio con las prioridades del agricultor. Las de
alto riesgo (una señal crítica) van al final y nunca entre las mejores. Arriba, el año de un vistazo; al abrir un
mes, sus semanas. Con cuenta, para una parte del lote; sin cuenta, desde la consulta. Es la historia de la zona,
no un pronóstico: decide el agricultor. Los datos salen de muestra.py.

    python design/pantallas/ventanas.py     # escribe svg/finca-03-calendario-planear-*, -semanas-* y consulta-04-calendario-sin-cuenta-*
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
import muestra as m  # noqa: E402
import senales as sg  # noqa: E402
from calendario import crop_chips, mode_toggle, tag  # noqa: E402
from finca import lot_header, lot_tabs  # noqa: E402
from ui import BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, card, chamfer, field, frame, group, link, paragraph, poly, text, topbar  # noqa: E402

FULL = {"Oct": "octubre", "Nov": "noviembre", "Dic": "diciembre", "Ene": "enero", "Feb": "febrero", "Mar": "marzo", "Abr": "abril",
        "May": "mayo", "Jun": "junio", "Jul": "julio", "Ago": "agosto", "Sep": "septiembre"}
LEVEL_FILL = {"favorable": P["brote"], "moderado": P["trigo"], "desfavorable": P["rojo"]}


def year_chart(x, y, w, h, chrono, compact=False):
    """El año de un vistazo: por mes de siembra, la nota del factor que más limita. Alto riesgo, rayado."""
    out = [text(0, -16, "El año de un vistazo: lo que más limita cada mes de siembra (0 a 100)", 14, 700, SEC) if not compact else
           text(0, -16, "Lo que más limita cada mes (0 a 100)", 13, 700, SEC)]
    n = len(chrono)
    bw = w / n * 0.66
    out.append(f'<defs><pattern id="rayado-alto-riesgo" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
               f'<rect width="8" height="8" fill="{P["rojo"]}" fill-opacity="0.18"/><rect width="3" height="8" fill="{P["rojo"]}" fill-opacity="0.55"/></pattern></defs>')
    out.append(f'<rect x="0" y="{h}" width="{w}" height="2" fill="{P["noche"]}"/>')
    for t in (40, 70):
        ty = h - h * t / 100
        out += [f'<rect x="0" y="{ty:.1f}" width="{w}" height="1" fill="{BORDE}" stroke-dasharray="4 3"/>', text(-6, ty + 4, str(t), 11, fill=SEC, anchor="end")]
    for i, win in enumerate(chrono):
        bx = i * w / n + (w / n - bw) / 2
        bh = max(4, h * win["limiting_score"] / 100)
        lv = m.level_of(win["limiting_score"])
        fill = "url(#rayado-alto-riesgo)" if win["high_risk"] else LEVEL_FILL[lv]
        best = win["rank"] <= 3
        out.append(poly(chamfer(bx, h - bh, bw, bh, 3), fill, P["calabaza"] if best else (P["rojo"] if win["high_risk"] else P["noche"]), 2.5 if best else 1.2))
        out.append(text(bx + bw / 2, h - bh - 6, str(win["limiting_score"]), 11 if compact else 12, 700, anchor="middle"))
        out.append(text(bx + bw / 2, h + 18, win["month"], 11 if compact else 12, 700 if best else 400, P["noche"] if best else SEC, anchor="middle"))
        if win["month"] in ("Oct", "Ene") and not compact:
            out.append(text(bx + bw / 2, h + 34, str(win["year"]), 11, fill=SEC, anchor="middle"))
        if best:
            out += [poly([(bx + bw / 2 - 9, h + 26 + (12 if compact else 18)), (bx + bw / 2 + 9, h + 26 + (12 if compact else 18)), (bx + bw / 2, h + 18 + (12 if compact else 18))], P["calabaza"])]
    ly = h + (50 if compact else 62)
    out += [poly(chamfer(0, ly - 11, 14, 14, 3), WHITE, P["calabaza"], 2.5), text(20, ly, "Entre las mejores", 12, fill=SEC),
            poly(chamfer(140, ly - 11, 14, 14, 3), "url(#rayado-alto-riesgo)", P["rojo"], 1.2), text(160, ly, "Alto riesgo", 12, fill=SEC)]
    return [group("ano-de-un-vistazo", out, x, y)]


def mini_scores(x, y, scores, gap=58):
    """Las seis señales de una ventana en pequeño: ícono, nota y color de nivel."""
    out = []
    for i, k in enumerate(m.SIGNAL_ORDER):
        v = scores[k]
        cx = x + i * gap
        out.append(f'<g transform="translate({cx:g} {y - 18:g}) scale(0.5)">{"".join(sg.kind(sg.KEY_TO_KIND[k], 0, 0))}</g>')
        if v is None:
            out += [poly(chamfer(cx + 24, y - 14, 30, 20, 4), WHITE, D["cielo"], 1.2, "3 3"), text(cx + 39, y + 1, "?", 12, 700, D["cielo"], anchor="middle")]
        else:
            lv = m.level_of(v)
            out += [poly(chamfer(cx + 24, y - 14, 30, 20, 4), LEVEL_FILL[lv]), text(cx + 39, y + 1, str(v), 12, 700, WHITE if lv == "desfavorable" else P["noche"], anchor="middle")]
    return out


def window_row(x, y, w, win, compact=False):
    """Una fecha de siembra en el orden: siembra, cosecha, lo que más limita, promedio y sus seis señales."""
    best = win["rank"] <= 3 and not win["high_risk"]
    h = 168 if compact else 92
    body = [poly(chamfer(0, 0, w, h, 10), "#FFF6EA" if best else WHITE, P["calabaza"] if best else (P["rojo"] if win["high_risk"] else BORDE), 2.5 if best or win["high_risk"] else 1.2)]
    body += [poly(chamfer(14, 14, 36, 36, 6), P["calabaza"] if best else P["niebla"]), text(32, 38, str(win["rank"]), 16, 700, anchor="middle")]
    body += [text(64, 34, f"Siembra en {FULL[win['month']]} {win['year']}", 17, 700), text(64, 56, f"Cosecha estimada {win['harvest']}", 13, fill=SEC)]
    lim = m.SIGNAL_NAME[win["limiting"]].lower()
    if compact:
        body += [text(64, 82, f"Limita: {lim} · {win['limiting_score']}/100", 14, 700), text(64, 100, f"Promedio con los pesos: {win['weighted']}/100", 13, fill=SEC)]
        body += mini_scores(18, 140, win["scores"], 54)
        if win["high_risk"]:
            body += tag(w - 60, 66, "Alto riesgo", P["rojo"], WHITE)
        elif best:
            body += tag(w - 66, 66, "Entre las mejores", P["calabaza"], P["noche"])
    else:
        body += [text(330, 34, f"Lo que más limita: {lim} · {win['limiting_score']}/100", 15, 700)] + sg.score_bar(330, 50, 200, win["limiting_score"], 10, show_number=False)
        body += [text(580, 34, "Promedio con los pesos", 13, fill=SEC), text(580, 60, f"{win['weighted']}/100", 18, 700)]
        body += mini_scores(700, 50, win["scores"])
        if win["high_risk"]:
            body += tag(w - 160, 18, "Alto riesgo: helada crítica", P["rojo"], WHITE)
        body += link(w - 18, 72, "Ver semanas", 14, anchor="end")
    return [group(f"fecha-{win['month'].lower()}-{win['year']}", body, x, y)], h


def legend_box(x, y, w, compact=False):
    lines = (["Ordenadas por lo que más limita cada fecha;", "entre parecidas, por sus prioridades.", "",
              "Según la historia de la zona. No es un", "pronóstico: usted decide."] if compact else
             ["Ordenadas por lo que más limita cada fecha; entre fechas parecidas, por sus prioridades. Las de alto riesgo van al final.",
              "Según la historia de la zona. No es un pronóstico: usted decide."])
    body = [poly(chamfer(0, 0, w, 24 + len(lines) * 21, 10), "#EEF2E4", D["oliva"], 1.5)] + paragraph(16, 28, lines, 14, 21)
    return [group("como-se-ordena", body, x, y)], 24 + len(lines) * 21


def ordered_list(x, y, w, ranked, compact=False):
    """Todas las fechas en el orden del motor; antes de las de alto riesgo, un rótulo que explica por qué van al final."""
    out = [text(0, 0, "Todas las fechas, en orden", 22 if not compact else 20, 600, font=FONT_TITLE)]
    yy = 22
    first_risk = min((v["rank"] for v in ranked if v["high_risk"]), default=None)
    for win in ranked:
        if win["rank"] == first_risk:
            out.append(text(0, yy + 22, "Alto riesgo: van al final y nunca entre las mejores" if not compact else "Alto riesgo: van al final", 15, 700, D["rojo"]))
            yy += 36
        row, rh = window_row(0, yy, w, win, compact)
        out += row
        yy += rh + 10
    return [group("orden-de-fechas", out, x, y)], yy


def best_banner(x, y, w, crop_label, ranked, compact=False):
    best = sorted([r for r in ranked if not r["high_risk"]][:3], key=lambda r: (r["year"], list(FULL).index(r["month"])))
    names = ", ".join(f"{FULL[b['month']]}" for b in best[:-1]) + f" y {FULL[best[-1]['month']]}"
    body = [poly(chamfer(0, 0, w, 84 if compact else 70, 12), "#E9F2D8", D["oliva"], 2)]
    body += [text(18, 28, f"Mejores fechas para sembrar {crop_label}", 14 if compact else 15, 700),
             text(18, 54, names[0].upper() + names[1:] + " de 2027", 18 if compact else 21, 600, font=FONT_TITLE)]
    if compact:
        body.append(text(18, 74, "Según la historia de la zona", 12, fill=SEC))
    else:
        body.append(text(w - 18, 42, "Según la historia de la zona; no es un pronóstico", 13, fill=SEC, anchor="end"))
    return [group("mejores-fechas", body, x, y)], 84 if compact else 70


def plan_desktop(guest=False):
    w = 1440
    chrono, ranked = m.windows()
    b = [f'<rect width="{w}" height="4000" fill="{P["niebla"]}"/>']
    if guest:
        b += topbar(w, active="Consultar")
        b += link(48, 140, "‹ Volver al resultado", 16)
        b += [text(48, 190, "Mejores fechas para la papa", 40, 600, font=FONT_TITLE), text(48, 222, "Samacá, Boyacá · historia de la zona, no es pronóstico", 17, fill=SEC)]
        b += field(48, 258, 280, "Municipio", "Samacá, Boyacá", trailing="▾", name="elegir-municipio")
        b += field(348, 258, 220, "Cultivo", "Papa", trailing="▾", name="elegir-cultivo")
        b += field(588, 258, 200, "¿Tiene riego?", "No", trailing="▾", name="elegir-riego")
        b += sg.priorities_summary(808, 270, w - 48 - 808, m.DEFAULT_WEIGHTS, own=False)
        y = 368
        crop_label = "papa en Samacá"
    else:
        b += topbar(w, active="Mi finca", user=m.NAME)
        b += lot_header(48, 140)
        b += lot_tabs(48, 212, "Calendario")
        b += mode_toggle(48, 280, False)
        chips, cx = crop_chips(500, 282, (("Papa", True), ("Haba", False), ("Cebolla", False)))
        b += chips
        b += sg.priorities_summary(cx + 24, 276, w - 48 - cx - 24, m.DEFAULT_WEIGHTS, own=False)
        b += [text(48, 368, "Para la parte libre de El Alto (0,41 ha) · sin riego", 15, fill=SEC)]
        y = 384
        crop_label = "papa en la parte libre de El Alto"
    bb, bh = best_banner(48, y, w - 96, crop_label, ranked)
    b += bb
    y += bh + 70
    chart_w = w - 96 - 140
    b += card(48, y - 50, w - 96, 300, "tarjeta-ano")
    b += year_chart(48 + 90, y + 20, chart_w - 40, 150, chrono)
    y += 290
    lg, lh = legend_box(48, y, w - 96)
    b += lg
    y += lh + 40
    ol, oh = ordered_list(48, y, w - 96, ranked)
    b += ol
    y += oh + 30
    b.append(text(48, y, f"{m.VERSIONS} · Pesos de AgroSense", 14, fill=SEC))
    b += link(w - 48, y, "¿De dónde salen estos datos?", 15, anchor="end")
    return frame((w, y + 50), b, P["niebla"])


def plan_mobile():
    w = MOBILE[0]
    pad, fw = 16, w - 32
    chrono, ranked = m.windows()
    b = topbar(w) + lot_header(pad, 118, mobile=True)
    tabs = lot_tabs(-98, 0, "Calendario")
    b.append(f'<defs><clipPath id="recorte-pestanas-plan"><rect x="0" y="200" width="{w}" height="60"/></clipPath></defs>'
             f'<g clip-path="url(#recorte-pestanas-plan)"><g transform="translate({pad} 210)">{"".join(tabs)}</g></g>')
    b += mode_toggle(pad, 276, False, fw)
    b += field(pad, 350, fw, "Cultivo", "Papa · parte libre (0,41 ha)", trailing="▾", name="elegir-cultivo")
    b += sg.priorities_summary(pad, 448, fw, m.DEFAULT_WEIGHTS, own=False)
    y = 532
    bb, bh = best_banner(pad, y, fw, "papa", ranked, compact=True)
    b += bb
    y += bh + 30
    b += card(pad, y, fw, 270, "tarjeta-ano")
    b += year_chart(pad + 40, y + 58, fw - 60, 120, chrono, compact=True)
    y += 290
    lg, lh = legend_box(pad, y, fw, compact=True)
    b += lg
    y += lh + 30
    ol, oh = ordered_list(pad, y, fw, ranked, compact=True)
    b += ol
    y += oh + 20
    b.append(text(pad, y, f"{m.VERSIONS} · Pesos de AgroSense", 13, fill=SEC))
    return frame((w, y + 50), b, P["niebla"])


def week_row(x, y, w, wk, i, compact=False):
    scores = wk["scores"]
    counted = {k: v for k, v in scores.items() if v is not None}
    lim = min(counted, key=lambda k: counted[k])
    h = 150 if compact else 84
    body = [poly(chamfer(0, 0, w, h, 10), "#FFF6EA" if i == 0 else WHITE, P["calabaza"] if i == 0 else BORDE, 2.5 if i == 0 else 1.2)]
    body += [text(18, 32, f"Semana del {wk['label']}", 17, 700), text(18, 54, f"Cosecha estimada {wk['harvest']}", 13, fill=SEC)]
    if compact:
        body += [text(18, 80, f"Limita: {m.SIGNAL_NAME[lim].lower()} · {counted[lim]}/100", 14, 700)] + mini_scores(18, 124, scores, 54)
    else:
        body += [text(330, 34, f"Lo que más limita: {m.SIGNAL_NAME[lim].lower()} · {counted[lim]}/100", 15, 700)] + sg.score_bar(330, 50, 200, counted[lim], 10, show_number=False)
        body += mini_scores(600, 50, scores)
        if i == 0:
            body += link(w - 18, 70, "Ver el diagnóstico de esta semana", 14, anchor="end")
    return [group(f"semana-{i + 1}", body, x, y)], h


def weeks(mobile=False):
    """Agosto de 2027 abierto: sus semanas. Afinan dentro de un mes; el dato semanal es más variable."""
    w = MOBILE[0] if mobile else 1440
    pad = 16 if mobile else 48
    fw = w - 2 * pad
    b = [f'<rect width="{w}" height="3000" fill="{P["niebla"]}"/>']
    b += topbar(w) if mobile else topbar(w, active="Mi finca", user=m.NAME)
    b += link(pad, 118 if mobile else 140, "‹ Todas las fechas", 16)
    if mobile:
        b += [text(pad, 160, "Agosto de 2027, por semana", 23, 600, font=FONT_TITLE), text(pad, 186, "Papa · parte libre de El Alto · sin riego", 14, fill=SEC)]
        y = 212
    else:
        b += [text(pad, 190, "Agosto de 2027, semana por semana", 36, 600, font=FONT_TITLE),
              text(pad, 222, "Papa · parte libre de El Alto (0,41 ha) · sin riego · pesos de AgroSense", 16, fill=SEC)]
        y = 250
    note = (["Las semanas afinan dentro de un mes: el", "dato por semana es más variable que el", "del mes. Mientras más tarde siembre en", "agosto, más se acerca el llenado a las", "heladas de enero."] if mobile else
            ["Las semanas afinan dentro de un mes: el dato por semana es más variable que el del mes.",
             "Mientras más tarde siembre en agosto, más se acerca el llenado de la papa a las heladas de enero."])
    nh = 24 + len(note) * 21
    b += [poly(chamfer(pad, y, fw, nh, 10), "#E6F0F5", D["cielo"], 1.5)] + paragraph(pad + 16, y + 28, note, 14, 21)
    y += nh + 24
    for i, wk in enumerate(m.AUG_WEEKS):
        row, rh = week_row(pad, y, fw, wk, i, compact=mobile)
        b += row
        y += rh + 10
    y += 14
    b.append(text(pad, y, "Según la historia de la zona. No es un pronóstico: usted decide.", 13 if mobile else 14, fill=SEC))
    return frame((w, y + 50), b, P["niebla"])


SCREENS = {
    "finca-03-calendario-planear-escritorio": lambda: plan_desktop(),
    "finca-03-calendario-planear-movil": plan_mobile,
    "finca-03-calendario-semanas-escritorio": lambda: weeks(),
    "finca-03-calendario-semanas-movil": lambda: weeks(mobile=True),
    "consulta-04-calendario-sin-cuenta-escritorio": lambda: plan_desktop(guest=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
