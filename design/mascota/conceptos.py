"""Tres conceptos de mascota para elegir (HU-171). Escribe conceptos.svg, la lámina comparativa para Figma.

A · Semilla: el satélite de build_mascota.py.
B · Colibrí: un ave-satélite andina, de perfil, con alas que son paneles.
C · Cubo vigía: un CubeSat con un gran ojo de lente, orejas de panel y antena de plato.

    python design/mascota/conceptos.py
"""

import math

from build_mascota import (BORDE, CASCO, D, DIR, FONT_TITLE, H, LUZ, MARCO, P, PARCELS, SEC, VISOR, W, WHITE, chamfer, group,
                           inner, lines, mascot, poly, ridges, section, shade, stage, svg, text)

MOODS = ("reposo", "celebra", "sin-datos")


def octagon(cx, cy, r):
    return [(cx + r * math.cos(math.pi / 4 * i + math.pi / 8), cy + r * math.sin(math.pi / 4 * i + math.pi / 8)) for i in range(8)]


def parcel_panel(x, y, w, h, cols=3, rows=2):
    out = [poly(chamfer(x, y, w, h, 5), MARCO)]
    cw, ch = (w - 8) / cols, (h - 8) / rows
    for r in range(rows):
        for c in range(cols):
            color = PARCELS[(r * 3 + c) % len(PARCELS)]
            cell = chamfer(x + 4 + c * cw + 1, y + 4 + r * ch + 1, cw - 2, ch - 2, 2)
            out += [poly(cell, color), poly([cell[0], cell[1], cell[-1]], shade(color, 0.14))]
    return out


def extras(mood):
    out = []
    if mood == "celebra":
        for x, y, r in ((50, 50, 9), (252, 44, 7), (258, 190, 6)):
            star = [(x, y - r), (x + r * 0.35, y - r * 0.35), (x + r, y), (x + r * 0.35, y + r * 0.35), (x, y + r), (x - r * 0.35, y + r * 0.35), (x - r, y), (x - r * 0.35, y - r * 0.35)]
            out.append(poly(star, P["trigo"], D["trigo"], 1.5))
    if mood == "sin-datos":
        for x, y, k in ((82, 216, 1.0), (214, 222, 0.8)):
            out.append(poly([(x - 46 * k, y + 12 * k), (x - 34 * k, y - 4 * k), (x - 8 * k, y - 14 * k), (x + 24 * k, y - 10 * k), (x + 46 * k, y + 4 * k), (x + 40 * k, y + 12 * k)], P["niebla"], BORDE, 1.5))
    return out


def light_eye(mood, cx, cy, r):
    """Ojo de luz: abierto, en arco (celebra) o en anillo a trazos (sin datos, nunca triste)."""
    if mood == "celebra":
        return [poly([(cx - r, cy + r * 0.5), (cx, cy - r * 0.8), (cx + r, cy + r * 0.5), (cx + r * 0.5, cy + r * 0.5), (cx, cy - r * 0.1), (cx - r * 0.5, cy + r * 0.5)], LUZ)]
    if mood == "sin-datos":
        return [poly(octagon(cx, cy, r), "none", LUZ, 2.5, "4 3")]
    return [poly(octagon(cx, cy, r), LUZ), poly(octagon(cx + r * 0.15, cy, r * 0.42), VISOR)]


# ---------- B · Colibrí ----------

def colibri(mood="reposo"):
    wing = {"reposo": 34, "celebra": 62, "sin-datos": -8}[mood]
    folded = mood == "sin-datos"
    px, py = 150, 122
    w, h = (40, 26) if folded else (74, 40)

    def wing_group(name, angle, dim):
        body = parcel_panel(px - 6 - w, py - h / 2, w, h, cols=2 if folded else 3)
        if dim:
            shade_pts = " ".join(f"{x:g},{y:g}" for x, y in chamfer(px - 6 - w, py - h / 2, w, h, 5))
            body.append(f'<polygon points="{shade_pts}" fill="{VISOR}" fill-opacity="0.35"/>')
        return group(name, body, f"rotate({angle} {px} {py})")

    tail = [
        poly([(108, 150), (58, 172), (86, 162)], P["oliva"]),
        poly([(104, 156), (50, 194), (90, 174)], D["brote"]),
        poly([(110, 164), (66, 214), (100, 182)], P["oliva"]),
    ]
    body = [
        poly([(120, 112), (160, 100), (196, 112), (150, 138)], P["brote"]),
        poly([(96, 150), (120, 112), (150, 138), (112, 172)], shade(P["brote"], -0.12)),
        poly([(150, 138), (196, 112), (206, 138), (190, 166)], CASCO),
        poly([(112, 172), (150, 138), (190, 166), (150, 182)], shade(CASCO, -0.1)),
        poly([(96, 150), (120, 112), (160, 100), (196, 112), (206, 138), (190, 166), (150, 182), (112, 172)], "none", D["cielo"], 3),
    ]
    head = [
        poly([(186, 84), (214, 74), (238, 92), (234, 118), (206, 130), (186, 112)], CASCO, D["cielo"], 3),
        poly([(186, 84), (214, 74), (238, 92), (208, 96)], P["brote"]),
        poly([(190, 114), (206, 130), (200, 148), (182, 134)], shade(P["calabaza"], 0.2)),  # gorguera: el rubor
        poly(octagon(214, 102, 14), VISOR),
        poly(octagon(214, 102, 14), "none", MARCO, 2.5),
    ]
    beak = [poly([(236, 98), (292, 105), (236, 109)], D["cielo"]), poly(octagon(292, 105, 4.5), P["calabaza"])]
    parts = [
        wing_group("ala-lejana", wing + 22, True),
        group("cola", tail),
        group("cuerpo", body),
        group("pico-antena", beak),
        group("cabeza", head),
        group("ojo", light_eye(mood, 214, 102, 8)),
        wing_group("ala", wing, False),
    ]
    lift = {"celebra": -8}.get(mood, 0)
    scale = "translate(15 20) scale(0.9)" if folded else f"translate(0 {lift})"
    return svg(W, H, [group("colibri", parts, scale)] + extras(mood))


# ---------- C · Cubo vigía ----------

def cubo(mood="reposo"):
    ear = {"reposo": 0, "celebra": -18, "sin-datos": 78}[mood]

    def ear_group(name, side):
        px, py = 112, 84
        body = [poly([(px, py), (px - 10, py - 14), (px - 6, py - 16), (px + 4, py - 2)], D["cielo"])]
        body += parcel_panel(px - 52, py - 46, 46, 32, cols=2)
        t = f"rotate({ear} {px} {py})"
        return group(name, body, t if side < 0 else f"translate(300 0) scale(-1 1) {t}")

    box = [
        poly([(106, 96), (194, 96), (214, 80), (126, 80)], WHITE, D["cielo"], 3),  # tapa
        poly([(204, 106), (222, 90), (222, 176), (204, 186)], shade(CASCO, -0.16), D["cielo"], 3),  # costado
        poly(chamfer(96, 96, 108, 100, 10), CASCO, D["cielo"], 3),
        poly([(106, 96), (150, 96), (120, 196), (106, 196), (96, 186), (96, 106)], WHITE),  # faceta de luz
        poly(chamfer(96, 96, 108, 100, 10), "none", D["cielo"], 3),
        poly([(104, 178), (112, 172), (120, 180), (112, 188)], shade(P["calabaza"], 0.35)),
        poly([(196, 178), (188, 172), (180, 180), (188, 188)], shade(P["calabaza"], 0.35)),
    ]
    feet = [poly([(114, 196), (136, 196), (132, 210), (118, 210)], D["cielo"]), poly([(164, 196), (186, 196), (182, 210), (168, 210)], D["cielo"])]
    lens = [poly(octagon(150, 144, 36), MARCO), poly(octagon(150, 144, 29), VISOR), poly([(150, 144)] + octagon(150, 144, 29)[4:7], shade(VISOR, 0.12))]
    dish = [
        poly([(166, 66), (170, 66), (170, 82), (166, 82)], D["cielo"]),
        poly([(136, 58), (200, 58), (186, 70), (150, 70)], P["trigo"], D["trigo"], 2),
        poly([(136, 58), (168, 58), (160, 70), (150, 70)], shade(P["trigo"], 0.16)),
        poly([(160, 58), (176, 58), (168, 44)], D["trigo"]),
    ]
    parts = [
        ear_group("oreja-izq", -1),
        ear_group("oreja-der", 1),
        group("pies", feet),
        group("antena-plato", dish, "rotate(-6 168 82)"),
        group("cuerpo", box),
        group("lente", lens),
        group("iris", light_eye(mood, 150, 144, 15)),
    ]
    t = {"celebra": "translate(0 -8)", "sin-datos": "translate(15 26) scale(0.9)"}.get(mood)
    return svg(W, H, [group("cubo", parts, t)] + extras(mood))


CONCEPTS = (
    ("A · Semilla", lambda mood: mascot(mood), [
        "Una semilla facetada con paneles",
        "de parcelas y un brote por antena.",
        "Visor oscuro con dos ojos de luz.",
        "",
        "A favor: la silueta más simple y la que",
        "mejor se lee en pequeño; repite la",
        "semilla del kit. Dos ojos dan mucha",
        "expresión.",
        "En contra: es la más «robot redondo»;",
        "viaja flotando, sin gesto de vuelo.",
    ]),
    ("B · Colibrí", colibri, [
        "Un ave-satélite andina de perfil: alas",
        "que son paneles de parcelas, pico que",
        "es la antena, cola de plumas facetadas.",
        "",
        "A favor: vuela, se detiene y señala con",
        "el pico: es la que mejor guía con el",
        "scroll. Tiene identidad local.",
        "En contra: un solo ojo visible y más",
        "detalle: pierde algo a 48 px. Se lee",
        "más como ave que como satélite.",
    ]),
    ("C · Cubo vigía", cubo, [
        "Un CubeSat, el satélite pequeño real:",
        "un bloque con un gran ojo de lente,",
        "orejas de panel y antena de plato.",
        "",
        "A favor: es un bloque más del diorama",
        "y lo más «satélite»; el ojo-lente dice",
        "que observa. Las orejas dan gesto.",
        "En contra: un solo ojo limita las",
        "expresiones; el cubo es una forma",
        "más común en mascotas.",
    ]),
)


def place(markup, x, y, scale):
    return f'<g transform="translate({x:g} {y:g}) scale({scale:g})">{inner(markup)}</g>'


def concept_column(draw, notes):
    b = stage(32, 96, 696, 470) + [place(draw("reposo"), 32 + 348 - W * 0.9, 96 + 10, 1.8)]
    b += stage(32, 590, 336, 230) + [place(draw("celebra"), 32 + 168 - W * 0.44, 594, 0.88)]
    b += stage(392, 590, 336, 230) + [place(draw("sin-datos"), 392 + 168 - W * 0.44, 594, 0.88)]
    b += [text(32, 846, "Celebra (verde)", 15, fill=SEC), text(392, 846, "Sin datos: se encoge entre niebla, no se entristece", 15, fill=SEC)]
    b += stage(32, 876, 110, 110, night=True) + [place(draw("reposo"), 32 + 55 - 48 * W / H / 2, 876 + 31, 48 / H)]
    b += stage(158, 876, 110, 110) + [place(draw("reposo"), 158 + 55 - 48 * W / H / 2, 876 + 31, 48 / H)]
    b.append(text(32, 1010, "A 48 px, de noche y de día", 15, fill=SEC))
    b += lines(300, 892, notes, 16, 23)
    return b


def sheet():
    SW, SH = 2400, 1500
    b = [f'<rect width="{SW}" height="{SH}" fill="{P["cielo"]}"/>']
    b += ridges(SW, 1370, 130)
    b.append(text(40, 84, "Mascota satélite · tres conceptos", 48, 600, font=FONT_TITLE))
    b.append(text(40, 122, "HU-171 · Elegir uno. El elegido pasa a versión final, expresiones completas, guía con el scroll y modelo 3D. Los tres comparten paneles de parcelas, ojos de luz y rubor facetado.", 18))
    for i, (name, draw, notes) in enumerate(CONCEPTS):
        b.append(section(40 + i * 780, 150, 760, 1180, name, concept_column(draw, notes)))
    return svg(SW, SH, b)


if __name__ == "__main__":
    out = DIR / "conceptos.svg"
    out.write_text(sheet(), encoding="utf-8", newline="\n")
    print(f"Escrito {out.name} ({out.stat().st_size // 1024} KB)")
