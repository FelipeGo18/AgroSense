"""Pantallas finales de la consulta sobre ventanas de siembra (rediseño, tanda 1). Escritorio y móvil.

EP-09 (HU-091, HU-092, HU-202, HU-203) sobre `specs/01-reglas.md`: aptitud del cultivo, seis señales calificadas
de 0 a 100, las prioridades del agricultor (seis pesos de 0 a 5) y, cuando sus prioridades dan otra luz que las de
AgroSense, las dos luces. Con «Mejor otro cultivo en esta fecha», los cultivos alternativos. Todo es informativo:
la decisión es del agricultor. Los datos salen de muestra.py; son de muestra.

    python design/pantallas/diagnostico.py     # escribe svg/consulta-01-elegir-*, consulta-02-resultado-*, consulta-05-prioridades-*
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
import muestra as m  # noqa: E402
import senales as sg  # noqa: E402
from ui import (BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, frame, group, link, mascot,  # noqa: E402
                paragraph, poly, scene, text, topbar, width_of)

CROPS = ("Papa", "Arveja", "Haba", "Maíz", "Zanahoria", "Cebolla")
MONTHS = (("Oct", "2026"), ("Nov", ""), ("Dic", ""), ("Ene", "2027"), ("Feb", ""), ("Mar", ""), ("Abr", ""), ("May", ""), ("Jun", ""),
          ("Jul", ""), ("Ago", ""), ("Sep", ""))
CHOSEN_MONTH = 10  # agosto de 2027


def wrap(t, n):
    words, line, out = t.split(" "), "", []
    for wd in words:
        if line and len(line) + len(wd) + 1 > n:
            out.append(line)
            line = ""
        line = (line + " " + wd).strip()
    out.append(line)
    return out


def chip(x, y, w, h, label, on, sub=None):
    out = [poly(chamfer(x, y, w, h, 9), "#E3EECF" if on else WHITE, D["oliva"] if on else BORDE, 3 if on else 1.5)]
    if sub:
        out += [text(x + w / 2, y + h / 2 + 1, label, 16, 700 if on else 400, anchor="middle"), text(x + w / 2, y + h / 2 + 18, sub, 11, fill=SEC, anchor="middle")]
    else:
        out.append(text(x + w / 2, y + h / 2 + 6, label, 16, 700 if on else 400, anchor="middle"))
    return out


def options(x, y, w, labels, on_index):
    """Elección de una opción entre varias (por ejemplo, el riego)."""
    gap = 10
    ow = (w - gap * (len(labels) - 1)) / len(labels)
    out = []
    for i, lab in enumerate(labels):
        on = i == on_index
        out += [poly(chamfer(x + i * (ow + gap), y, ow, 48, 10), D["oliva"] if on else WHITE, None if on else BORDE, 0 if on else 2),
                text(x + i * (ow + gap) + ow / 2, y + 31, lab, 17, 700, WHITE if on else P["noche"], anchor="middle")]
    return out


# ---------- Elegir: cultivo, cuándo sembrar, riego y prioridades ----------

def choose(mobile=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    h = 1560 if mobile else 1300
    b = scene("a5-municipio", w, h, "recorte-elegir" + ("-m" if mobile else ""), 0.1)
    b += topbar(w, "Consultar", None if mobile else m.NAME)
    x, y, cw, pad = (12, 92, 366, 20) if mobile else (96, 120, 700, 36)
    fw = cw - 2 * pad
    c = [text(pad, 50, "CONSULTA", 15, 700, SEC), text(pad, 92, "¿Qué quiere sembrar?", 28 if mobile else 38, 600, font=FONT_TITLE)]
    c += [poly(chamfer(pad, 112, fw, 48, 10), P["niebla"]), poly([(pad + 22, 124), (pad + 30, 136), (pad + 22, 148), (pad + 14, 136)], D["brote"]),
          text(pad + 42, 143, m.TOWN, 18, 700)] + link(pad + fw - 16, 143, "Cambiar", 16, anchor="end")
    # cultivo
    c.append(text(pad, 196, "Cultivo", 18, 700))
    cols = 2 if mobile else 3
    chw, chh = (fw - (cols - 1) * 10) / cols, 48
    for i, crop in enumerate(CROPS):
        c += chip(pad + (i % cols) * (chw + 10), 210 + (i // cols) * (chh + 10), chw, chh, crop, crop == "Papa")
    yy = 210 + ((len(CROPS) + cols - 1) // cols) * (chh + 10) + 6
    c += link(pad, yy + 16, "Ver todos los cultivos", 15)
    # cuándo sembrar
    yy += 56
    c += [text(pad, yy, "¿Cuándo quiere sembrar?", 18, 700), text(pad, yy + 22, "Un mes de los próximos doce y, si quiere, la semana.", 14, fill=SEC)]
    mc = 4 if mobile else 6
    mw, mh = (fw - (mc - 1) * 8) / mc, 50
    for i, (mon, yr) in enumerate(MONTHS):
        c += chip(pad + (i % mc) * (mw + 8), yy + 38 + (i // mc) * (mh + 8), mw, mh, mon, i == CHOSEN_MONTH, yr or None)
    yy += 38 + ((12 + mc - 1) // mc) * (mh + 8) + 4
    c += ui.field(pad, yy + 18, fw, "Semana (opcional)", "Del 2 al 8 de agosto de 2027", trailing="▾", name="campo-semana")
    yy += 110
    c += [poly(chamfer(pad, yy, fw, 56, 10), "#EEF2E4", D["oliva"], 1.5), text(pad + 16, yy + 24, "¿No sabe cuándo?", 15, 700)]
    c += link(pad + 16, yy + 44, "Ver las mejores fechas para la papa", 15)
    # riego
    yy += 92
    c += [text(pad, yy, "¿Tiene riego?", 18, 700), text(pad, yy + 22, "Con riego, que no llueva no es un riesgo.", 14, fill=SEC)]
    c += options(pad, yy + 36, fw, ("Sí", "No", "No sé"), 1)
    # prioridades
    yy += 112
    c.append(text(pad, yy, "¿Qué le importa al elegir la fecha?", 18, 700))
    c += sg.priorities_summary(pad, yy + 14, fw, m.DEFAULT_WEIGHTS, own=False)
    yy += 96
    c += button(pad, yy, fw, "Ver diagnóstico")
    c += paragraph(pad, yy + 96, ["¿Ya sembró y quiere saber qué sigue?"], 16, fill=SEC)
    c += link(pad, yy + 124, "Ver qué sembrar después", 16)
    ch = yy + 150
    b += card(x, y, cw, ch) + [group("contenido", c, x, y)]
    if not mobile:
        b += mascot(900, 220, 1.3, "guia", "germinada")
    return frame((w, max(h, y + ch + 60)), b)


# ---------- Resultado ----------

def action_card(x, y, cw, pad, mobile, weights, farmer):
    """La acción primero (HU-092). Con pesos propios que dan otra luz, las dos luces (HU-203)."""
    fw = cw - 2 * pad
    res = m.light_for(weights)
    res_default = m.light_for(m.DEFAULT_WEIGHTS)
    c = [text(pad, 42, "PAPA · SIEMBRA 2 AGO 2027 → COSECHA ~27 DIC" if mobile else m.QUERY_KICKER, 13 if mobile else 14, 700, SEC),
         text(pad, 62, "Cosecha estimada con un año normal; no es pronóstico.", 13, fill=SEC)]
    yy = 86
    if farmer and res["light"] != res_default["light"]:
        tl, th = sg.two_lights(pad, yy, fw, res, res_default, "Usted puso la oferta en 0: no cuenta para su luz.")
        c += tl
        yy += th + 22
        reasons = ["Con sus prioridades no hay nada en contra: lo que más limita son las heladas, moderadas.",
                   "Con el criterio de AgroSense, hay mucha papa sembrada en Samacá."]
        primary, secondary = "Registrar esta siembra", "Ver otros cultivos"
    else:
        c += sg.light_block(pad, yy, fw, res, "Criterio de AgroSense", True)
        yy += 128 if mobile else 102
        reasons = ["En 2025 B, el último dato, se sembró 35 % más papa que antes en Samacá: con mucha oferta, el precio suele bajar.",
                   "El clima de esta fecha le sirve a la papa: agua y calor bien, heladas moderadas."]
        primary, secondary = "Ver otros cultivos", "Ver otras fechas"
    for r in reasons:
        rows = wrap(r, 40 if mobile else 92)
        c += paragraph(pad, yy, rows, 16, 23)
        yy += len(rows) * 23 + 6
    yy += 10
    if mobile:
        c += button(pad, yy, fw, primary) + button(pad, yy + 68, fw, secondary, "secondary")
        yy += 140
    else:
        c += button(pad, yy, 300, primary) + button(pad + 316, yy, 260, secondary, "secondary")
        yy += 76
    c += sg.priorities_summary(pad, yy, fw, weights, own=farmer)
    yy += 88 if mobile else 72
    c += link(pad, yy, "Cambiar cultivo, fecha o riego", 15)
    yy += 26
    return c, yy


def result(mobile=False, farmer=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    weights = m.FARMER_WEIGHTS if farmer else m.DEFAULT_WEIGHTS
    res = m.light_for(weights)
    header_h = 560 if mobile else 440
    tagname = ("-m" if mobile else "") + ("-f" if farmer else "")
    b = scene("a5-municipio", w, header_h, f"recorte-resultado{tagname}", 0.12)
    b += topbar(w, "Consultar", None if mobile else m.NAME)
    x, y, cw, pad = (12, 92, 366, 20) if mobile else (96, 116, 900, 36)
    c, ch = action_card(x, y, cw, pad, mobile, weights, farmer)
    b += card(x, y, cw, ch) + [group("accion", c, x, y)]
    if not mobile:
        b += mascot(1090, 130, 0.95, "guia")
    top = max(header_h, y + ch + 40)
    pad2 = 16 if mobile else 96
    iw = w - 2 * pad2
    s = sg.suitability_line(pad2, 20, iw, m.SUITABILITY)
    ty = 168 if mobile else 124
    s += [text(pad2, ty, "Las seis señales de esta fecha", 24 if mobile else 32, 600, font=FONT_TITLE)]
    s += paragraph(pad2, ty + 32, ["Cada una calificada de 0 a 100 para la", "papa. Ninguna se promedia con otra."] if mobile else
                   ["Cada una calificada de 0 a 100 frente a lo que necesita la papa. Ninguna se promedia con otra. Toque una para ver su gráfica."], 15, 21, fill=SEC)
    gy = 256 if mobile else 190
    if mobile:
        ch2 = 300
        for i, k in enumerate(m.SIGNAL_ORDER):
            s += sg.signal_card(pad2, gy + i * (ch2 + 14), iw, ch2, k, weights, res["limiting"], compact=True)
        ny = gy + 6 * (ch2 + 14) + 20
    else:
        gap, cols = 24, 3
        cw2, ch2 = (iw - (cols - 1) * gap) / cols, 300
        for i, k in enumerate(m.SIGNAL_ORDER):
            s += sg.signal_card(pad2 + (i % cols) * (cw2 + gap), gy + (i // cols) * (ch2 + gap), cw2, ch2, k, weights, res["limiting"])
        ny = gy + 2 * (ch2 + gap) + 20
    show_alt = res["action"] == "rotate" or m.light_for(m.DEFAULT_WEIGHTS)["action"] == "rotate"
    if show_alt:
        al, ah = sg.alternatives(pad2, ny + 24, iw, m.ALTERNATIVES, compact=mobile)
        s += al
        ny += ah + 50
    lim = ["Los datos de EVA de 2025 son preliminares.", "El suelo es el estimado para el municipio, no para su lote.",
           "Sin datos de mercado: el precio no se evaluó.", "Evaluado sin riego, como usted indicó."]
    lh = 60 + len(lim) * (24 if not mobile else 44)
    lb = [poly(chamfer(0, 0, iw, lh, 12), "#F2F5F7", BORDE, 2), poly([(0, 0), (8, 0), (8, lh), (0, lh)], P["calabaza"]), text(24, 34, "Limitaciones", 18, 700)]
    for i, r in enumerate(lim):
        rows = wrap(r, 40) if mobile else [r]
        lb += [text(24, 62 + i * (44 if mobile else 24) + j * 20, ("· " if j == 0 else "  ") + ln, 15) for j, ln in enumerate(rows)]
    s.append(group("limitaciones", lb, pad2, ny))
    vy = ny + lh + 40
    pesos = "Sus prioridades" if farmer else "Pesos de AgroSense"
    s.append(text(pad2, vy, f"{m.VERSIONS} · {pesos}", 15, fill=SEC))
    s += link(pad2 if mobile else w - pad2, vy + (30 if mobile else 0), "¿Cómo funciona y de dónde sale esto?", 15, anchor="start" if mobile else "end")
    h = top + vy + 70
    b = [f'<rect y="{header_h}" width="{w}" height="{h - header_h}" fill="{P["niebla"]}"/>'] + b
    b.append(group("senales", s, 0, top))
    foot, fh = ui.footer(w, h, mobile, above=P["niebla"])
    return frame((w, h + fh), b + foot)


# ---------- Ajustar prioridades (hoja sobre el resultado) ----------

def priorities_sheet(mobile=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    weights = m.FARMER_WEIGHTS
    h = 1240 if mobile else 1000
    b = scene("a5-municipio", w, h, "recorte-prioridades" + ("-m" if mobile else ""), 0.12)
    b += topbar(w, "Consultar", None if mobile else m.NAME)
    b.append(f'<rect width="{w}" height="{h}" fill="{P["noche"]}" fill-opacity="0.55"/>')
    if mobile:
        sx, sy, sw, pad = 0, 150, w, 20
    else:
        sx, sy, sw, pad = (w - 720) / 2, 110, 720, 40
    fw = sw - 2 * pad
    c = [text(pad, 48, "SUS PRIORIDADES", 14, 700, SEC)]
    panel, ph = sg.priorities_panel(pad, 88, fw, weights, compact=mobile)
    c += panel
    yy = 88 + ph + 10
    note = ["Agua, heladas y calor graves cuentan siempre,", "aunque les ponga 0: es la protección para no", "sembrar a ciegas."] if mobile else \
        ["Agua, heladas y calor graves cuentan siempre, aunque les ponga 0: es la protección para no sembrar a ciegas."]
    c += [poly(chamfer(pad, yy, fw, 22 + len(note) * 20, 10), "#E6F0F5", D["cielo"], 1.5)] + paragraph(pad + 16, yy + 26, note, 14, 20)
    yy += 22 + len(note) * 20 + 24
    c += paragraph(pad, yy, ["Con cuenta, se guardan en su perfil; sin cuenta,", "en este navegador."] if mobile else
                   ["Con cuenta, se guardan en su perfil; sin cuenta, en este navegador. Cambian el semáforo y el orden de las fechas."], 14, 20, fill=SEC)
    yy += 52 if mobile else 30
    if mobile:
        c += button(pad, yy, fw, "Aplicar") + link(pad, yy + 94, "Volver al criterio de AgroSense", 15)
        c += link(fw + pad, yy + 94, "Cancelar", 15, anchor="end")
    else:
        c += button(pad, yy, 240, "Aplicar") + link(pad + 270, yy + 33, "Volver al criterio de AgroSense", 15)
        c += link(fw + pad, yy + 33, "Cancelar", 15, anchor="end")
    shh = yy + 110
    if mobile:
        b += [poly(chamfer(sx, sy, sw, shh + 40, 20), WHITE), poly(chamfer(w / 2 - 28, sy + 10, 56, 6, 3), BORDE)]
    else:
        b += card(sx, sy, sw, shh)
    b += [group("hoja-prioridades", c, sx, sy)]
    return frame((w, max(h, sy + shh + 60)), b)


SCREENS = {
    "consulta-01-elegir-escritorio": lambda: choose(),
    "consulta-01-elegir-movil": lambda: choose(mobile=True),
    "consulta-02-resultado-amarillo-escritorio": lambda: result(),
    "consulta-02-resultado-amarillo-movil": lambda: result(mobile=True),
    "consulta-02-resultado-dos-luces-escritorio": lambda: result(farmer=True),
    "consulta-02-resultado-dos-luces-movil": lambda: result(mobile=True, farmer=True),
    "consulta-05-prioridades-escritorio": lambda: priorities_sheet(),
    "consulta-05-prioridades-movil": lambda: priorities_sheet(mobile=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
