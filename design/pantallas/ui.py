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


# ---------- Pie de página: los cerros del paisaje y la tierra donde se lee el contenido ----------

EARTH, EARTH_INK, EARTH_SOFT = "#3B2A20", "#F6EEDF", "#CDBBA3"
TEAM = "RealE4Life"
SITE = "agrosense.app"  # dominio por confirmar
SOCIAL = (("github", "GitHub"), ("instagram", "Instagram"), ("linkedin", "LinkedIn"), ("youtube", "YouTube"))


def social_icon(kind_, x, y, s=44):
    """Botón de red social con el logo original de la marca (marcas.py); cada uno abre el perfil del equipo."""
    from marcas import BRANDS

    vb, d = BRANDS[kind_]
    _, _, vw, vh = (float(v) for v in vb.split())
    body = [poly(chamfer(0, 4, s, s, 9), shade(EARTH, -0.35)), poly(chamfer(0, 0, s, s, 9), "#FFFFFF")]

    def glyph(size, fill, cx=s / 2, cy=s / 2):
        k = size / max(vw, vh)
        return f'<path transform="translate({cx - vw * k / 2:.2f} {cy - vh * k / 2:.2f}) scale({k:.4f})" d="{d}" fill="{fill}"/>'

    if kind_ == "github":
        body.append(glyph(30, "#181717"))
    elif kind_ == "instagram":  # cuadro con el degradado oficial y el glifo en blanco
        gid = "ig-degradado"
        body.append(f'<defs><radialGradient id="{gid}" cx="0.3" cy="1.07" r="1.3"><stop offset="0" stop-color="#FDF497"/><stop offset="0.05" stop-color="#FDF497"/>'
                    f'<stop offset="0.45" stop-color="#FD5949"/><stop offset="0.6" stop-color="#D6249F"/><stop offset="0.9" stop-color="#285AEB"/></radialGradient></defs>')
        body.append(f'<rect x="{s / 2 - 15}" y="{s / 2 - 15}" width="30" height="30" rx="8" fill="url(#{gid})"/>')
        body.append(glyph(21, "#FFFFFF"))
    elif kind_ == "linkedin":  # cuadro azul oficial con «in» en blanco
        body.append(f'<rect x="{s / 2 - 15}" y="{s / 2 - 15}" width="30" height="30" rx="5" fill="#0A66C2"/>')
        body.append(glyph(18, "#FFFFFF", cy=s / 2 + 1))
    elif kind_ == "youtube":  # botón rojo con el triángulo blanco
        body.append(f'<rect x="{s / 2 - 6}" y="{s / 2 - 6}" width="12" height="12" fill="#FFFFFF"/>')
        body.append(glyph(32, "#FF0000"))
    return [group(f"red-{kind_}", body, x, y)]


def earth_band(w, y, h):
    """Tierra facetada low-poly: tiras de triángulos en tonos muy cercanos, para que el texto se lea."""
    out = [f'<rect x="0" y="{y}" width="{w}" height="{h}" fill="{EARTH}"/>']
    n = max(6, int(w / 120))
    step = w / n
    tones = (0.04, -0.03, 0.02, -0.05, 0.05, -0.02)
    for i in range(n):
        x0, x1 = i * step, (i + 1) * step
        mid = x0 + step * (0.4 + 0.2 * (i % 3) / 2)
        out.append(poly([(x0, y), (x1, y), (mid, y + h * 0.55)], shade(EARTH, tones[i % 6])))
        out.append(poly([(mid, y + h * 0.55), (x1, y + h), (x0, y + h)], shade(EARTH, tones[(i + 3) % 6])))
    return out


def footer(w, y0, mobile=False, above=None):
    """Pie de página común. `above` es el color de la sección de arriba: se ve detrás de los cerros."""
    from sheet import ridges

    hills = 96 if mobile else 130
    body_h = 640 if mobile else 330
    h = hills + body_h
    pad = 20 if mobile else 96
    out = [f'<rect x="0" y="0" width="{w}" height="{hills}" fill="{above or P["cielo"]}"/>', "".join(ridges(w, 0, hills))]
    out += earth_band(w, hills, body_h)
    y = hills + (48 if mobile else 64)
    # marca y frase
    out += logo(pad, y - 34, EARTH_INK)
    out += paragraph(pad, y + 30, ["Datos de la NASA y reglas que se", "pueden leer, para sembrar mejor."], 16, 24, fill=EARTH_SOFT)
    cols = (("Explorar", ("Consultar", "Mi finca", "Cómo funciona")),
            ("Datos y cuenta", ("Fuentes y versión de los datos", "Política de tratamiento de datos", "Reportar un problema")))
    if mobile:
        cy = y + 104
        for title, items in cols:
            out.append(text(pad, cy, title.upper(), 13, 700, EARTH_SOFT))
            for i, it in enumerate(items):
                out += _footer_link(pad, cy + 32 + i * 30, it)
            cy += 32 + len(items) * 30 + 20
        out.append(text(pad, cy, "SÍGANOS", 13, 700, EARTH_SOFT))
        for i, (k, _) in enumerate(SOCIAL):
            out += social_icon(k, pad + i * 56, cy + 16)
        cy += 92
    else:
        for ci, (title, items) in enumerate(cols):
            cx = 520 + ci * 300
            out.append(text(cx, y - 14, title.upper(), 13, 700, EARTH_SOFT))
            for i, it in enumerate(items):
                out += _footer_link(cx, y + 20 + i * 32, it)
        sx = w - pad - (4 * 56 - 12)
        out.append(text(sx, y - 14, "SÍGANOS", 13, 700, EARTH_SOFT))
        for i, (k, _) in enumerate(SOCIAL):
            out += social_icon(k, sx + i * 56, y + 2)
        out += _footer_link(sx, y + 92, SITE + " ↗")
        cy = hills + body_h - 74
    # línea final: derechos reservados
    line_y = cy if mobile else cy
    out.append(f'<rect x="{pad}" y="{line_y}" width="{w - 2 * pad}" height="1" fill="{EARTH_SOFT}" fill-opacity="0.35"/>')
    if mobile:
        out += _footer_link(pad, line_y + 36, SITE + " ↗")
        out += paragraph(pad, line_y + 76, [f"© 2026 {TEAM}. Todos los derechos reservados.", "Hecho para el NASA Space Apps Challenge 2026."], 13, 22, fill=EARTH_SOFT)
    else:
        out.append(text(pad, line_y + 40, f"© 2026 {TEAM}. Todos los derechos reservados.", 14, fill=EARTH_SOFT))
        out.append(text(w - pad, line_y + 40, "Hecho para el NASA Space Apps Challenge 2026", 14, fill=EARTH_SOFT, anchor="end"))
    return [group("pie", out, 0, y0)], h


def long_page(size, body, bg=None):
    """Vista larga: el contenido y, debajo, el pie de página común (specs/05-frontend.md, «Pie de página»)."""
    w, h = size
    foot, fh = footer(w, h, w < 700, above=bg)
    return frame((w, h + fh), body + foot, bg)


def _footer_link(x, y, label):
    wd = width_of(label, 16, True)
    return [text(x, y, label, 16, 700, EARTH_INK), f'<rect x="{x:g}" y="{y + 5:g}" width="{wd:g}" height="2" fill="{P["trigo"]}"/>']
