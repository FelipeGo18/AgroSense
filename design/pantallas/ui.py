"""Piezas de interfaz para las pantallas finales de AgroSense, en el estilo diorama del kit.

Amplía el kit (design/kit) con lo que piden las pantallas de verdad: barra superior, campo de texto,
casilla, interruptor, botón de peligro, enlace y tarjeta. Solo geometría y texto en SVG; los textos
llegan a Figma como capas editables con su fuente.
"""

import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
for folder in ("kit", "mascota", "paisaje"):
    sys.path.insert(0, str(DIR.parent / folder))

from build_kit_svg import BORDE, D, P, WHITE, chamfer, facets, poly, pts, shade, svg  # noqa: E402,F401
from build_paisaje import SCENES  # noqa: E402
from semilla_sputnik import seed_mascot  # noqa: E402
from sheet import FONT_TEXT, FONT_TITLE, SEC, text  # noqa: E402,F401

DESKTOP = (1440, 900)
MOBILE = (390, 844)
OLIVA_CANTO, TRIGO_CANTO, ROJO_CANTO = "#3A4A1D", "#B8862E", "#7E251B"


def inner(markup):
    return markup[markup.index(">") + 1 : markup.rindex("</svg>")]


def group(name, body, x=0, y=0):
    """Grupo con nombre: en Figma queda como una capa con ese nombre."""
    return f'<g id="{name}" transform="translate({x:g} {y:g})">{"".join(body)}</g>'


def paragraph(x, y, rows, size=18, gap=None, **kw):
    gap = gap or round(size * 1.45)
    return [text(x, y + i * gap, row, size, **kw) for i, row in enumerate(rows)]


def width_of(label, size, bold=False):
    """Ancho aproximado de un texto en Atkinson Hyperlegible, para subrayados y botones."""
    return len(label) * size * (0.56 if bold else 0.52)


def scene(name, w, h, clip_id, dim=0.0):
    """Fondo de paisaje que cubre el marco, recortado. `dim` lo oscurece para que el contenido mande."""
    s = max(w / 1440, h / 900)
    ox, oy = (w - 1440 * s) / 2, (h - 900 * s) / 2
    body = f'<g transform="translate({ox:g} {oy:g}) scale({s:g})">{inner(SCENES[name]())}</g>'
    veil = f'<rect width="{w}" height="{h}" fill="{P["noche"]}" fill-opacity="{dim}"/>' if dim else ""
    return [f'<defs><clipPath id="{clip_id}"><rect width="{w}" height="{h}"/></clipPath></defs><g id="fondo" clip-path="url(#{clip_id})">{body}{veil}</g>']


def mascot(x, y, scale, mood="reposo", seed="germinada"):
    return [f'<g id="mascota" transform="translate({x:g} {y:g}) scale({scale:g})">{"".join(seed_mascot(mood, seed))}</g>']


def card(x, y, w, h, name="tarjeta", c=18, depth=8):
    return [group(name, [poly(chamfer(0, depth, w, h, c), BORDE), poly(chamfer(0, 0, w, h, c), WHITE)], x, y)]


def button(x, y, w, label, kind="primary", h=52, name=None):
    top, side, ink = {
        "primary": (D["oliva"], OLIVA_CANTO, WHITE),
        "secondary": (P["trigo"], TRIGO_CANTO, P["noche"]),
        "danger": (P["rojo"], ROJO_CANTO, WHITE),
        "disabled": (P["niebla"], None, SEC),
    }[kind]
    body = []
    if side:
        body += [poly(chamfer(0, 6, w, h, 10), side), poly(chamfer(0, 0, w, h, 10), top)] + facets(0, 0, w, h, 10, top)
        ty = 33
    else:
        body += [poly(chamfer(0, 6, w, h, 10), top)]
        ty = 39
    body.append(text(w / 2, ty, label, 18, 700, ink, anchor="middle"))
    return [group(name or f"boton-{kind}", body, x, y)]


def field(x, y, w, label, value="", placeholder="", state="normal", hint=None, trailing=None, name=None):
    """Campo de texto con su etiqueta encima. Estados: normal, foco, error."""
    stroke = {"normal": BORDE, "foco": P["noche"], "error": D["rojo"]}[state]
    body = [text(0, 0, label, 18, 700)]
    body.append(poly(chamfer(1.5, 13.5, w - 3, 53, 10), WHITE, stroke, 3))
    body.append(poly([(12, 16), (w - 12, 16), (w - 15, 20), (15, 20)], P["niebla"]))  # canto interior: campo hundido
    body.append(text(20, 48, value or placeholder, 18, fill=P["noche"] if value else SEC))
    if state == "foco" and value:
        cx = 20 + width_of(value, 18) + 3
        body.append(f'<rect x="{cx:g}" y="30" width="2" height="24" fill="{P["noche"]}"/>')
    if trailing:
        body.append(text(w - 20, 48, trailing, 16, 700, D["oliva"], anchor="end"))
    if hint:
        body.append(text(0, 90, hint, 15, fill=D["rojo"] if state == "error" else SEC, weight=700 if state == "error" else 400))
    return [group(name or f"campo-{label.lower().split()[0]}", body, x, y)]


def checkbox(x, y, checked=True, name="casilla"):
    body = [poly(chamfer(1.5, 1.5, 29, 29, 6), D["oliva"] if checked else WHITE, D["oliva"] if checked else P["noche"], 3)]
    if checked:
        body.append(f'<polyline points="8,16 14,22 24,10" fill="none" stroke="{WHITE}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    return [group(name, body, x, y)]


def toggle(x, y, on, name="interruptor"):
    """Interruptor: una semilla que corre por un riel biselado."""
    track = poly(chamfer(0, 6, 64, 28, 10), D["oliva"] if on else P["niebla"], D["oliva"] if on else BORDE, 2.5)
    kx = 44 if on else 20
    knob = [(kx, 2), (kx + 13, 12), (kx + 13, 28), (kx, 38), (kx - 13, 28), (kx - 13, 12)]
    body = [track, poly(knob, P["brote"] if on else WHITE, D["brote"] if on else D["cielo"], 2.5)]
    if on:
        body.append(poly([knob[0], knob[1], knob[2], knob[3]], shade(P["brote"], -0.14)))
    return [group(name, body, x, y)]


def link(x, y, label, size=18, anchor="start", bold=True):
    w = width_of(label, size, bold)
    x0 = x - (w if anchor == "end" else w / 2 if anchor == "middle" else 0)
    return [text(x, y, label, size, 700 if bold else 400, D["oliva"], anchor=anchor),
            f'<rect x="{x0:g}" y="{y + 4:g}" width="{w:g}" height="2" fill="{D["oliva"]}"/>']


def logo(x, y, ink=None):
    """Marca: la semilla y el nombre."""
    ink = ink or P["noche"]
    seed = [
        '<path d="M16 9c9 .6 13 9 12 17-.8 8-7 12-13 12S3 34 2 26C1 17 7 9 16 9z" fill="#C8873A" stroke="#1D1D1B" stroke-width="2.5"/>',
        '<path d="M15 9c-5 0-7-4-6-7 4 .6 7 3 6 7zm2 0c4 .6 8-2 8-6-4-.6-7 2-8 6z" fill="#5FA052" stroke="#1D1D1B" stroke-width="2"/>',
    ]
    return [group("marca", seed + [text(40, 33, "AgroSense", 28, 600, ink, FONT_TITLE)], x, y)]


def topbar(w, active=None, user=None):
    """Barra superior: una tabla biselada que flota sobre el paisaje."""
    if w < 700:  # móvil: marca y menú
        body = [poly(chamfer(12, 18, w - 24, 56, 12), BORDE), poly(chamfer(12, 12, w - 24, 56, 12), WHITE)]
        body += logo(26, 18)
        for i in range(3):
            body.append(poly(chamfer(w - 62, 27 + i * 10, 30, 5, 2), P["noche"]))
        return [group("barra", body)]
    body = [poly(chamfer(32, 26, w - 64, 64, 14), BORDE), poly(chamfer(32, 20, w - 64, 64, 14), WHITE)]
    body += logo(56, 30)
    x = 300
    for item in ("Consultar", "Mi finca", "Cómo funciona"):
        on = item == active
        body.append(text(x, 60, item, 18, 700 if on else 400))
        if on:
            body.append(poly(chamfer(x, 68, width_of(item, 18, True), 5, 2), P["calabaza"]))
        x += width_of(item, 18, True) + 44
    if user:
        body.append(poly(chamfer(w - 250, 30, 194, 44, 10), P["niebla"]))
        body.append(f'<g transform="translate({w - 244} 28) scale(0.16)">{"".join(seed_mascot("reposo"))}</g>')
        body.append(text(w - 190, 59, user, 18, 700))
    else:
        body += button(w - 196, 26, 140, "Entrar", "secondary")
    return [group("barra", body)]


def frame(size, body, bg=None):
    w, h = size
    return svg(w, h, [f'<rect width="{w}" height="{h}" fill="{bg or P["cielo"]}"/>'] + body)
