"""Tanda 8: «Agregar lote o zona» (HU-169). Escritorio y móvil.

Desde Mi finca, «Agregar lote» pregunta dónde está el lote nuevo: en una zona donde ya tiene lotes o en otro
municipio (una zona nueva). Al seguir, la cámara hace un mini descenso de su finca al municipio elegido y abre
«Dibujar mi lote» (HU-164), con la pregunta del riego. Solo aparecen los municipios con datos de la región piloto.
Los nombres son de muestra.

    python design/pantallas/agregar.py     # escribe svg/finca-09-agregar-lote-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from inicio import dropdown  # noqa: E402
from ui import BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, field, frame, group, link, mascot, paragraph, poly, scene, text, topbar  # noqa: E402

ZONES = (("Samacá, Boyacá", "4 lotes"),)
RESULTS = (("Ventaquemada", "Boyacá"), ("Villa de Leyva", "Boyacá"), ("Viracachá", "Boyacá"))


def choice_card(x, y, w, title, sub, on, h=72):
    body = [poly(chamfer(0, 0, w, h, 12), "#FFF6EA" if on else WHITE, P["calabaza"] if on else BORDE, 2.5 if on else 1.5),
            poly([(30, h / 2 - 12), (42, h / 2), (30, h / 2 + 12), (18, h / 2)], P["calabaza"] if on else WHITE, P["noche"], 2)]
    body += [text(58, h / 2 - 4, title, 17, 700), text(58, h / 2 + 18, sub, 13, fill=SEC)]
    return [group("opcion-" + title.split(",")[0].lower().replace(" ", "-"), body, x, y)]


def add_lot(mobile=False, other=False):
    w = MOBILE[0] if mobile else 1440
    h = 844 if mobile else 900
    x, y, cw = (12, 100, 366) if mobile else (96, 140, 600)
    pad = 22 if mobile else 40
    fw = cw - 2 * pad
    c = [text(pad, 52, "AGREGAR LOTE", 14, 700, SEC), text(pad, 94, "¿Dónde está el lote nuevo?", 25 if mobile else 34, 600, font=FONT_TITLE)]
    c += paragraph(pad, 128, ["Al seguir, bajamos de su finca al", "municipio que elija para dibujarlo."] if mobile else
                   ["Al seguir, bajamos de su finca al municipio que elija para dibujarlo."], 15, 22, fill=SEC)
    yy = 128 + (2 if mobile else 1) * 22 + 20
    c.append(text(pad, yy, "En una zona donde ya tiene lotes", 15, 700, SEC))
    yy += 14
    for name, sub in ZONES:
        c += choice_card(pad, yy, fw, name, sub, not other)
        yy += 84
    c += choice_card(pad, yy, fw, "En otro municipio", "Se agrega como una zona nueva", other)
    yy += 106 if other else 96
    if other:
        c += field(pad, yy, fw, "Municipio", "v", state="foco", name="campo-municipio")
        c += dropdown(pad, yy + 74, fw, RESULTS)
        yy += 74 + len(RESULTS) * 52 + 16 + 20
        c += paragraph(pad, yy, ["Solo aparecen los municipios con datos", "de la región piloto."], 13, 19, fill=SEC)
        yy += 54
    c += button(pad, yy, fw, "Seguir: dibujar el lote", "disabled" if other else "primary")
    c += link(pad + fw / 2, yy + 88, "Cancelar", 16, anchor="middle")
    ch = yy + 116
    h = max(h, y + ch + 40)
    b = scene("a3-region", w, h, "recorte-agregar" + ("-m" if mobile else "") + ("-o" if other else ""))
    b += topbar(w, active="Mi finca", user=None if mobile else "Rosa")
    if not mobile:
        b += mascot(860, 220, 1.3, "vuelo")
    b += card(x, y, cw, ch) + [group("contenido", c, x, y)]
    return frame((w, h), b)


SCREENS = {
    "finca-09-agregar-lote-escritorio": add_lot,
    "finca-09-agregar-lote-otro-municipio-movil": lambda: add_lot(mobile=True, other=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
