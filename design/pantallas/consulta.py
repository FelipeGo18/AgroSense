"""Pantallas finales de la Consulta (tanda 3): elegir cultivo y semestre, resultado del diagnóstico y las cinco señales.

EP-09 (HU-091 a HU-094) con las cinco señales de `specs/01-reglas.md`: lluvia, heladas, suelo, oferta y mercado.
Cada botón lleva a algo que existe: el diagnóstico (POST /diagnostics), el calendario (HU-180), las rotaciones
(tanda 4), el detalle de señales, el panel «¿Cómo funciona?» o volver a elegir. Las cifras son de muestra.

    python design/pantallas/consulta.py     # escribe svg/consulta-*.svg
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401  (agrega design/kit y design/mascota al camino de importación)
import muestra  # noqa: E402
from build_kit_svg import LIGHTS, STATUS, facets, icon, kind_icon, sign  # noqa: E402
from ui import (BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, frame, group, inner, link,  # noqa: E402
                mascot, paragraph, poly, scene, shade, text, topbar, width_of)

CROP, TOWN, SEM = "papa", "Samacá, Boyacá", "B · jul–dic 2026"

# ---------- Piezas ----------

TAGS = {  # forma + texto + color, nunca solo color (W2, R1)
    "favorable": ("Favorable", "octagon"),
    "moderado": ("Moderado", "triangle"),
    "desfavorable": ("Desfavorable", "square"),
    "insuficiente": ("Sin datos", None),
    "no-aplica": ("No aplica", None),
}


def tag(x, y, status, w=176, h=38, critical=False):
    label, shape = TAGS[status]
    if status == "no-aplica":
        body = [poly(chamfer(0, 0, w, h, 8), WHITE, D["cielo"], 2.5), f'<rect x="14" y="{h / 2 - 2:g}" width="16" height="4" fill="{D["cielo"]}"/>']
        ink = P["noche"]
    elif status == "insuficiente":
        body = [poly(chamfer(0, 0, w, h, 8), WHITE, D["cielo"], 2.5, "3 5"),
                text(22, h / 2 + 6, "?", 18, 700, D["cielo"], anchor="middle")]
        ink = P["noche"]
    else:
        st = STATUS[status]
        c = 0 if status == "desfavorable" else 8
        body = [poly(chamfer(0, 0, w, h, c), st["fill"])] + facets(0, 0, w, h, c, st["fill"]) + [poly(chamfer(0, 0, w, h, c), "none", st["stroke"], 2.5)]
        body += icon(shape, 12, h / 2 - 8, st["ink"], 16)
        ink = st["ink"]
    body.append(text(38, h / 2 + 6, label, 16, 700, ink))
    if critical:
        body += [poly(chamfer(w + 8, 4, 74, h - 8, 4), WHITE, P["rojo"], 2), text(w + 45, h / 2 + 5, "Crítica", 14, 700, P["rojo"], anchor="middle")]
    return [group(f"estado-{status}", body, x, y)]


def kind(k, x, y):
    if k == "lluvia":
        return kind_icon("clima", x, y)
    if k == "oferta":
        return kind_icon("oferta", x, y)
    if k == "mercado":
        return kind_icon("mercado", x, y)
    if k == "heladas":  # cristal de hielo facetado
        cx, cy, out = x + 22, y + 22, []
        for i in range(6):
            a = math.radians(60 * i - 90)
            tip = (cx + 20 * math.cos(a), cy + 20 * math.sin(a))
            left = (cx + 7 * math.cos(a - 0.5), cy + 7 * math.sin(a - 0.5))
            right = (cx + 7 * math.cos(a + 0.5), cy + 7 * math.sin(a + 0.5))
            out.append(poly([(cx, cy), left, tip], P["niebla"], D["cielo"], 1.5))
            out.append(poly([(cx, cy), tip, right], shade(P["niebla"], -0.12)))
        return out
    if k == "suelo":  # terrón con capas
        return [poly([(x + 4, y + 16), (x + 40, y + 16), (x + 42, y + 24), (x + 2, y + 24)], P["brote"], D["brote"], 1.5),
                poly([(x + 2, y + 24), (x + 42, y + 24), (x + 40, y + 33), (x + 4, y + 33)], P["tierra"]),
                poly([(x + 4, y + 33), (x + 40, y + 33), (x + 36, y + 42), (x + 8, y + 42)], D["tierra"]),
                poly([(x + 12, y + 27), (x + 18, y + 27), (x + 16, y + 30)], shade(P["tierra"], 0.25)),
                poly([(x + 28, y + 36), (x + 34, y + 36), (x + 31, y + 39)], shade(D["tierra"], 0.3))]
    return []


def mist(w, h):
    """Bruma de «sin datos»: nubes de niebla, nunca color de riesgo (R1)."""
    out = []
    for cx, cy, k in ((w * 0.7, h - 40, 0.9), (w * 0.3, h - 26, 0.7)):
        cloud = [(cx - 90 * k, cy + 16 * k), (cx - 66 * k, cy - 8 * k), (cx - 24 * k, cy - 22 * k), (cx + 18 * k, cy - 26 * k),
                 (cx + 62 * k, cy - 10 * k), (cx + 90 * k, cy + 10 * k), (cx + 76 * k, cy + 20 * k)]
        out.append(poly(cloud, P["niebla"]))
    return out


def light(key, x, y, scale):
    return [f'<g id="semaforo" transform="translate({x:g} {y:g}) scale({scale:g})">{inner(sign(key))}</g>']


# ---------- Datos de muestra ----------

SIGNALS = {
    "amarillo": [
        ("lluvia", "Lluvia", "favorable", False, ["En 7 de los últimos 10", "semestres B la lluvia fue", "favorable para la papa."]),
        ("heladas", "Heladas", "moderado", False, ["Sembrando en agosto,", "heló en el llenado (dic)", f"{muestra.FROST[11]} de cada 100 años."]),
        ("suelo", "Suelo", "favorable", False, ["pH estimado 5,2 a 5,8:", "apto para la papa.", "Estimación de 250 m."]),
        ("oferta", "Oferta", "desfavorable", False, ["En 2025 B se sembró 35 %", "más papa que en los tres", "semestres B anteriores."]),
        ("mercado", "Mercado", "insuficiente", False, ["Sin datos de precios", "para Samacá. No cambia", "el semáforo."]),
    ],
    # El caso rojo es de otro municipio, más alto y frío: en Samacá la helada no llega a crítica sembrando en el mejor mes.
    "rojo": [
        ("lluvia", "Lluvia", "favorable", False, ["En 8 de los últimos 10", "semestres A la lluvia fue", "favorable para la papa."]),
        ("heladas", "Heladas", "desfavorable", True, ["Aun sembrando en marzo,", "heló en la floración", "4 de cada 10 años."]),
        ("suelo", "Suelo", "favorable", False, ["pH estimado 5,3 a 5,9:", "apto para la papa.", "Estimación de 250 m."]),
        ("oferta", "Oferta", "favorable", False, ["En 2025 A, área sembrada", "parecida a los tres", "semestres A anteriores."]),
        ("mercado", "Mercado", "insuficiente", False, ["Sin datos de precios", "para Toca. No cambia", "el semáforo."]),
    ],
    "no-evaluable": [
        ("lluvia", "Lluvia", "favorable", False, ["En 7 de los últimos 10", "semestres B la lluvia fue", "favorable para el haba."]),
        ("heladas", "Heladas", "no-aplica", False, ["La ficha del cultivo", "no tiene etapas", "sensibles a la helada."]),
        ("suelo", "Suelo", "moderado", False, ["pH estimado 5,2 a 5,8:", "en el límite de lo", "que tolera."]),
        ("oferta", "Oferta", "insuficiente", False, ["EVA no registra este", "cultivo en Samacá en", "los últimos semestres."]),
        ("mercado", "Mercado", "insuficiente", False, ["Sin datos de precios", "para Samacá. No cambia", "el semáforo."]),
    ],
}

HEAD = {
    "amarillo": dict(kicker=f"PAPA · SEMESTRE {SEM.upper()} · {TOWN.upper()}", title="Mejor espere otro semestre", mood="guia",
                     reasons=["En 2025 B, el último dato, se sembró 35 % más papa que antes en Samacá.",
                              "La lluvia ha sido favorable y el suelo es apto; las heladas, moderadas."],
                     primary="Ver el calendario de la papa", secondary="¿Qué sembrar en su lugar?"),
    "rojo": dict(kicker="PAPA · SEMESTRE A · ENE–JUN 2027 · TOCA, BOYACÁ", title="Alto riesgo: espere otro semestre", mood="preocupa",
                 reasons=["En Toca ha helado en la floración aun sembrando en marzo, el mejor mes.",
                          "Una señal crítica basta para el rojo, aunque las demás sean buenas."],
                 primary="Ver el calendario de la papa", secondary="¿Qué sembrar en su lugar?"),
    "no-evaluable": dict(kicker="HABA · SEMESTRE B · JUL–DIC 2026 · SAMACÁ, BOYACÁ", title="No se puede evaluar todavía", mood="sin-datos",
                         reasons=["Faltan datos de oferta: EVA no registra haba en Samacá.",
                                  "Sin lluvia u oferta no damos un semáforo: no inventamos datos."],
                         primary="Elegir otro cultivo", secondary="¿Por qué faltan datos?"),
}

LIMITS = {
    "amarillo": ["Los datos de EVA de 2025 son preliminares.", "El suelo es el estimado para el municipio, no para su lote.",
                 "Sin datos de mercado: el precio no se evaluó."],
    "rojo": ["El suelo es el estimado para el municipio, no para su lote.", "Sin datos de mercado: el precio no se evaluó."],
    "no-evaluable": ["Sin datos de oferta para haba en Samacá.", "Sin datos de mercado: el precio no se evaluó."],
}


# ---------- Tarjeta de señal ----------

def signal_card(x, y, w, h, k, title, status, critical, rows, compact=False):
    insufficient = status == "insuficiente"
    body = [poly(chamfer(0, 6, w, h, 14), BORDE), poly(chamfer(0, 0, w, h, 14), WHITE, D["cielo"] if insufficient else None, 2.5 if insufficient else 0,
                                                      "3 5" if insufficient else None)]
    if insufficient:
        body += mist(w, h)
    body += kind(k, w - 62, 16)
    body.append(text(20, 42, title, 22, 600, font=FONT_TITLE))
    if compact:  # móvil: el estado a la derecha del título y dos líneas de razón
        body += tag(20, 58, status, 150, 34, critical)
        body += paragraph(20, 118, rows, 15, 21)
        body += link(w - 20, h - 18, "Ver detalle", 15, anchor="end")
    else:
        body += tag(20, 64, status, w - 40, 38)
        if critical:
            body += [poly(chamfer(20, 110, 84, 28, 4), WHITE, P["rojo"], 2), text(62, 129, "Crítica", 14, 700, P["rojo"], anchor="middle")]
        body += paragraph(20, 164 if critical else 134, rows, 15, 21)
        body += link(20, h - 22, "Ver detalle", 15)
    return [group(f"senal-{k}", body, x, y)]


# ---------- Elegir cultivo y semestre ----------

CROPS = ("Papa", "Arveja", "Haba", "Maíz", "Zanahoria", "Cebolla")


def choose(mobile=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    h = 960 if mobile else DESKTOP[1]
    b = scene("a5-municipio", w, h, "recorte-elegir" + ("-m" if mobile else ""), 0.1)
    b += topbar(w, "Consultar", None if mobile else "Rosa")
    x, y, cw, pad = (12, 92, 366, 22) if mobile else (96, 120, 620, 36)
    fw = cw - 2 * pad
    c = [text(pad, 50, "CONSULTA", 15, 700, SEC), text(pad, 92, "¿Qué quiere sembrar?", 28 if mobile else 38, 600, font=FONT_TITLE)]
    # municipio elegido en el descenso
    c += [poly(chamfer(pad, 112, fw, 48, 10), P["niebla"]), poly([(pad + 22, 124), (pad + 30, 136), (pad + 22, 148), (pad + 14, 136)], D["brote"]),
          text(pad + 42, 143, TOWN, 18, 700)] + link(pad + fw - 16, 143, "Cambiar", 16, anchor="end")
    c.append(text(pad, 198, "Cultivo", 18, 700))
    cols = 2 if mobile else 3
    chip_w, chip_h = (fw - (cols - 1) * 12) / cols, 52
    for i, crop in enumerate(CROPS):
        cx, cy = pad + (i % cols) * (chip_w + 12), 212 + (i // cols) * (chip_h + 12)
        on = crop == "Papa"
        c += [poly(chamfer(cx, cy, chip_w, chip_h, 10), "#E3EECF" if on else WHITE, D["oliva"] if on else BORDE, 3 if on else 2)]
        if on:
            c.append(poly([(cx + 22, cy + 16), (cx + 30, cy + 26), (cx + 22, cy + 36), (cx + 14, cy + 26)], D["brote"]))
        c.append(text(cx + (40 if on else 20), cy + 33, crop, 18, 700 if on else 400))
    rows = math.ceil(len(CROPS) / cols)
    sy = 212 + rows * (chip_h + 12) + 4
    c += paragraph(pad, sy + 6, ["Solo cultivos con datos en Samacá."], 15, fill=SEC)
    c.append(text(pad, sy + 50, "Semestre", 18, 700))
    opts = (("B · jul–dic 2026", "En curso", True), ("A · ene–jun 2027", "El próximo", False))
    ow = fw if mobile else (fw - 12) / 2
    for i, (label, note, on) in enumerate(opts):
        ox, oy = (pad, sy + 64 + i * 80) if mobile else (pad + i * (ow + 12), sy + 64)
        c += [poly(chamfer(ox, oy, ow, 68, 10), "#E3EECF" if on else WHITE, D["oliva"] if on else BORDE, 3 if on else 2),
              text(ox + 20, oy + 30, label, 18, 700), text(ox + 20, oy + 54, note, 15, fill=SEC)]
    by = sy + 64 + (2 * 80 if mobile else 92)
    c += button(pad, by, fw, "Ver diagnóstico")
    c += paragraph(pad, by + 96, ["¿Ya sembró y quiere saber qué sigue?"], 16, fill=SEC)
    c += link(pad, by + 124, "Ver qué sembrar después", 16)
    ch = by + 150
    b += card(x, y, cw, ch) + [group("contenido", c, x, y)]
    if not mobile:
        b += mascot(860, 220, 1.3, "guia", "germinada")
    return frame((w, h), b)


# ---------- Resultado ----------

def result(variant="amarillo", mobile=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    hd, sg, lim = HEAD[variant], SIGNALS[variant], LIMITS[variant]
    key = {"amarillo": "amarillo", "rojo": "rojo", "no-evaluable": "no-evaluable"}[variant]
    header_h = 560 if mobile else 440
    b = scene("a5-municipio", w, header_h, f"recorte-resultado-{variant}" + ("-m" if mobile else ""), 0.12)
    b += topbar(w, "Consultar", None if mobile else "Rosa")
    # Tarjeta principal: la acción primero (HU-092)
    if mobile:
        x, y, cw, pad = 12, 92, 366, 22
    else:
        x, y, cw, pad = 96, 116, 820, 36
    fw = cw - 2 * pad
    c = [text(pad, 44, hd["kicker"] if not mobile else hd["kicker"].split(" · ")[0] + " · " + hd["kicker"].split(" · ")[1], 14, 700, SEC)]
    sx, sy, ss = (pad, 62, 0.42) if mobile else (pad, 64, 0.5)
    c += light(key, sx, sy, ss)
    tx = pad + (150 if mobile else 180)
    title = hd["title"]
    if mobile:
        words = title.split(" ")
        cut = len(words) // 2
        c += [text(pad, 150, " ".join(words[:cut]), 26, 600, font=FONT_TITLE), text(pad, 182, " ".join(words[cut:]), 26, 600, font=FONT_TITLE)]
        ry = 214
        rows = []
        for r in hd["reasons"]:
            line = ""
            for word in r.split(" "):
                if width_of(line + " " + word, 16) > fw:
                    rows.append(line.strip())
                    line = ""
                line += " " + word
            rows.append(line.strip())
        c += paragraph(pad, ry, rows, 16, 23)
        by = ry + len(rows) * 23 + 10
        c += button(pad, by, fw, hd["primary"]) + button(pad, by + 68, fw, hd["secondary"], "secondary")
        c += link(pad, by + 158, "Cambiar cultivo o semestre", 16)
        ch = by + 184
    else:
        c.append(text(tx, 108, title, 38, 600, font=FONT_TITLE))
        c += paragraph(tx, 146, hd["reasons"], 17, 25)
        by = 210
        c += button(pad, by, 330, hd["primary"]) + button(pad + 346, by, 300, hd["secondary"], "secondary")
        c += link(pad, by + 94, "Cambiar cultivo o semestre", 16)
        ch = by + 120
    b += card(x, y, cw, ch) + [group("accion", c, x, y)]
    if not mobile:
        b += mascot(1000, 130, 1.05, hd["mood"])
    top = max(header_h, y + ch + 40)
    # Las cinco señales
    pad2 = 20 if mobile else 96
    s = [text(pad2, 56, "Las cinco señales", 26 if mobile else 34, 600, font=FONT_TITLE)]
    s += paragraph(pad2, 90, ["Cada una se evalúa por separado;", "ninguna se promedia con otra."] if mobile else
                   ["Cada una se evalúa por separado; ninguna se promedia con otra. Toque una para ver su gráfica."], 16, 22, fill=SEC)
    if mobile:
        cw2, ch2, gy = 350, 196, 140
        for i, (k, t, st, crit, rows) in enumerate(sg):
            s += signal_card(pad2, gy + i * (ch2 + 16), cw2, ch2, k, t, st, crit, rows, compact=True)
        ly = gy + 5 * (ch2 + 16) + 10
    else:
        gap = 20
        cw2 = (w - 2 * pad2 - 4 * gap) / 5
        ch2, gy = 290, 124
        for i, (k, t, st, crit, rows) in enumerate(sg):
            s += signal_card(pad2 + i * (cw2 + gap), gy, cw2, ch2, k, t, st, crit, rows)
        ly = gy + ch2 + 40
    # Limitaciones y versiones (R4, R5)
    lw = w - 2 * pad2
    lh = 64 + len(lim) * (24 if not mobile else 46)
    l = [poly(chamfer(0, 0, lw, lh, 12), "#F2F5F7", BORDE, 2), poly([(0, 0), (8, 0), (8, lh), (0, lh)], P["calabaza"]),
         text(24, 36, "Limitaciones", 18, 700)]
    for i, r in enumerate(lim):
        if mobile and width_of(r, 15) > lw - 60:
            half = r.split(" ")
            m = len(half) // 2
            l += [text(24, 66 + i * 46, "· " + " ".join(half[:m]), 15), text(36, 86 + i * 46, " ".join(half[m:]), 15)]
        else:
            l.append(text(24, 66 + i * (46 if mobile else 24), "· " + r, 15))
    s.append(group("limitaciones", l, pad2, ly))
    vy = ly + lh + 40
    s.append(text(pad2, vy, "Datos 2026.11.0 · Reglas 1.0.0", 15, fill=SEC))
    s += link(pad2 if mobile else w - pad2, vy + (30 if mobile else 0), "¿Cómo funciona y de dónde sale esto?", 15, anchor="start" if mobile else "end")
    sec_h = vy + 70
    h = top + sec_h
    b = [f'<rect y="{header_h}" width="{w}" height="{h - header_h}" fill="{P["niebla"]}"/>'] + b
    b.append(group("senales", s, 0, top))
    foot, fh = ui.footer(w, h, mobile, above=P["niebla"])
    return frame((w, h + fh), b + foot)


# ---------- Gráficas ----------

def bars(x, y, w, h, values, labels, color, stroke, unit, ref=None, ref_label="", last_label="", hatch_last=False, y_max=None):
    """Gráfica de barras con su unidad y su referencia; el último periodo se marca (HU-093)."""
    out = [text(0, -14, unit, 14, 700, SEC)]
    vmax = y_max or max(values + ([ref] if ref else [])) * 1.15
    n = len(values)
    bw = w / n * 0.62
    out.append(f'<rect x="0" y="{h}" width="{w}" height="2" fill="{P["noche"]}"/>')
    for t in (0.5, 1.0):
        ty = h - h * t
        out.append(f'<rect x="0" y="{ty:.1f}" width="{w}" height="1" fill="{BORDE}"/>')
        out.append(text(-8, ty + 5, f"{round(vmax * t):,}".replace(",", "."), 12, fill=SEC, anchor="end"))
    for i, v in enumerate(values):
        bx = i * w / n + (w / n - bw) / 2
        bh = h * v / vmax
        last = i == n - 1
        if last and hatch_last:
            out.append(poly(chamfer(bx, h - bh, bw, bh, 3), WHITE, stroke, 2, "4 3"))
        else:
            out.append(poly(chamfer(bx, h - bh, bw, bh, 3), P["calabaza"] if last else color, D["calabaza"] if last else stroke, 1.5))
        out.append(text(bx + bw / 2, h + 20, labels[i], 12, 700 if last else 400, P["noche"] if last else SEC, anchor="middle"))
    if ref:
        ry = h - h * ref / vmax
        out.append(f'<line x1="0" y1="{ry:.1f}" x2="{w}" y2="{ry:.1f}" stroke="{P["noche"]}" stroke-width="2" stroke-dasharray="8 5"/>')
        out.append(text(w, ry - 8, ref_label, 13, 700, anchor="end"))
    if last_label:
        lx = (n - 1) * w / n + w / n / 2
        out.append(text(lx, h + 38, last_label, 12, 700, D["calabaza"], anchor="middle"))
    return [group("grafica", out, x, y)]


def frost_chart(x, y, w, h, freq, sow, sensitive, short=False):
    months = "EFMAMJJASOND"
    out = [text(0, -14, "% de años con helada" if short else "% de años con al menos una helada (mínima menor que 2 °C)", 14, 700, SEC)]
    n, vmax = 12, 30
    s0, s1 = sensitive
    out.append(f'<rect x="{s0 * w / n:.1f}" y="0" width="{(s1 - s0 + 1) * w / n:.1f}" height="{h}" fill="{P["calabaza"]}" fill-opacity="0.16"/>')
    out.append(text((s0 + (s1 - s0 + 1) / 2) * w / n, 16, "etapa sensible", 12, 700, D["calabaza"], anchor="middle"))
    out.append(f'<rect x="0" y="{h}" width="{w}" height="2" fill="{P["noche"]}"/>')
    for t in (0.5, 1.0):
        ty = h - h * t
        out.append(f'<rect x="0" y="{ty:.1f}" width="{w}" height="1" fill="{BORDE}"/>')
        out.append(text(-8, ty + 5, f"{round(vmax * t)} %", 12, fill=SEC, anchor="end"))
    bw = w / n * 0.62
    for i, v in enumerate(freq):
        bx = i * w / n + (w / n - bw) / 2
        bh = max(2, h * v / vmax)
        hot = s0 <= i <= s1
        out.append(poly(chamfer(bx, h - bh, bw, bh, 2), D["cielo"] if hot else P["niebla"], D["cielo"], 1.5))
        out.append(text(bx + bw / 2, h + 20, months[i], 12, 700 if i == sow else 400, P["noche"] if i == sow else SEC, anchor="middle"))
    sx = sow * w / n + w / n / 2
    out += [poly([(sx - 7, h + 30), (sx + 7, h + 30), (sx, h + 24)], D["brote"]), text(sx, h + 46, "siembra", 12, 700, D["oliva"], anchor="middle")]
    return [group("grafica-heladas", out, x, y)]


def ph_scale(x, y, w):
    narrow = w < 400
    lo, hi = 4.0, 8.0
    X = lambda v: (v - lo) / (hi - lo) * w  # noqa: E731
    out = [text(0, -14, "pH del suelo, de 0 a 30 cm", 14, 700, SEC)]
    out.append(poly(chamfer(0, 0, w, 28, 6), P["niebla"]))
    out.append(f'<rect x="{X(4.8):.1f}" y="0" width="{X(7.0) - X(4.8):.1f}" height="28" fill="{P["trigo"]}" fill-opacity="0.55"/>')
    out.append(f'<rect x="{X(5.0):.1f}" y="0" width="{X(6.5) - X(5.0):.1f}" height="28" fill="{P["brote"]}"/>')
    for v in (4, 5, 6, 7, 8):
        out.append(text(X(v), 50, f"{v}", 12, fill=SEC, anchor="middle"))
    a, b = X(5.2), X(5.8)
    out += [f'<path d="M{a:.1f} -6 V34 M{b:.1f} -6 V34 M{a:.1f} 34 H{b:.1f}" stroke="{P["noche"]}" stroke-width="3" fill="none"/>',
            poly([(X(5.5), -2), (X(5.5) + 8, 8), (X(5.5), 18), (X(5.5) - 8, 8)], P["noche"])]
    out += [text(X(5.5), 74, "Su suelo: 5,2 a 5,8", 14, 700, anchor="middle")]
    lx, ly = (0, 118) if narrow else (w / 2, 92)
    out += [poly(chamfer(0, 92, 16, 16, 3), P["brote"]), text(24, 105, "Óptimo para la papa", 13),
            poly(chamfer(lx, ly, 16, 16, 3), P["trigo"]), text(lx + 24, ly + 13, "Lo tolera", 13)]
    return [group("escala-ph", out, x, y)]


# ---------- Detalle de las cinco señales ----------

RAIN = [350, 402, 298, 381, 420, 455, 310, 395, 376, 412]
RAIN_LABELS = ["16", "17", "18", "19", "20", "21", "22", "23", "24", "25"]
AREA = [790, 820, 805, 840, 860, 830, 1138]
AREA_LABELS = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]
FROST = list(muestra.FROST)  # la misma serie del calendario: es el mismo cálculo


def panel(x, y, w, h, k, title, status, sub, body_fn, name):
    insufficient = status == "insuficiente"
    out = [poly(chamfer(0, 8, w, h, 18), BORDE),
           poly(chamfer(0, 0, w, h, 18), WHITE, D["cielo"] if insufficient else None, 2.5 if insufficient else 0, "3 5" if insufficient else None)]
    if insufficient:
        out += mist(w, h)
    narrow = w < 500
    out += kind(k, 24, 22) + [text(80, 50, title, 26, 600, font=FONT_TITLE)]
    out += tag(24, 68, status, 176, 36) if narrow else tag(w - 200, 24, status, 176, 38)
    out += paragraph(24, 136 if narrow else 96, sub, 15, 21, fill=SEC)
    out += [f'<g transform="translate(0 {40 if narrow else 0})">{"".join(body_fn(w))}</g>']
    return [group(name, out, x, y)]


def signals(mobile=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    pad = 20 if mobile else 96
    pw = w - 2 * pad if mobile else (w - 2 * pad - 24) / 2
    ph = 500 if mobile else 430
    b = topbar(w, "Consultar", None if mobile else "Rosa")
    hy = 120 if mobile else 140
    head = link(0, 0, "← Volver al resultado", 16)
    head += [text(0, 48, "Las cinco señales", 30 if mobile else 40, 600, font=FONT_TITLE)]
    head += paragraph(0, 82, ["Papa · semestre B 2026 · Samacá.", "Cifras de muestra."] if mobile else
                      ["Papa · semestre B · jul–dic 2026 · Samacá, Boyacá. Cifras de muestra."], 16, 22, fill=SEC)
    b.append(group("encabezado", head, pad, hy))
    gw = pw - 100  # ancho de las gráficas

    def rain(wp):
        return bars(64, 190, wp - 100, 150, RAIN, RAIN_LABELS, P["cielo"], D["cielo"], "Lluvia del semestre B, en mm", ref=389,
                    ref_label="Normal: 389 mm", last_label="2025 B")

    def frost(wp):
        return frost_chart(64, 190, wp - 100, 150, FROST, 7, muestra.PAPA_CYCLE_MONTHS, short=wp < 500)

    def soil(wp):
        out = ph_scale(40, 176, wp - 80)
        narrow = wp < 500
        oy = 26 if narrow else 0
        out += [text(40, 330 + oy, "Carbono orgánico: 32 g/kg (medio)", 15, 700), text(40, 354 + oy, "Textura: franco arcillosa", 15, 700)]
        if narrow:
            out += [poly(chamfer(24, 372 + oy, wp - 48, 58, 10), P["niebla"], D["cielo"], 2),
                    text(40, 396 + oy, "Estimación de un mapa global de 250 m.", 13), text(40, 416 + oy, "Un análisis de suelo es más preciso.", 13)]
        else:
            out += [poly(chamfer(24, 372, wp - 48, 44, 10), P["niebla"], D["cielo"], 2),
                    text(44, 400, "Estimación de un mapa global de 250 m. Un análisis de suelo es más preciso.", 13)]
        return out

    def supply(wp):
        short = wp < 500
        return bars(64, 190, wp - 100, 150, AREA, [a[-2:] if short else a for a in AREA_LABELS], shade(P["trigo"], 0.2), D["trigo"],
                    "Papa sembrada, semestre B (ha)" if short else "Papa sembrada en el semestre B, en hectáreas",
                    ref=843, ref_label="Prom. 3 anteriores: 843 ha" if short else "Promedio de los 3 anteriores: 843 ha", last_label="preliminar", hatch_last=False)

    def market(wp):
        return paragraph(24, 190, ["SIPSA no publica precios mayoristas", "de papa para esta zona.", "",
                                   "Esta señal no cambia el semáforo;", "se lista en las limitaciones."], 16, 24) + link(24, 340, "¿De dónde salen los precios?", 15)

    def rules(wp):
        steps = [("1", "Lluvia y oferta tienen datos:", "se puede evaluar."), ("2", "Ninguna señal crítica y una sola", "desfavorable: no es rojo."),
                 ("3", "Hay una desfavorable (oferta):", "no es verde."), ("4", "Queda amarillo: esperar otro", "semestre, porque el suelo es apto.")]
        out = []
        for i, (n, a, c2) in enumerate(steps):
            yy = 110 + i * 72
            out += [poly(chamfer(24, yy - 22, 36, 36, 6), P["trigo"] if i == 3 else P["niebla"]), text(42, yy + 2, n, 18, 700, anchor="middle"),
                    text(76, yy - 2, a, 16, 700), text(76, yy + 20, c2, 15, fill=SEC)]
        return out

    items = [
        ("lluvia", "Lluvia", "favorable", ["En 7 de los últimos 10 semestres B la", "lluvia fue favorable para la papa.", "Último dato: 2025 B. Fuente: NASA POWER."], rain, "detalle-lluvia"),
        ("heladas", "Heladas", "moderado", ["Sembrando en agosto, el mejor mes del", f"semestre: heló en diciembre {muestra.FROST[11]} de cada", "100 años. Fuente: NASA POWER."], frost, "detalle-heladas"),
        ("suelo", "Suelo", "favorable", ["El pH estimado cae en el rango óptimo", "de la papa. Fuente: SoilGrids (ISRIC),", "celdas de 250 m."], soil, "detalle-suelo"),
        ("oferta", "Oferta", "desfavorable", ["En 2025 B (último dato, preliminar) se", "sembró 35 % más que en los tres", "semestres B anteriores. Fuente: EVA."], supply, "detalle-oferta"),
        ("mercado", "Mercado", "insuficiente", ["Sin datos de precios para Samacá.", "Fuente prevista: SIPSA (DANE)."], market, "detalle-mercado"),
    ]
    gy = hy + (150 if mobile else 140)
    for i, (k, t, st, sub, fn, name) in enumerate(items):
        if mobile:
            px, py = pad, gy + i * (ph + 24)
        else:
            px, py = pad + (i % 2) * (pw + 24), gy + (i // 2) * (ph + 24)
        b += panel(px, py, pw, ph, k, t, st, sub, fn, name)
    # Cómo se decidió el semáforo (explicable, R2)
    if mobile:
        rx, ry = pad, gy + 5 * (ph + 24)
    else:
        rx, ry = pad + pw + 24, gy + 2 * (ph + 24)
    r = [poly(chamfer(0, 8, pw, ph, 18), BORDE), poly(chamfer(0, 0, pw, ph, 18), WHITE), text(24, 50, "Cómo salió el amarillo", 26, 600, font=FONT_TITLE)]
    r += rules(pw)
    r += link(24, ph - 24, "Ver todas las reglas del semáforo", 15)
    b.append(group("como-se-decidio", r, rx, ry))
    h = ry + ph + 80
    foot, fh = ui.footer(w, h, mobile, above=P["niebla"])
    return frame((w, h + fh), b + foot, P["niebla"])


SCREENS = {  # elegir y el resultado amarillo pasaron a diagnostico.py (ventanas de siembra); rojo, no evaluable y señales se rehacen en la tanda 2
    "consulta-02-resultado-rojo-helada-escritorio": lambda: result("rojo"),
    "consulta-02-resultado-no-evaluable-escritorio": lambda: result("no-evaluable"),
    "consulta-03-senales-escritorio": lambda: signals(),
    "consulta-03-senales-movil": lambda: signals(mobile=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
