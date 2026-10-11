"""Pantalla final «Lote · próxima siembra» (D2, tanda 7c; rediseño, tanda 6). Escritorio y móvil.

Rediseño: el terreno se elige en el lote (uno o varios, para juntarlos), su historial sale de la red de siembras con
fechas y no con semestres, y el diagnóstico es el de la ventana que empieza cuando se libera el terreno, con las seis
señales y las dos luces. Las prioridades de aquí son las de la rotación («¿Qué busca en la rotación?»).

Qué sembrar después en una parte del lote, con su historial real (el historial de ese terreno: todas las temporadas de las que viene,
`follows_season_ids`) y el suelo estimado del lote: POST /rotations con `lot_id`. Arriba, el diagnóstico de la
siguiente ventana para la mejor opción (POST /diagnostics con `lot_id`). Las prioridades reordenan al instante.
Al final, dos decisiones de P1 rotuladas para el equipo: asegurar la cosecha y los años de El Niño y La Niña;
en la app solo aparecen cuando su dato existe. Nada es pronóstico. Los nombres y las cifras son de muestra.

    python design/pantallas/proxima.py     # escribe svg/finca-04-proxima-siembra-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from build_kit_svg import STATUS, icon  # noqa: E402
from calendario import level_mark, tag, wrap_lines  # noqa: E402
from finca import lot_header, lot_tabs  # noqa: E402
from rotaciones import RANKED, excluded_box, option_card, priorities_panel  # noqa: E402
from ui import BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, frame, group, link, paragraph, poly, text, topbar, width_of  # noqa: E402

PARTS = (("Donde está la papa", "1,26 ha · se libera el 28 dic", True), ("Terreno libre", "0,41 ha · listo para sembrar", False),
         ("Donde está el haba", "0,42 ha · en curso", False), ("Donde está la cebolla", "0,42 ha · en curso", False))
# El historial del terreno sale de la red (historial.py): papa ← maíz ← arveja (que juntó papa y maíz).
HISTORY = (("ago 2025", "Arveja", False), ("ene 2026", "Maíz", False), ("ago 2026", "Papa", True))
SIGNALS = (("Agua", "favorable", 84), ("Heladas", "moderado", 62), ("Calor", "favorable", 96), ("Suelo del lote", "favorable", 78),
           ("Oferta", "favorable", 74), ("Mercado", None, None))


def part_chips(x, y, w, mobile=False):
    """El terreno que se va a sembrar: uno o varios (se juntan); cada uno trae su historial."""
    out, cx, cy = [], 0, 0
    for name, sub, on in PARTS:
        cw = max(width_of(name, 15, True), width_of(sub, 12)) + 30
        if cx + cw > w:
            cx, cy = 0, cy + 58
        cw += 26
        out.append(poly(chamfer(cx, cy, cw, 50, 10), D["oliva"] if on else WHITE, None if on else BORDE, 0 if on else 1.5))
        out.append(poly(chamfer(cx + cw - 30, cy + 15, 20, 20, 4), WHITE if on else WHITE, None if on else BORDE, 0 if on else 2))
        if on:
            out.append(f'<polyline points="{cx + cw - 25},{cy + 25} {cx + cw - 21},{cy + 29} {cx + cw - 14},{cy + 21}" fill="none" stroke="{D["oliva"]}" stroke-width="3" stroke-linecap="round"/>')
        out += [text(cx + 15, cy + 22, name, 15, 700, WHITE if on else P["noche"]), text(cx + 15, cy + 40, sub, 12, fill="#E3EECF" if on else SEC)]
        cx += cw + 8
    return [group("elegir-parte", out, x, y)], cy + 50


def history_card(x, y, w, mobile=False):
    """El historial real de la parte (no se elige a mano) y el suelo del lote que usa el motor."""
    body = [text(24, 40, "HISTORIAL DE ESTE TERRENO", 14, 700, SEC)]
    cx = 24
    for i, (sem, crop, now) in enumerate(HISTORY):
        cw = (w - 48 - 12) / 3 if mobile else 150
        body.append(poly(chamfer(cx, 56, cw, 58, 10), "#FFF1DF" if now else P["niebla"], P["calabaza"] if now else None, 2 if now else 0))
        body += [text(cx + 14, 78, sem, 12, fill=SEC), text(cx + 14, 100, crop, 17, 700)]
        if now:
            body += tag(cx + cw - 34, 50 if mobile else 62, "En curso", P["calabaza"], P["noche"])
        cx += cw + (6 if mobile else 26)
        if i < len(HISTORY) - 1 and not mobile:
            body.append(text(cx - 13, 92, "→", 18, 700, SEC, anchor="middle"))
    yy = 144
    body += [text(24, yy, "Suelo estimado del lote", 13, fill=SEC), text(24, yy + 22, "pH 5,0 a 5,9 · carbono orgánico medio", 16, 700)]
    body += link(w - 24, yy, "Ver suelo", 14, anchor="end")
    body += paragraph(24, yy + 48, wrap_lines(["Se usan las tres últimas siembras de este terreno, de todas las que vino, y el suelo de su polígono. Es una estimación de 250 m (SoilGrids)."], int((w - 48) / 7)), 13, 19, fill=SEC)
    h = yy + 48 + (38 if not mobile else 58) + 16
    return card(x, y, w, h, "tarjeta-historial") + [group("historial", body, x, y)], h


def diagnosis_card(x, y, w, mobile=False):
    """Diagnóstico de la siguiente ventana para la mejor opción del orden."""
    body = [text(24, 40, "DIAGNÓSTICO DE LA MEJOR OPCIÓN", 14, 700, SEC),
            text(24, 74, "Arveja sembrada el 15 ene 2027" if mobile else "Arveja · sembrando el 15 de enero de 2027", 22 if not mobile else 19, 600, font=FONT_TITLE)]
    body += level_mark(46, 112, "favorable", 26) + [text(78, 108, "Verde: sembrar", 20, 700),
                                                    text(78, 130, "Igual con sus prioridades y con el criterio de AgroSense." if not mobile else "Igual con las dos prioridades.", 14, fill=SEC)]
    sx, sy = 24, 156
    for name, lv, score in SIGNALS:
        label = f"{name}: sin datos" if lv is None else f"{name} {score}"
        cw = width_of(label, 13, True) + 44
        if sx + cw > w - 24:
            sx, sy = 24, sy + 36
        if lv is None:
            body += [poly(chamfer(sx, sy, cw, 28, 6), WHITE, D["cielo"], 1.5, "3 4"), text(sx + 16, sy + 19, "?", 14, 700, D["cielo"], anchor="middle")]
        else:
            st = STATUS[lv]
            body += [poly(chamfer(sx, sy, cw, 28, 6), WHITE, st["stroke"], 1.5)] + icon(st["icon"], sx + 9, sy + 7, st["stroke"], 14)
        body.append(text(sx + 30, sy + 19, label, 13, 700))
        sx += cw + 8
    yy = sy + 44
    body += paragraph(24, yy + 6, wrap_lines(["Lo que más limita: heladas (62 de 100). El mercado sin datos no cambia la luz; queda como limitación. Es riesgo histórico, no pronóstico."], int((w - 48) / 7)), 13, 19, fill=SEC)
    yy += 30 if not mobile else 70
    body += button(24, yy + 6, 300 if not mobile else w - 48, "Ver diagnóstico completo", "secondary", h=46)
    h = yy + 76
    return card(x, y, w, h, "tarjeta-diagnostico") + [group("diagnostico", body, x, y)], h


def p1_cards(x, y, w, mobile=False):
    """Decisiones de P1 para la próxima siembra: el seguro y los años de El Niño y La Niña."""
    cw = w if mobile else (w - 24) / 2
    out = tag(x + 76, y, "P1 · próximas tarjetas", WHITE, D["cielo"], D["cielo"], 12)
    out.append(text(x + 160, y + 14, "Solo aparecen cuando su dato existe", 12, fill=SEC))
    y += 34
    n = int((cw - 48) / 7.2)
    # asegurar la cosecha
    a = [text(24, 40, "¿ASEGURAR LA COSECHA?", 14, 700, SEC), text(24, 72, "Riesgos que cubre un seguro, en Samacá", 18, 600, font=FONT_TITLE)]
    rows = (("Helada de enero a mayo", 38, "moderado"), ("Sequía (lluvia muy baja)", 14, "favorable"), ("Exceso de lluvia", 22, "moderado"))
    for i, (name, pct, lv) in enumerate(rows):
        ry = 96 + i * 38
        a += level_mark(40, ry + 10, lv, 14) + [text(64, ry + 15, name, 15), text(cw - 24, ry + 15, f"{pct} de 100 años" if mobile else f"{pct} de cada 100 años", 13 if mobile else 14, 700, anchor="end")]
    note_a = wrap_lines(["Frecuencia histórica de la zona. AgroSense no recomienda un seguro ni una aseguradora."], n)
    note_b = wrap_lines(["Lluvia frente a un año neutro, con los años del pasado. No dice en qué fase estamos: eso lo publica el boletín oficial."], n)
    ly = 226 + max(len(note_a), len(note_b)) * 19 + 18
    a += paragraph(24, 226, note_a, 13, 19, fill=SEC)
    a += link(24, ly, "Incentivo al Seguro Agropecuario ↗" if mobile else "Incentivo al Seguro Agropecuario (sitio oficial) ↗", 14)
    ah = ly + 28
    out += card(x, y, cw, ah, "tarjeta-seguro") + [group("seguro", a, x, y)]
    # El Niño y La Niña
    bx, by = (x, y + ah + 24) if mobile else (x + cw + 24, y)
    b = [text(24, 40, "AÑOS DE EL NIÑO Y LA NIÑA", 14, 700, SEC), text(24, 72, "Lluvia de enero a mayo en el pasado", 18, 600, font=FONT_TITLE)]
    bars = (("Años de El Niño", 78, P["trigo"], D["trigo"]), ("Años neutros", 100, P["cielo"], D["cielo"]), ("Años de La Niña", 124, P["brote"], D["brote"]))
    bw = cw - 48 - 190
    for i, (name, pct, fill, stroke) in enumerate(bars):
        ry = 96 + i * 38
        b += [text(24, ry + 15, name, 15), poly(chamfer(170, ry, bw * pct / 130, 20, 3), fill, stroke, 1.5), text(170 + bw * pct / 130 + 8, ry + 15, f"{pct} %", 14, 700)]
    b += paragraph(24, 226, note_b, 13, 19, fill=SEC)
    b += link(24, ly, "Boletín oficial del fenómeno (Ideam) ↗", 14)
    out += card(bx, by, cw, ah, "tarjeta-enso") + [group("nino-y-nina", b, bx, by)]
    return out, 34 + (ah * 2 + 24 if mobile else ah)


def desktop():
    w = 1440
    b = [f'<rect width="{w}" height="3200" fill="{P["niebla"]}"/>']
    b += topbar(w, active="Mi finca", user="Rosa")
    b += lot_header(48, 140)
    b += lot_tabs(48, 212, "Próxima siembra")
    b += [text(48, 300, "¿Qué terreno va a sembrar?", 18, 700), text(300, 300, "Puede elegir varios para juntarlos en uno.", 15, fill=SEC)]
    chips, ch = part_chips(48, 314, w - 96)
    b += chips
    y = 314 + ch + 30
    b.append(text(48, y + 30, "¿Qué sembrar después de la papa?", 34, 600, font=FONT_TITLE))
    b.append(text(48, y + 58, "Primera siembra desde el 15 de enero de 2027, cuando se libera el terreno · cada opción en su propia ventana · historial real y suelo del lote", 16, fill=SEC))
    b += link(w - 48, y + 30, "Cambiar la fecha", 15, anchor="end")
    y += 84
    lw = 660
    hc, hh = history_card(48, y, lw)
    b += hc
    dc, dh = diagnosis_card(48, y + hh + 24, lw)
    b += dc
    # prioridades
    pw = w - 96 - lw - 24
    ph = hh + 24 + dh
    b += card(48 + lw + 24, y, pw, ph, "tarjeta-prioridades") + priorities_panel(48 + lw + 24 + 32, y + 48, pw - 64, False)
    b += paragraph(48 + lw + 24 + 32, y + 48 + 52 + 4 * 60 + 30, wrap_lines(["Cada prioridad va de 0 a 5. El puntaje de cada opción es el promedio de sus cuatro criterios, ponderado por estas prioridades.",
                                                                                 "Las opciones que violan una regla de rotación o que no se dan en su zona no entran al orden: se listan abajo con su motivo.",
                                                                                 "Son distintas de «¿Qué le importa al elegir la fecha?», que da el semáforo y ordena las ventanas."], 70), 14, 21, fill=SEC)
    y += ph + 44
    b.append(text(48, y + 24, "Opciones ordenadas por lo que le importa", 28, 600, font=FONT_TITLE))
    y += 48
    ow, oh = (w - 96 - 24) / 2, 360
    for i, opt in enumerate(RANKED):
        b += option_card(48 + (i % 2) * (ow + 24), y + (i // 2) * (oh + 28), ow, oh, i + 1, opt, False)
    y += 2 * (oh + 28) + 10
    box, bh = excluded_box(48, y, w - 96, False, False)
    b += box
    y += bh + 40
    p1, p1h = p1_cards(48, y, w - 96)
    b += p1
    y += p1h + 44
    b.append(text(48, y, "Datos 2026.11.0 · Reglas 1.0.0 · Cifras de muestra", 15, fill=SEC))
    b += link(w - 48, y, "¿Cómo se arma este orden?", 15, anchor="end")
    return ui.long_page((w, y + 60), b, P["niebla"])


def mobile():
    w = MOBILE[0]
    pad, fw = 16, w - 32
    b = topbar(w) + lot_header(pad, 118, mobile=True)
    tabs = lot_tabs(-230, 0, "Próxima siembra")
    b.append(f'<defs><clipPath id="recorte-pestanas-prox"><rect x="0" y="200" width="{w}" height="60"/></clipPath></defs>'
             f'<g clip-path="url(#recorte-pestanas-prox)"><g transform="translate({pad} 210)">{"".join(tabs)}</g></g>')
    b += [text(pad, 290, "¿Qué terreno va a sembrar?", 17, 700), text(pad, 312, "Puede elegir varios para juntarlos.", 13, fill=SEC)]
    chips, ch = part_chips(pad, 326, fw, True)
    b += chips
    y = 326 + ch + 24
    b += [text(pad, y + 26, "¿Qué sembrar después", 25, 600, font=FONT_TITLE), text(pad, y + 56, "de la papa?", 25, 600, font=FONT_TITLE),
          text(pad, y + 82, "Primera siembra: 15 de enero de 2027", 14, fill=SEC)]
    b += link(w - pad, y + 82, "Cambiar", 14, anchor="end")
    y += 104
    hc, hh = history_card(pad, y, fw, True)
    b += hc
    y += hh + 20
    dc, dh = diagnosis_card(pad, y, fw, True)
    b += dc
    y += dh + 20
    ph = 52 + 4 * 66 + 60
    b += card(pad, y, fw, ph, "tarjeta-prioridades") + priorities_panel(pad + 20, y + 44, fw - 40, True)
    y += ph + 36
    b.append(text(pad, y + 10, "Opciones ordenadas", 24, 600, font=FONT_TITLE))
    y += 32
    oh = 440
    for i, opt in enumerate(RANKED):
        b += option_card(pad, y + i * (oh + 20), fw, oh, i + 1, opt, True)
    y += 4 * (oh + 20) + 10
    box, bh = excluded_box(pad, y, fw, False, True)
    b += box
    y += bh + 36
    p1, p1h = p1_cards(pad, y, fw, True)
    b += p1
    y += p1h + 40
    b.append(text(pad, y, "Datos 2026.11.0 · Reglas 1.0.0 · Cifras de muestra", 13, fill=SEC))
    b += link(pad, y + 30, "¿Cómo se arma este orden?", 15)
    return ui.long_page((w, y + 80), b, P["niebla"])


SCREENS = {"finca-04-proxima-siembra-escritorio": desktop, "finca-04-proxima-siembra-movil": mobile}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
