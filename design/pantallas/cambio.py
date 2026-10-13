"""Tanda 11 · «Qué cambió en su zona» (HU-219). Escritorio, móvil y el cultivo que no se da en la zona.

Compara dos periodos de la historia del municipio (GET /changes, `specs/01-reglas.md`, «Qué cambió en la zona»):
por mes, la frecuencia de heladas, la lluvia normal y la temperatura máxima, y cómo se movieron las mejores fechas
de siembra del cultivo. **Es historia comparada, nunca pronóstico:** el rótulo «Así fue en la historia de su zona.
No es un pronóstico» va fijo arriba.

- Los dos periodos de una comparación son de la misma fuente. Las heladas y el calor salen de NASA POWER
  (1981–2000 y 2005–2024). Si la lluvia sale de GPM IMERG, sus datos empiezan en 2000 y sus periodos son más cortos
  (2001–2012 y 2013–2024): la pantalla lo dice junto a la gráfica.
- NASA POWER es un reanálisis (un modelo con observaciones), no una observación directa: se dice (R8).
- Un valor sin datos suficientes se ve «Sin datos suficientes», con forma y texto, nunca como un cambio de cero (R1).
- Las mejores fechas de cada periodo usan el mismo orden de ventanas y los pesos de AgroSense. Solo cambia el clima:
  la oferta, el mercado y el suelo son los mismos en los dos periodos, y se dice.
- Si el cultivo no se da en la zona, lo dice con su razón y muestra solo el clima.

Se llega desde el resultado del diagnóstico, desde el ciclo de una estrategia (ciclo.py) y desde el lote, con el
municipio y el cultivo ya elegidos. Qué hace cada control: «Cambiar» abre el selector de cultivo o de municipio;
«Ver las fechas de hoy» abre el calendario del cultivo; «Volver» regresa a donde se vino; «¿De dónde sale esto?»
abre «¿Cómo funciona?». Los nombres y las cifras son de muestra.

    python design/pantallas/cambio.py     # escribe svg/cambio-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402
import muestra as m  # noqa: E402
import senales as sg  # noqa: E402
from diagnostico import limits_box, wrap  # noqa: E402
from estrategias import context_rows, label_strip  # noqa: E402
from ui import (BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, frame, group, link, mascot,  # noqa: E402
                paragraph, poly, scene, text, topbar)

NOT_FORECAST = "Así fue en la historia de su zona. No es un pronóstico."
BEFORE, AFTER = "1981–2000", "2005–2024"
BEFORE_RAIN, AFTER_RAIN = "2001–2012", "2013–2024"
MONTHS = "EFMAMJJASOND"
NAMES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")

# Cifras de muestra, de enero a diciembre. `None`: ese periodo no tiene datos suficientes en ese mes.
FROST = ((30, 22, 8, 2, 0, 1, 4, 6, 3, 1, 3, 16), m.FROST)                                    # % de años con helada
RAIN = ((28, 45, 80, 120, 105, 60, 50, 48, 70, 125, 110, 50), (35, 48, 74, 112, 110, 55, 44, 50, 78, 118, 116, 58))  # mm
TMAX = ((None, 20.6, 20.9, 20.7, 20.4, 19.9, 19.6, 20.0, 20.5, 20.4, 20.1, 20.2), (21.4, 21.3, 21.6, 21.2, 20.9, 20.3, 20.0, 20.5, 21.0, 20.8, 20.6, 20.9))  # °C

# Mejores meses de siembra de la papa en cada periodo (`best_windows`): mes, lo que más limita y su nota.
BEST = {BEFORE: (("Marzo", "heladas", 64), ("Agosto", "heladas", 55), ("Abril", "agua", 52)),
        AFTER: (("Marzo", "agua", 80), ("Abril", "heladas", 72), ("Febrero", "agua", 70))}
REASONS = ["Entre 1981 y 2000 heló en enero en 30 de cada 100 años; entre 2005 y 2024, en 22.",
           "En marzo y abril hiela menos que antes: por eso sembrar en esos meses limita menos hoy.",
           "La temperatura máxima subió cerca de medio grado en casi todos los meses."]
LIMITS = ["NASA POWER es un reanálisis (un modelo con observaciones), no una observación directa.",
          "La oferta, el mercado y el suelo son los mismos en los dos periodos: solo cambia el clima.",
          "Comparado sin riego, como usted indicó.", "Los datos son de la zona (celdas de kilómetros), no de su lote."]


def fmt(v, digits=0):
    return (f"{v:.{digits}f}" if digits else f"{v:g}").replace(".", ",")


def nodata(x, y, w, h):
    """«Sin datos suficientes» en una gráfica: un hueco punteado con su signo, nunca una barra en cero (R1)."""
    return [poly(chamfer(x, y, w, h, 2), WHITE, D["cielo"], 1.5, "3 3"), text(x + w / 2, y + h / 2 + 5, "?", 13, 700, D["cielo"], anchor="middle")]


def compare_chart(x, y, w, title, unit, series, labels, source, fill, stroke, vmin=0, vmax=None, digits=0, note=None, mobile=False):
    """Doce meses, dos barras por mes: el periodo de antes (rayado) y el de después (lleno), con su unidad y su fuente."""
    before, after = series
    known = [v for s in series for v in s if v is not None]
    vmax = vmax or max(known) * 1.15
    ch, top, left = (150, 96, 44) if mobile else (180, 92, 60)
    cw = w - left - 20
    h = top + ch + (118 if mobile else 96) + (38 if note else 0)
    b = [poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE)]
    b += [text(20, 36, title, 19 if mobile else 21, 600, font=FONT_TITLE), text(20, 58, unit, 13, 700, SEC)]
    pid = f"rayado-{title.split()[0].lower()}" + ("-m" if mobile else "")
    b.append(f'<defs><pattern id="{pid}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="{WHITE}"/>'
             f'<rect width="2.5" height="6" fill="{stroke}"/></pattern></defs>')
    Y = lambda v: top + ch - ch * (v - vmin) / (vmax - vmin)  # noqa: E731
    for t in (0.5, 1.0):
        v = vmin + (vmax - vmin) * t
        b += [f'<rect x="{left}" y="{Y(v):.1f}" width="{cw}" height="1" fill="{BORDE}"/>', text(left - 8, Y(v) + 4, fmt(v, digits), 12, fill=SEC, anchor="end")]
    gw = cw / 12
    bw = gw * 0.34
    missing = False
    for i in range(12):
        gx = left + i * gw + (gw - 2 * bw - 3) / 2
        for k, (value, style) in enumerate(((before[i], f"url(#{pid})"), (after[i], fill))):
            bx = gx + k * (bw + 3)
            if value is None:
                b += nodata(bx, top + ch - 46, bw, 46)
                missing = True
            else:
                bh = max(2, top + ch - Y(value))
                b.append(poly(chamfer(bx, top + ch - bh, bw, bh, 2), style, stroke, 1.5))
        b.append(text(left + i * gw + gw / 2, top + ch + 20, MONTHS[i], 12, fill=SEC, anchor="middle"))
    b.append(f'<rect x="{left}" y="{top + ch}" width="{cw}" height="2" fill="{P["noche"]}"/>')
    ly = top + ch + 46
    b += [poly(chamfer(20, ly - 12, 22, 14, 2), f"url(#{pid})", stroke, 1.5), text(50, ly, f"Entre {labels[0].replace('–', ' y ')}", 13, 700)]
    lx = 20 if mobile else 250
    ly2 = ly + 22 if mobile else ly
    b += [poly(chamfer(lx, ly2 - 12, 22, 14, 2), fill, stroke, 1.5), text(lx + 30, ly2, f"Entre {labels[1].replace('–', ' y ')}", 13, 700)]
    if missing:
        my = ly2 + 22
        b += nodata(20, my - 13, 16, 16) + [text(44, my, "Sin datos suficientes en ese mes y periodo", 13, 700, D["cielo"])]
    sy = ly2 + (44 if missing else 22) + (0 if mobile else 4)
    b.append(text(20, sy, f"Fuente: {source}", 12, fill=SEC))
    if note:
        rows = wrap(note, 44 if mobile else 130)
        b += [poly(chamfer(20, sy + 12, w - 40, 14 + len(rows) * 18, 8), "#E6F0F5", D["cielo"], 1.5)] + paragraph(32, sy + 31, rows, 13, 18, weight=700)
        h = sy + 12 + 14 + len(rows) * 18 + 20
    else:
        h = sy + 22
    b[0], b[1] = poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE)
    return [group("grafica-" + title.split()[0].lower(), b, x, y)], h + 8


def windows_column(x, y, w, period, items, highlight=False):
    """Las mejores fechas de un periodo: hasta tres meses de siembra, con lo que más limita cada uno."""
    h = 70 + max(1, len(items)) * 62
    b = [poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE, P["calabaza"] if highlight else None, 3 if highlight else 0)]
    b += [text(20, 36, f"Entre {period.replace('–', ' y ')}", 20, 600, font=FONT_TITLE), text(w - 20, 36, "lo de ahora" if highlight else "antes", 13, 700, SEC, anchor="end")]
    for i, (month, limiting, score) in enumerate(items):
        ry = 58 + i * 62
        b += [f'<rect x="20" y="{ry}" width="{w - 40}" height="1" fill="{BORDE}"/>',
              poly([(34, ry + 16), (48, ry + 30), (34, ry + 44), (20, ry + 30)], P["calabaza"] if i == 0 else P["niebla"], P["noche"], 2), text(34, ry + 36, f"{i + 1}", 15, 700, anchor="middle"),
              text(62, ry + 28, f"Sembrar en {month.lower()}", 17, 700), text(62, ry + 48, f"limita: {limiting}", 13, fill=SEC)]
        bar_w = 84 if w < 420 else 130
        b += sg.score_bar(w - 20 - bar_w, ry + 30, bar_w, score, 10)
    return [group("mejores-fechas-" + period[:4], b, x, y)], h + 8


def changes(mobile=False, unsuitable=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    crop, town = ("papa", "Puerto Boyacá, Boyacá") if unsuitable else ("papa", m.TOWN)
    short_town = town.split(",")[0]
    header_h = 560 if mobile else 440
    tagname = ("-m" if mobile else "") + ("-n" if unsuitable else "")
    b = scene("a3-region", w, header_h, "recorte-cambio" + tagname, 0.12)
    b += topbar(w, "Consultar")
    x, y, cw, pad = (12, 92, 366, 20) if mobile else (96, 116, 900, 36)
    fw = cw - 2 * pad
    c = link(pad, 40, "‹ Volver", 15)
    c.append(text(pad, 76, f"QUÉ CAMBIÓ · {crop.upper()} · {short_town.upper()}" if mobile else f"QUÉ CAMBIÓ · {crop.upper()} · {town.upper()}", 13 if mobile else 14, 700, SEC))
    c += paragraph(pad, 116, ["¿Qué cambió", "en su zona?"] if mobile else ["¿Qué cambió en su zona?"], 28 if mobile else 38, 34, weight=600, font=FONT_TITLE)
    yy = 116 + (34 if mobile else 0) + 20
    lb, lh = label_strip(pad, yy, fw, wrap(NOT_FORECAST, 36) if mobile else [NOT_FORECAST])
    c += lb
    yy += lh + 16
    intro = (["Dos periodos de la historia de su municipio,", "lado a lado: heladas, lluvia y calor, y", "cómo se movieron las mejores fechas."] if mobile else
             ["Dos periodos de la historia de su municipio, lado a lado: heladas, lluvia y calor de cada mes,", "y cómo se movieron las mejores fechas de siembra."])
    c += paragraph(pad, yy + 6, intro, 16, 23)
    yy += len(intro) * 23 + 16
    rows = (("Cultivo", "Papa", "Cambiar"), ("Municipio", town, "Cambiar"), ("Riego", "Sin riego", "Cambiar"))
    cr, crh = context_rows(pad, yy, fw if mobile else 420, rows)
    c += cr
    ch = yy + crh + 14
    b += card(x, y, cw, ch) + [group("encabezado", c, x, y)]
    if not mobile:
        b += mascot(1090, 130, 0.95, "guia")
    top = max(header_h, y + ch + 40)
    pad2 = 16 if mobile else 96
    iw = w - 2 * pad2
    s, yy = [], 20
    # 1. Las mejores fechas, lado a lado
    s.append(text(pad2, yy + 26, "Las mejores fechas de siembra" if mobile else f"Las mejores fechas para sembrar {crop}, antes y ahora", 24 if mobile else 32, 600, font=FONT_TITLE))
    if unsuitable:
        ns = m.NOT_SUITABLE
        yy += 50
        if mobile:
            box = [poly(chamfer(0, 0, iw, 150, 12), WHITE, P["noche"], 3), poly([(28, 20), (52, 20), (62, 38), (40, 64), (18, 38)], P["niebla"], P["noche"], 2.5),
                   f'<path d="M26 28 l28 28 M54 28 l-28 28" stroke="{P["noche"]}" stroke-width="3"/>', text(78, 36, "La papa no se da", 19, 600, font=FONT_TITLE),
                   text(78, 60, "en Puerto Boyacá", 19, 600, font=FONT_TITLE)]
            box += paragraph(16, 96, ["Está a 125 m; la papa se da entre", "2.000 y 3.500 m. Fuente: ficha del cultivo."], 14, 20)
            s.append(group("no-se-da-en-su-zona", box, pad2, yy))
            yy += 166
        else:
            sign, sh = sg.not_suitable_sign(pad2, yy, iw, ns["crop"], ns["town"], ns["score"], ns["reason"], ns["source"])
            s += sign
            yy += sh + 16
        note = wrap("Por eso no hay fechas que comparar: evaluarlas sería inventar un resultado. Abajo está solo el clima de su zona.", 40 if mobile else 130)
        s += paragraph(pad2, yy + 8, note, 15, 21)
        yy += len(note) * 21 + 14
        s += link(pad2, yy + 8, "Elegir otro cultivo", 15)
        yy += 40
    else:
        sub = (["Con los pesos de AgroSense. Solo cambia", "el clima entre un periodo y otro."] if mobile else
               ["Con el mismo orden de ventanas y los pesos de AgroSense. Entre un periodo y otro solo cambia el clima: la oferta, el mercado y el suelo son los mismos."])
        s += paragraph(pad2, yy + 54, sub, 15, 21, fill=SEC)
        yy += 54 + len(sub) * 21 + 6
        if mobile:
            for period in (BEFORE, AFTER):
                wc, wh = windows_column(pad2, yy, iw, period, BEST[period], period == AFTER)
                s += wc
                yy += wh + 16
        else:
            half = (iw - 24) / 2
            wc, wh = windows_column(pad2, yy, half, BEFORE, BEST[BEFORE])
            s += wc
            wc2, wh2 = windows_column(pad2 + half + 24, yy, half, AFTER, BEST[AFTER], True)
            s += wc2
            yy += max(wh, wh2) + 16
        s += link(pad2, yy + 10, "Ver las fechas de hoy en el calendario de la papa", 15)
        yy += 44
    # 2. El clima, mes a mes
    s.append(text(pad2, yy + 36, "El clima, mes a mes", 24 if mobile else 32, 600, font=FONT_TITLE))
    s += paragraph(pad2, yy + 64, ["Cada gráfica con su unidad, sus años y", "su fuente. Nunca se mezclan fuentes."] if mobile else
                   ["Cada gráfica con su unidad, los años de cada periodo y su fuente. Los dos periodos de una gráfica son siempre de la misma fuente."], 15, 21, fill=SEC)
    yy += 64 + (2 if mobile else 1) * 21 + 10
    power = "NASA POWER · reanálisis (un modelo con observaciones), no una medición directa"
    charts = (
        ("Heladas", "% de años con al menos una helada (mínima menor que 2 °C)" if not mobile else "% de años con helada", FROST, (BEFORE, AFTER), power, P["cielo"], D["cielo"], 0, 36, 0, None),
        ("Lluvia", "mm de lluvia normal en el mes", RAIN, (BEFORE_RAIN, AFTER_RAIN), "GPM IMERG · lluvia por satélite", P["brote"], D["brote"], 0, 140, 0,
         "Los datos de lluvia por satélite (IMERG) empiezan en 2000: por eso sus periodos son más cortos que los de las heladas y el calor."),
        ("Temperatura máxima", "°C que se superan uno de cada diez días", TMAX, (BEFORE, AFTER), power, P["calabaza"], D["calabaza"], 18, 22.5, 1, None),
    )
    if mobile:
        for title, unit, series, labels, source, fill, stroke, vmin, vmax, digits, note in charts:
            cc, chh = compare_chart(pad2, yy, iw, title, unit, series, labels, source if len(source) < 46 else source.split(" (")[0], fill, stroke, vmin, vmax, digits, note, True)
            s += cc
            yy += chh + 16
    else:
        half = (iw - 24) / 2
        c1, h1 = compare_chart(pad2, yy, half, *charts[0][:2], charts[0][2], charts[0][3], charts[0][4], *charts[0][5:10])
        c3, h3 = compare_chart(pad2 + half + 24, yy, half, *charts[2][:2], charts[2][2], charts[2][3], charts[2][4], *charts[2][5:10])
        s += c1 + c3
        yy += max(h1, h3) + 20
        c2, h2 = compare_chart(pad2, yy, iw, *charts[1][:2], charts[1][2], charts[1][3], charts[1][4], *charts[1][5:10], note=charts[1][10])
        s += c2
        yy += h2 + 20
    # 3. Lo que se ve en los datos
    rb = [poly(chamfer(0, 8, iw, 10, 16), BORDE), poly(chamfer(0, 0, iw, 10, 16), WHITE), text(24, 40, "Lo que se ve en estos datos", 20, 600, font=FONT_TITLE)]
    ry = 70
    for r in (REASONS[:1] + REASONS[2:] if unsuitable else REASONS):
        rows = wrap("· " + r, 40 if mobile else 130)
        rb += paragraph(24, ry, rows, 15, 21)
        ry += len(rows) * 21 + 6
    rb[0], rb[1] = poly(chamfer(0, 8, iw, ry + 6, 16), BORDE), poly(chamfer(0, 0, iw, ry + 6, 16), WHITE)
    s.append(group("razones", rb, pad2, yy))
    yy += ry + 36
    lim = LIMITS if not unsuitable else LIMITS[:1] + LIMITS[3:]
    lb2, lh2 = limits_box(pad2, yy, iw, lim, mobile)
    s += lb2
    yy += lh2 + 24
    nb, nh = label_strip(pad2, yy, iw, wrap(NOT_FORECAST, 38) if mobile else [NOT_FORECAST])
    s += nb
    vy = yy + nh + 40
    s.append(text(pad2, vy, f"{m.VERSIONS} · Cifras de muestra", 15, fill=SEC))
    s += link(pad2 if mobile else w - pad2, vy + (30 if mobile else 0), "¿Cómo funciona y de dónde sale esto?", 15, anchor="start" if mobile else "end")
    h = top + vy + 70
    b = [f'<rect y="{header_h}" width="{w}" height="{h - header_h}" fill="{P["niebla"]}"/>'] + b + [group("comparacion", s, 0, top)]
    foot, fh = ui.footer(w, h, mobile, above=P["niebla"])
    return frame((w, h + fh), b + foot)


SCREENS = {
    "cambio-01-que-cambio-escritorio": lambda: changes(),
    "cambio-01-que-cambio-movil": lambda: changes(mobile=True),
    "cambio-02-no-se-da-en-la-zona-escritorio": lambda: changes(unsuitable=True),
    "cambio-02-no-se-da-en-la-zona-movil": lambda: changes(mobile=True, unsuitable=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
