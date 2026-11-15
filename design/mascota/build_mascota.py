"""Mascota satélite de AgroSense en 2D (HU-171) y sus expresiones (boceto de HU-172).

Cada parte móvil va en su propio grupo con nombre, para animarla después:
cuerpo, visor, ojo-izq, ojo-der, panel-izq, panel-der, antena. Los puntos de giro están en PIVOTS.

    python design/mascota/build_mascota.py     # escribe svg/*.svg y mascota.svg (lámina para Figma)
"""

import math
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parent / "kit"))

from build_kit_svg import BORDE, D, P, WHITE, chamfer, poly, pts, shade, svg  # noqa: E402
from sheet import FONT_TITLE, SEC, lines, ridges, section, text  # noqa: E402

W, H = 300, 250
CX, CY = 150, 128
CASCO = "#F3F6F8"  # blanco frío del cuerpo: se lee sobre el cielo de día y sobre la noche
VISOR = P["noche"]
LUZ = "#FFF1C9"  # luz de los ojos; nunca cambia de color con el estado (W2)
MARCO = "#2B3B50"

# Puntos de giro para animar (coordenadas del lienzo de 300 × 250).
PIVOTS = {"cuerpo": (CX, CY), "panel-izq": (88, 128), "panel-der": (212, 128), "antena": (CX, 58)}

BODY = [(150, 58), (196, 78), (210, 126), (192, 176), (150, 196), (108, 176), (90, 126), (104, 78)]
VISOR_PTS = [(112, 104), (126, 92), (174, 92), (188, 104), (188, 138), (174, 152), (126, 152), (112, 138)]


def group(name, body, transform=None):
    attr = f' transform="{transform}"' if transform else ""
    return f'<g id="{name}"{attr}>{"".join(body)}</g>'


def mirror(points):
    return [(2 * CX - x, y) for x, y in points]


def body_shape():
    """Semilla facetada: triángulos desde un centro desplazado, con luz desde la izquierda."""
    hub = (144, 118)
    tones = (0.0, -0.05, -0.11, -0.16, -0.09, -0.03, 0.04, 0.02)
    out = []
    for i, f in enumerate(tones):
        a, b = BODY[i], BODY[(i + 1) % len(BODY)]
        out.append(poly([hub, a, b], shade(CASCO, f) if f <= 0 else CASCO))
    out.append(poly(BODY, "none", D["cielo"], 3))
    # Rubor facetado: lo tierno del personaje.
    for cheek in ([(100, 150), (110, 144), (118, 152), (108, 160)],):
        out.append(poly(cheek, shade(P["calabaza"], 0.35)))
        out.append(poly(mirror(cheek), shade(P["calabaza"], 0.35)))
    # Tobera inferior.
    out.append(poly([(132, 194), (168, 194), (160, 210), (140, 210)], D["cielo"]))
    out.append(poly([(150, 194), (168, 194), (160, 210), (150, 210)], shade(D["cielo"], -0.2)))
    return out


def visor():
    return [
        poly(VISOR_PTS, VISOR),
        poly([(112, 104), (126, 92), (150, 92), (124, 138), (112, 138)], shade(VISOR, 0.1)),
        poly(VISOR_PTS, "none", MARCO, 3),
    ]


def eye(kind, cx, cy, side):
    """Un ojo. `side` es -1 (izquierdo) o 1 (derecho), para las formas que no son simétricas."""
    if kind == "open":
        return [poly([(cx, cy - 13), (cx + 8, cy - 6), (cx + 8, cy + 6), (cx, cy + 13), (cx - 8, cy + 6), (cx - 8, cy - 6)], LUZ)]
    if kind == "happy":  # arco hacia arriba
        return [poly([(cx - 10, cy + 6), (cx, cy - 9), (cx + 10, cy + 6), (cx + 5, cy + 6), (cx, cy - 1), (cx - 5, cy + 6)], LUZ)]
    if kind == "squint":  # ojo entrecerrado, de duda
        return [poly([(cx - 9, cy - 2), (cx + 9, cy - 2), (cx + 9, cy + 4), (cx - 9, cy + 4)], LUZ)]
    if kind == "worried":  # el borde superior cae hacia afuera
        inner, outer = cx - 8 * side, cx + 8 * side
        return [poly([(inner, cy - 11), (outer, cy - 2), (outer, cy + 8), (cx, cy + 13), (inner, cy + 8)], LUZ)]
    if kind == "hollow":  # sin datos: anillo a trazos, el mismo lenguaje de «no evaluable»
        ring = [(cx + 9 * math.cos(math.pi / 4 * i + math.pi / 8), cy + 9 * math.sin(math.pi / 4 * i + math.pi / 8)) for i in range(8)]
        return [poly(ring, "none", LUZ, 2.5, "4 3")]
    if kind == "loading":  # hexágono a medio llenar, como el indicador de carga del kit
        hexa = [(cx + 10 * math.cos(math.pi / 3 * i - math.pi / 2), cy + 10 * math.sin(math.pi / 3 * i - math.pi / 2)) for i in range(6)]
        return [poly(hexa, "none", LUZ, 2.5), poly([hexa[0], hexa[1], hexa[2], hexa[3], (cx, cy)], LUZ)]
    if kind == "cross":  # error
        a = 8
        return [
            poly([(cx - a, cy - a + 3), (cx - a + 3, cy - a), (cx + a, cy + a - 3), (cx + a - 3, cy + a)], LUZ),
            poly([(cx + a, cy - a + 3), (cx + a - 3, cy - a), (cx - a, cy + a - 3), (cx - a + 3, cy + a)], LUZ),
        ]
    raise ValueError(kind)


PARCELS = (P["brote"], P["trigo"], P["oliva"], P["tierra"], P["brote"], P["trigo"])


def panel(side, angle, folded=False):
    """Panel solar que es un mosaico de parcelas. Gira sobre su unión con el cuerpo."""
    px, py = PIVOTS["panel-izq"]
    w, h = (30, 40) if folded else (62, 46)
    x0 = px - 14 - w
    out = [poly([(px, py - 3), (px - 16, py - 3), (px - 16, py + 3), (px, py + 3)], D["cielo"])]
    out.append(poly(chamfer(x0, py - h / 2, w, h, 6), MARCO))
    cols, rows = (1, 2) if folded else (3, 2)
    cw, ch = (w - 8) / cols, (h - 8) / rows
    for r in range(rows):
        for c in range(cols):
            color = PARCELS[(r * 3 + c) % len(PARCELS)]
            cell = chamfer(x0 + 4 + c * cw + 1, py - h / 2 + 4 + r * ch + 1, cw - 2, ch - 2, 2)
            out.append(poly(cell, color))
            out.append(poly([cell[0], cell[1], cell[-1]], shade(color, 0.14)))
    if side == 1:
        return group("panel-der", out, f"translate({2 * CX} 0) scale(-1 1) rotate({angle} {px} {py})")
    return group("panel-izq", out, f"rotate({angle} {px} {py})")


def antenna(tilt=0, waves=0, spark=False):
    ax, ay = PIVOTS["antena"]
    out = [
        poly([(ax - 2, ay), (ax + 2, ay), (ax + 2, ay - 28), (ax - 2, ay - 28)], D["cielo"]),
        poly([(ax, ay - 26), (ax - 18, ay - 40), (ax - 13, ay - 22)], P["brote"], D["brote"], 1.5),
        poly([(ax, ay - 28), (ax + 20, ay - 46), (ax + 15, ay - 24)], shade(P["brote"], -0.1), D["brote"], 1.5),
    ]
    for i in range(waves):  # ondas de señal: está guiando o cargando
        r = 12 + i * 9
        arc = [(ax + r * math.cos(a), ay - 44 - r * math.sin(a) * 0.9) for a in (math.radians(d) for d in (35, 62, 90, 118, 145))]
        out.append(f'<polyline points="{pts(arc)}" fill="none" stroke="{P["calabaza"]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    if spark:
        out.append(poly([(ax + 22, ay - 58), (ax + 30, ay - 50), (ax + 24, ay - 48), (ax + 32, ay - 38), (ax + 18, ay - 50), (ax + 25, ay - 52)], P["calabaza"]))
    return group("antena", out, f"rotate({tilt} {ax} {ay})")


# Expresiones: qué hace cada parte. Ningún estado depende del color.
EXPRESSIONS = {
    "reposo": dict(eyes="open", panels=(0, 0)),
    "guia": dict(eyes="open", look=(4, 2), panels=(8, -28), waves=2, tilt=-4),
    "celebra": dict(eyes="happy", panels=(-30, -30), lift=-8, extra="sparkles"),
    "duda": dict(eyes=("open", "squint"), panels=(10, -6), tilt=9, body_tilt=7),
    "preocupada": dict(eyes="worried", panels=(24, 24), tilt=6, extra="drop"),
    "sin-datos": dict(eyes="hollow", panels=(0, 0), folded=True, scale=0.9, extra="mist"),
    "cargando": dict(eyes="loading", panels=(-6, -6), waves=3),
    "error": dict(eyes="cross", panels=(28, -14), tilt=-18, spark=True, body_tilt=-5),
}


def mascot(expression="reposo", decorations=True):
    e = EXPRESSIONS[expression]
    eyes = e["eyes"] if isinstance(e["eyes"], tuple) else (e["eyes"], e["eyes"])
    lx, ly = e.get("look", (0, 0))
    left, right = e["panels"]
    folded = e.get("folded", False)
    parts = [
        panel(-1, left, folded),
        panel(1, right, folded),
        antenna(e.get("tilt", 0), e.get("waves", 0), e.get("spark", False)),
        group("cuerpo", body_shape()),
        group("visor", visor()),
        group("ojo-izq", eye(eyes[0], 134 + lx, 122 + ly, -1)),
        group("ojo-der", eye(eyes[1], 166 + lx, 122 + ly, 1)),
    ]
    transforms = []
    if e.get("lift"):
        transforms.append(f"translate(0 {e['lift']})")
    if e.get("body_tilt"):
        transforms.append(f"rotate({e['body_tilt']} {CX} {CY})")
    if e.get("scale"):
        s = e["scale"]
        transforms.append(f"translate({CX * (1 - s):g} {CY * (1 - s) + 8:g}) scale({s})")
    body = [group("satelite", parts, " ".join(transforms) or None)]
    extra = e.get("extra") if decorations else None
    if extra == "sparkles":
        for x, y, r in ((58, 46, 9), (246, 60, 7), (236, 196, 6)):
            body.append(poly([(x, y - r), (x + r * 0.35, y - r * 0.35), (x + r, y), (x + r * 0.35, y + r * 0.35), (x, y + r), (x - r * 0.35, y + r * 0.35), (x - r, y), (x - r * 0.35, y - r * 0.35)], P["trigo"], D["trigo"], 1.5))
    if extra == "drop":
        body.append(poly([(226, 70), (234, 84), (230, 92), (222, 92), (218, 84)], P["cielo"], D["cielo"], 1.5))
    if extra == "mist":
        for x, y, k in ((86, 208, 1.0), (206, 214, 0.8)):
            body.append(poly([(x - 46 * k, y + 12 * k), (x - 34 * k, y - 4 * k), (x - 8 * k, y - 14 * k), (x + 24 * k, y - 10 * k), (x + 46 * k, y + 4 * k), (x + 40 * k, y + 12 * k)], P["niebla"], BORDE, 1.5))
    return svg(W, H, body)


def inner(markup):
    return markup[markup.index(">") + 1 : markup.rindex("</svg>")]


def place(x, y, scale, expression="reposo", decorations=True):
    return f'<g transform="translate({x:g} {y:g}) scale({scale:g})">{inner(mascot(expression, decorations))}</g>'


def stage(x, y, w, h, night=False):
    """Fondo de prueba: cielo de día o de noche, para comprobar que se lee en los dos."""
    out = [poly(chamfer(x, y, w, h, 16), P["noche"] if night else P["cielo"])]
    if night:
        for i in range(16):
            sx, sy = x + 30 + (i * 137) % (w - 60), y + 24 + (i * 71) % (h - 60)
            out.append(poly([(sx, sy - 3), (sx + 3, sy), (sx, sy + 3), (sx - 3, sy)], LUZ))
    return out


def final_panel():
    b = stage(32, 96, 520, 430) + [place(52, 116, 1.6)]
    b += stage(572, 96, 520, 430, night=True) + [place(592, 116, 1.6)]
    b += [text(32, 556, "De día, sobre cielo", 14, fill=SEC), text(572, 556, "De noche: el visor y los ojos de luz siguen leyéndose", 14, fill=SEC)]
    # Legibilidad en pequeño: a 48 px quedan la silueta, el visor y los dos ojos.
    for i, size in enumerate((96, 64, 48)):
        x = 1130 + i * 150
        b += stage(x, 96, 120, 120)
        b.append(place(x + 60 - size * 0.6, 156 - size * 0.5, size / H))
        b.append(text(x + 60, 240, f"{size} px", 14, fill=SEC, anchor="middle"))
    b += lines(1130, 290, [
        "Concepto",
        "· Cuerpo: una semilla facetada, la misma silueta",
        "  de las semillas del control de prioridad.",
        "· Paneles solares: un mosaico de parcelas",
        "  (brote, trigo, oliva, tierra), no celdas azules.",
        "· Antena: un brote con dos hojas.",
        "· Visor oscuro con dos ojos de luz: toda la",
        "  expresión sale de ojos, paneles y antena.",
        "· Rubor facetado: lo tierno. Sin boca.",
        "Original: no usa formas ni colores de ningún",
        "satélite, agencia o personaje existente.",
    ], 16, 23)
    return b


def expressions_panel():
    notes = {
        "reposo": ("Reposo", "Flota y parpadea."),
        "guia": ("Guía", "Mira y señala con un panel; ondas."),
        "celebra": ("Celebra · verde", "Sube, paneles arriba, ojos en arco."),
        "duda": ("Duda · amarillo", "Se ladea; un ojo entrecerrado."),
        "preocupada": ("Preocupada · rojo", "Paneles caídos; una gota."),
        "sin-datos": ("Sin datos · no evaluable", "Se encoge; ojos en anillo a trazos."),
        "cargando": ("Cargando", "Ojos giran; ondas de señal."),
        "error": ("Error", "Ojos en cruz; chispa en la antena."),
    }
    b = []
    for i, (key, (title, note)) in enumerate(notes.items()):
        x, y = 32 + (i % 4) * 566, 96 + (i // 4) * 300
        b += stage(x, y, 536, 210)
        b.append(place(x + 268 - W * 0.42, y + 4, 0.84, key))
        b.append(text(x, y + 238, title, 18, 700))
        b.append(text(x, y + 262, note, 15, fill=SEC))
    b.append(text(32, 690, "«Sin datos» se encoge y pliega los paneles entre niebla, con ojos en anillo a trazos: no se parece a «preocupada» (R1). La expresión acompaña al texto, nunca lo reemplaza. Los ojos no cambian de color.", 16, fill=SEC))
    return b


def scroll_panel():
    stops = (
        ("1 · Satélite", "reposo", 0.62, "Arriba, en órbita. Saluda y", "presenta qué es AgroSense."),
        ("2 · Región", "guia", 0.54, "Baja con la cámara y señala", "la región con un panel."),
        ("3 · Municipio", "guia", 0.46, "Se acerca al municipio; las", "ondas marcan dónde mirar."),
        ("4 · Lote", "celebra", 0.4, "Queda a un lado del resultado", "y reacciona al semáforo."),
    )
    b = []
    path = []
    for i, (title, key, scale, l1, l2) in enumerate(stops):
        x = 32 + i * 566
        y = 96 + i * 34  # baja con el scroll
        b += stage(x, 96, 536, 300, night=(i == 0))
        cx = x + 268 + (-150 if i % 2 else 150) * (0 if i == 0 else 1) * 0.6
        b.append(place(cx - W * scale / 2, y + 10, scale, key))
        path.append((cx, y + 10 + H * scale / 2))
        b.append(text(x, 426, title, 18, 700))
        b += lines(x, 450, [l1, l2], 15, 21, fill=SEC)
    b += lines(32, 516, [
        "El scroll mueve una línea de tiempo: la mascota baja, se achica y cambia de lado de una estación a la siguiente (GSAP ScrollTrigger; todo valor es función del avance, sin temporizadores).",
        "Entre estaciones gira los paneles y la antena hacia donde va. Con «reducir movimiento» no viaja: aparece ya colocada en cada sección. En modo ligero se usa esta versión 2D.",
    ], 16, 24)
    return b


def rig_panel():
    b = stage(32, 96, 520, 430) + [place(52, 116, 1.6, decorations=False)]
    for name, (px, py) in PIVOTS.items():
        x, y = 52 + px * 1.6, 116 + py * 1.6
        b.append(f'<circle cx="{x:g}" cy="{y:g}" r="7" fill="{P["calabaza"]}" stroke="{WHITE}" stroke-width="2.5"/>')
    b += lines(590, 122, [
        "Partes que se animan (una capa por parte)",
        "· cuerpo — flota arriba y abajo; se ladea y se encoge.",
        "· panel-izq y panel-der — giran sobre su unión con el",
        "  cuerpo (puntos naranja): señalan, se alzan o caen.",
        "· antena — se inclina desde su base; emite ondas.",
        "· ojo-izq y ojo-der — cambian de forma y siguen",
        "  al cursor o al punto de interés (±4 px).",
        "· visor — fijo; da contraste a los ojos.",
        "",
        "En Figma cada parte es un grupo con ese nombre.",
        "En código, la versión 2D es un SVG con los mismos",
        "grupos; la 3D usa los mismos nombres de nodo.",
    ], 16, 24)
    return b


def sheet():
    SW, SH = 2400, 2590
    b = [f'<rect width="{SW}" height="{SH}" fill="{P["cielo"]}"/>']
    b += ridges(SW, 2460, 130)
    b.append(text(40, 84, "Mascota satélite · AgroSense", 48, 600, font=FONT_TITLE))
    b.append(text(40, 122, "HU-171 · Un satélite pequeño, tecnológico y tierno: una semilla con paneles de parcelas y un brote por antena. Es quien guía el descenso del satélite al lote.", 18))
    b.append(section(40, 150, 1560, 590, "Versión 2D", final_panel()))
    b.append(section(1640, 150, 720, 590, "Modelo 3D low-poly", [text(32, 100, "Renders del modelo (ver design/mascota/modelo3d.html)", 16, fill=SEC)]))
    b.append(section(40, 780, 2320, 730, "Expresiones (boceto para HU-172)", expressions_panel()))
    b.append(section(40, 1550, 2320, 590, "Guía con el scroll", scroll_panel()))
    b.append(section(40, 2180, 1560, 250, "", []))
    return svg(SW, SH, b)


def main():
    out = DIR / "svg"
    out.mkdir(exist_ok=True)
    for key in EXPRESSIONS:
        (out / f"mascota-{key}.svg").write_text(mascot(key), encoding="utf-8", newline="\n")
    print(f"{len(EXPRESSIONS)} expresiones en {out}")


if __name__ == "__main__":
    main()
