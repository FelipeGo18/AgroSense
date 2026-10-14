"""Tanda 11 · «Lote sin dibujar» (HU-164, HU-169). Escritorio y móvil, y cómo se ve en Mi finca.

Quien no puede o no quiere dibujar su lote escribe el área a mano («Escribir el área a mano», en lote.py). El lote
se guarda sin contorno (`geometry` nulo) y **queda sin ubicación**: se dice qué cambia y que puede dibujarlo después.

- Sin contorno, el suelo y la altitud son los del municipio, no los del lote, y el lote no sale en el mapa.
- El resto es igual: nombre, «¿Este lote tiene riego?» y, si ya sembró, el cultivo y la fecha.
- En Mi finca, los lotes sin dibujar no están en el mapa: se ven en una lista aparte, cada uno con «Dibujar en el mapa».

Qué hace cada control: «Guardar lote» envía POST /lots sin `geometry`; «Dibujar en el mapa» vuelve al dibujo (o lo
abre para un lote ya guardado, PATCH /lots/{id} con `geometry`); tocar el lote en la lista abre su detalle.
Los nombres y las cifras son de muestra.

    python design/pantallas/sin_dibujo.py     # escribe svg/descenso-03-lote-sin-dibujar-*.svg y svg/finca-01-mis-lotes-sin-dibujar-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from finca import LOTS, lot_on_map, lot_row, map_legend, zone_select  # noqa: E402
from inicio import stepper  # noqa: E402
from lote import SOWN_ON, attribution, choice, irrigation_question, map_view, scale_bar, zoom_controls  # noqa: E402
from ui import BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, field, frame, group, link, paragraph, poly, text, topbar  # noqa: E402

UNDRAWN = dict(name="La Esperanza", area="2,50 ha", crop="Sin siembra en curso")


def what_changes(x, y, w, compact=False):
    """Lo que cambia sin dibujo, dicho antes de guardar."""
    rows = (["Sin dibujo, su lote queda sin ubicación:", "· No sale en el mapa de su finca.", "· El suelo y la altitud son los de Samacá,", "  no los de su lote.", "Puede dibujarlo después, cuando quiera."] if compact else
            ["Sin dibujo, su lote queda sin ubicación:", "· No sale en el mapa de su finca.", "· El suelo y la altitud son los de Samacá, no los", "  de su lote.", "Puede dibujarlo después, cuando quiera."])
    h = 26 + len(rows) * 21
    body = [poly(chamfer(0, 0, w, h, 10), "#E6F0F5", D["cielo"], 1.5)]
    body += [text(16, 30 + i * 21, row, 14, 700 if i in (0, len(rows) - 1) else 400) for i, row in enumerate(rows)]
    return [group("sin-ubicacion", body, x, y)], h


def form(pad, fw, compact=False):
    c = field(pad, 0, fw, "Área del lote (ha)", "2,5", state="foco", name="campo-area", hint="En hectáreas. Una hectárea son 10.000 m².")
    yy = 128
    wc, wh = what_changes(pad, yy, fw, compact)
    c += wc
    yy += wh + 30
    c += field(pad, yy, fw, "Nombre del lote", UNDRAWN["name"], name="campo-nombre")
    yy += 112
    rq, rh = irrigation_question(pad, yy, fw, on=2, compact=compact)
    c += rq
    yy += rh + 26
    c.append(text(pad, yy, "¿Ya sembró algo en este lote?", 18, 700))
    c += [group("opciones", choice(pad, yy + 16, fw, "Sí", "Todavía no", on_left=False))]
    yy += 92
    c += button(pad, yy, fw, "Guardar lote")
    c += link(pad, yy + 88, "Dibujar en el mapa")
    return c, yy + 112


def desktop():
    w, h = DESKTOP[0], DESKTOP[1] + 190
    zoom = 1.5
    b = map_view(w, h, (920 - 200 / zoom, 600), zoom, [], "recorte-sin-dibujo")
    b.append(f'<rect width="{w}" height="{h}" fill="{WHITE}" fill-opacity="0.45"/>')  # el mapa queda atrás: aquí no se dibuja
    b += topbar(w, user="Rosa")
    b += stepper(500, 112, 520, 3)
    b += zoom_controls(w - 88, 116)
    note = [poly(chamfer(0, 6, 420, 92, 12), BORDE), poly(chamfer(0, 0, 420, 92, 12), WHITE), text(20, 34, "Está escribiendo el área a mano", 17, 700)]
    note += paragraph(20, 58, ["El mapa sigue aquí por si quiere dibujar su lote."], 14, 20, fill=SEC) + link(20, 82, "Dibujar en el mapa", 14)
    b.append(group("aviso-mapa", note, 500 + (w - 500 - 420) / 2, h / 2 - 20))
    b += scale_bar(470, h - 44, zoom)
    b += attribution(w - 12, h - 30)
    x, y, cw, pad = 32, 112, 420, 30
    fw = cw - 2 * pad
    c = [text(pad, 48, "PASO 2 DE 2", 15, 700, SEC), text(pad, 92, "Su lote, sin dibujar", 32, 600, font=FONT_TITLE)]
    f, fh = form(pad, fw)
    c.append(group("formulario", f, 0, 136))
    b += card(x, y, cw, 136 + fh + 14) + [group("panel", c, x, y)]
    return frame((w, max(h, y + 136 + fh + 60)), b)


def mobile():
    w = MOBILE[0]
    pad, fw = 22, w - 44
    b = [f'<rect width="{w}" height="2000" fill="{P["niebla"]}"/>'] + topbar(w)
    b += link(16, 118, "‹ Samacá, Boyacá", 16)
    c = [text(pad, 44, "PASO 2 DE 2", 14, 700, SEC), text(pad, 82, "Su lote, sin dibujar", 26, 600, font=FONT_TITLE)]
    f, fh = form(pad, fw, compact=True)
    c.append(group("formulario", f, 0, 126))
    ch = 126 + fh + 14
    b += card(12, 140, w - 24, ch) + [group("panel", c, 1, 140)]
    return frame((w, 140 + ch + 50), b, P["niebla"])


def undrawn_row(x, y, w):
    """Un lote sin dibujar en Mi finca: no está en el mapa; se puede abrir o dibujar."""
    u = UNDRAWN
    body = [poly(chamfer(0, 0, w, 96, 12), WHITE, D["cielo"], 2, "6 5"),
            poly(chamfer(12, 14, 68, 68, 8), "#F2F5F7", BORDE, 1.5), f'<path d="M30 60 L38 30 L64 36 L58 62 Z" fill="none" stroke="{D["cielo"]}" stroke-width="2.5" stroke-dasharray="5 4" stroke-linejoin="round"/>',
            text(96, 34, u["name"], 19, 700), text(w - 16, 34, u["area"], 14, fill=SEC, anchor="end"),
            text(96, 56, u["crop"], 14, fill=SEC), text(96, 74, "Área escrita a mano", 13, fill=SEC)]
    body += link(96, 98, "Dibujar en el mapa", 15)
    body[0] = poly(chamfer(0, 0, w, 114, 12), WHITE, D["cielo"], 2, "6 5")
    return [group("lote-sin-dibujar", body, x, y)], 114


def my_lots(mobile_=False):
    """Mi finca con un lote sin dibujar: va en una lista aparte, bajo los lotes que sí están en el mapa."""
    if mobile_:
        w = MOBILE[0]
        zoom, mh = 0.72, 300
        drawn = []
        for lot in LOTS:
            drawn += lot_on_map(lot, zoom * 1.35, compact=True)
        b = map_view(w, mh + 30, (905, 655), zoom, drawn, "recorte-mis-lotes-sd-m")
        b += topbar(w)
        b += attribution(w - 8, mh - 2)
        pad, fw = 16, w - 32
        s = [poly(chamfer(0, 0, w, 1600, 20), WHITE), poly(chamfer(w / 2 - 28, 10, 56, 6, 3), BORDE)]
        s += [text(pad, 50, "MI FINCA", 14, 700, SEC), text(pad, 84, "Sus lotes", 26, 600, font=FONT_TITLE)]
        s += zone_select(pad, 122, fw)
        yy = 210
    else:
        w, h = DESKTOP[0], DESKTOP[1] + 260
        zoom = 1.15
        drawn = []
        for lot in LOTS:
            drawn += lot_on_map(lot, zoom, lot["key"] == "el-alto")
        b = map_view(w, h, (880 - 230 / zoom, 700), zoom, drawn, "recorte-mis-lotes-sd")
        b += topbar(w, active="Mi finca", user="Rosa")
        b += zoom_controls(w - 88, 116)
        b += map_legend(500, h - 100)
        b += scale_bar(w - 270, h - 66, zoom)
        b += attribution(w - 12, h - 30)
        pad, fw = 24, 440 - 48
        s = [text(pad, 44, "MI FINCA", 15, 700, SEC), text(pad, 82, "Sus lotes", 34, 600, font=FONT_TITLE)]
        s += zone_select(pad, 122, fw)
        yy = 206
    s.append(text(pad, yy + 4, "EN EL MAPA", 13, 700, SEC))
    yy += 18
    for lot in LOTS:
        row, rh = lot_row(pad, yy, fw, lot, lot["key"] == "el-alto" and not mobile_)
        s += row
        yy += rh + 10
    s.append(text(pad, yy + 24, "SIN DIBUJAR · NO ESTÁN EN EL MAPA", 13, 700, SEC))
    row, rh = undrawn_row(pad, yy + 38, fw)
    s += row
    yy += 38 + rh + 8
    s += paragraph(pad, yy + 14, ["Usan el suelo y la altitud de Samacá, no los suyos."], 13, 19, fill=SEC)
    yy += 44
    s += button(pad, yy, fw, "Agregar lote")
    if mobile_:
        b += [group("hoja", s, 0, mh)]
        return frame((w, mh + yy + 90), b)
    b += card(32, 104, 440, yy + 76) + [group("panel", s, 32, 104)]
    return frame((w, max(h, 104 + yy + 76 + 50)), b)


SCREENS = {
    "descenso-03-lote-sin-dibujar-escritorio": desktop,
    "descenso-03-lote-sin-dibujar-movil": mobile,
    "finca-01-mis-lotes-sin-dibujar-escritorio": lambda: my_lots(),
    "finca-01-mis-lotes-sin-dibujar-movil": lambda: my_lots(True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
