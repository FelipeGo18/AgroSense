"""Estados del ambiente del lote vivo (tanda 6, HU-187): la hora del día y el clima de ahora sobre el diorama.

El clima en vivo es ambiente: refleja lo que pasa ahora en el municipio (Open-Meteo, HU-175) y nunca cambia un
resultado (decisión 7). «Riego probable» no es clima en vivo: sale del plan de agua y es una estimación (R10).
Todas las láminas usan el mismo lote (maíz en llenado) para comparar solo el ambiente.

    python design/finca/ambiente.py     # escribe svg/ambiente-*.svg
"""

import math
import random
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))
sys.path.insert(0, str(DIR.parent / "kit"))

import cultivos as cv  # noqa: E402
from build_kit_svg import BORDE, D, P, WHITE, chamfer, poly, shade, svg  # noqa: E402
from sheet import FONT_TITLE, SEC, ridges, text  # noqa: E402

CROP = next(c for c in cv.CROPS if c[0] == "maiz")
STAGE = 4
W, H = 440, 470  # tarjeta de cada estado
SCALE = 1.55


# ---------- Cielo ----------

SKIES = {
    "dia": ("#8FC3E8", "#DDEFF7"),
    "atardecer": ("#5B5E9A", "#F2A65A"),
    "noche": ("#0B1226", "#1E2F55"),
    "nublado": ("#8D9AA6", "#C9D2D8"),
    "lluvia": ("#5E6B78", "#8E9AA4"),
    "viento": ("#9CC4DE", "#E4EFF4"),
    "escarcha": ("#0E1A38", "#2C4470"),
    "riego": ("#A9CDE6", "#F2EFD9"),
    "sin-datos": ("#C9D2D8", "#E3E8EB"),
}


def sky(state, gid):
    top, bottom = SKIES[state]
    return [f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient></defs>',
            f'<rect width="{W}" height="{H}" fill="url(#{gid})"/>']


def cloud(x, y, r, color, seed):
    out = []
    for i, (dx, dy, k) in enumerate(((-r, 2, 0.75), (0, -r * 0.3, 1.0), (r, 2, 0.8), (r * 0.4, 4, 0.7), (-r * 0.4, 4, 0.7))):
        out += cv.blob(x + dx, y + dy, r * k, color, seed + i, ry=r * k * 0.7, light=0.08)
    return out


def stars(rnd, n, top=0, bottom=240):
    return [f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(top, bottom):.0f}" r="{rnd.choice((0.8, 1.1, 1.5))}" fill="#FFFFFF" fill-opacity="{rnd.uniform(0.4, 0.95):.2f}"/>'
            for _ in range(n)]


def sun(x, y, r=18, color="#F7D46A", glow="#FFF4C2"):
    return [f'<circle cx="{x}" cy="{y}" r="{r * 2.4}" fill="{glow}" fill-opacity="0.45"/>', f'<circle cx="{x}" cy="{y}" r="{r * 1.5}" fill="{glow}" fill-opacity="0.6"/>',
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>']


def moon(x, y, r=14):
    return [f'<circle cx="{x}" cy="{y}" r="{r * 2}" fill="#DDE6FF" fill-opacity="0.12"/>', f'<circle cx="{x}" cy="{y}" r="{r}" fill="#F2F0E0"/>',
            f'<circle cx="{x + r * 0.45}" cy="{y - r * 0.2}" r="{r * 0.95}" fill="{SKIES["noche"][0]}"/>']


# ---------- Lote ----------

def plot(cx, cy, state):
    """El lote de maíz con el suelo y las plantas según el ambiente."""
    _, _, _, _, plant, rows, cols, ridged, _, *_ = CROP
    top = {"lluvia": "#4A2A18", "riego": "#9A6A40", "escarcha": "#6B5048"}.get(state)
    out = cv.block(0, 0, rows, ridged=ridged, top=top)
    if state == "riego":  # grietas del suelo seco
        rnd = random.Random(4)
        for _ in range(14):
            x, y = cv.at(0, 0, rnd.random(), rnd.random())
            out.append(f'<path d="M{x:.1f} {y:.1f} l4 2 l-2 3 l5 2" stroke="#6B4528" stroke-width="1" fill="none"/>')
    if state == "lluvia":  # charcos
        for u, v, r in ((0.3, 0.7, 9), (0.7, 0.35, 7), (0.55, 0.85, 6)):
            x, y = cv.at(0, 0, u, v)
            out.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{r}" ry="{r * 0.45}" fill="#8EB4D0" fill-opacity="0.7"/>')

    def plant_state(x, y, s, sd):
        body = "".join(plant(x, y, s, sd))
        if state == "viento":  # las plantas se inclinan con el viento
            return [f'<g transform="translate({x:g} {y:g}) skewX(-16) translate({-x:g} {-y:g})">{body}</g>']
        if state == "riego":  # algo marchitas: se encogen y pierden verde
            return [f'<g transform="translate({x:g} {y:g}) scale(1 0.9) translate({-x:g} {-y:g})" opacity="0.92">{body}</g>']
        return [body]

    out += cv.field(0, 0, rows, cols, plant_state, STAGE, seed=sum(map(ord, "maiz")))
    if state == "escarcha":  # capa de hielo sobre la tierra y cristales sobre las hojas
        out.insert(len(out) - len(cv.field(0, 0, rows, cols, plant_state, STAGE, seed=sum(map(ord, "maiz")))),
                   poly([cv.at(0, 0, 0, 0), cv.at(0, 0, 1, 0), cv.at(0, 0, 1, 1), cv.at(0, 0, 0, 1)], "#E8F0FF").replace('fill="#E8F0FF"', 'fill="#E8F0FF" fill-opacity="0.45"'))
        rnd = random.Random(9)
        for _ in range(140):
            x, y = cv.at(0, 0, rnd.random(), rnd.random())
            y -= rnd.uniform(0, 70)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.choice((0.7, 1.0, 1.3))}" fill="#FFFFFF" fill-opacity="{rnd.uniform(0.6, 1):.2f}"/>')
    return [f'<g id="lote" transform="translate({cx} {cy}) scale({SCALE})">{"".join(out)}</g>']


# ---------- Efectos sobre la escena ----------

def rain(rnd, n=90, slant=-6):
    return [f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x + slant:.0f}" y2="{y + 14:.0f}" stroke="#DCE8F2" stroke-width="1.3" stroke-opacity="0.75" stroke-linecap="round"/>'
            for x, y in ((rnd.uniform(-10, W + 10), rnd.uniform(60, H - 40)) for _ in range(n))]


def wind_streaks(rnd):
    out = []
    for _ in range(9):
        x, y, ln = rnd.uniform(0, W - 120), rnd.uniform(70, 300), rnd.uniform(60, 140)
        out.append(f'<path d="M{x:.0f} {y:.0f} q{ln / 2:.0f} -8 {ln:.0f} 0 t{ln * 0.3:.0f} 6" stroke="#FFFFFF" stroke-width="2" stroke-opacity="0.7" fill="none" stroke-linecap="round"/>')
    for _ in range(7):  # hojas que vuelan
        x, y = rnd.uniform(40, W - 40), rnd.uniform(90, 300)
        out += cv.leaf(x, y, rnd.uniform(0, 180), 7, 4, rnd.choice(("#6FA03C", "#9CC152", "#C9A86A")))
    return out


def tint(color, opacity):
    return [f'<rect width="{W}" height="{H}" fill="{color}" fill-opacity="{opacity}"/>']


def chip(x, y, label, fill, ink, stroke=None, dash=None, icon=None):
    w = len(label) * 7.4 + (44 if icon else 24)
    out = [poly(chamfer(x, y, w, 30, 8), fill, stroke, 2 if stroke else 0, dash)]
    tx = x + 12
    if icon == "gota":
        out += [poly([(x + 18, y + 6), (x + 25, y + 17), (x + 22, y + 24), (x + 14, y + 24), (x + 11, y + 17)], P["cielo"], D["cielo"], 1.5)]
        tx = x + 34
    out.append(text(tx, y + 20, label, 14, 700, ink))
    return out


# ---------- Estados ----------

STATES = (
    ("dia", "Día", "Hora local entre la salida y la puesta del sol (se calcula con la posición del municipio)"),
    ("atardecer", "Atardecer y amanecer", "Media hora antes y después de la puesta o la salida del sol"),
    ("noche", "Noche", "Después de la puesta del sol; luna y estrellas"),
    ("nublado", "Nublado", "Nubosidad de ahora mayor que 70 % (Open-Meteo)"),
    ("lluvia", "Lluvia", "Lluvia de ahora mayor que 0,2 mm (Open-Meteo); el suelo se moja"),
    ("viento", "Viento", "Viento de ahora mayor que 25 km/h (Open-Meteo); las matas se inclinan"),
    ("escarcha", "Escarcha", "Temperatura de ahora menor que 2 °C (Open-Meteo); cristales sobre hojas y tierra"),
    ("riego", "Riego probable", "El plan de agua marca déficit este mes: suelo seco. Es una estimación (R10)"),
    ("sin-datos", "Sin condición en vivo", "Open-Meteo no respondió: clima neutro y se dice"),
)


def scene(state):
    rnd = random.Random(sum(map(ord, state)))
    b = sky(state, f"cielo-{state}")
    if state in ("noche", "escarcha"):
        b += stars(rnd, 70) + moon(340, 70)
    elif state == "atardecer":
        b += sun(330, 210, 22, "#F28C4A", "#F7C08A")
    elif state in ("dia", "viento", "riego"):
        b += sun(350, 66, 18 if state != "riego" else 22)
    if state in ("nublado", "lluvia"):
        col = "#E3E8EB" if state == "nublado" else "#7E8A96"
        for x, y, r, sd in ((90, 70, 30, 1), (250, 50, 36, 2), (380, 95, 28, 3), (170, 120, 24, 4)):
            b += cloud(x, y, r, col, sd)
    elif state in ("dia", "viento", "atardecer"):
        for x, y, r, sd in ((90, 80, 18, 5), (220, 120, 14, 6)):
            b += cloud(x + (30 if state == "viento" else 0), y, r, "#FFFFFF" if state != "atardecer" else "#F2C9A8", sd)
    hills = "".join(ridges(W, 0, 90))
    b.append(f'<g transform="translate(0 210)" opacity="{0.55 if state in ("noche", "escarcha") else 0.9}">{hills}</g>')
    b.append(f'<rect y="300" width="{W}" height="{H - 300}" fill="{shade(cv.GRASS, -0.15) if state != "escarcha" else "#9DB6A8"}"/>')
    b += plot(W / 2, 290, state)
    if state == "lluvia":
        b += rain(rnd)
    if state == "viento":
        b += wind_streaks(rnd)
    if state in ("noche", "escarcha"):
        b += tint("#0B1A3A", 0.28)
    if state == "atardecer":
        b += tint("#F28C4A", 0.12)
    if state == "escarcha":
        b += tint("#BFD8FF", 0.08)
    if state == "nublado":
        b += tint("#8D9AA6", 0.08)
    if state == "sin-datos":
        b += tint("#E3E8EB", 0.35)
    # rótulo de la escena (lo que también ve el agricultor)
    if state == "riego":
        b += chip(16, H - 46, "Riego probable este mes · estimación", WHITE, P["noche"], BORDE, None, "gota")
    elif state == "sin-datos":
        b += chip(16, H - 46, "Sin condición en vivo · clima neutro", WHITE, P["noche"], D["cielo"], "4 3")
    else:
        names = {"dia": "Soleado", "atardecer": "Atardecer", "noche": "Noche despejada", "nublado": "Nublado", "lluvia": "Lloviendo",
                 "viento": "Viento fuerte", "escarcha": "Escarcha · 1 °C"}
        b += chip(16, H - 46, f"Ahora en Samacá: {names[state]}", "#FFFFFF", P["noche"], None)
    return b


def card(state, title, rule, x, y):
    clip = f"recorte-{state}"
    body = [f'<defs><clipPath id="{clip}"><path d="M14 0 H{W - 14} L{W} 14 V{H - 14} L{W - 14} {H} H14 L0 {H - 14} V14 Z"/></clipPath></defs>',
            f'<g clip-path="url(#{clip})">{"".join(scene(state))}</g>',
            poly(chamfer(0, 0, W, H, 14), "none", BORDE, 2)]
    body.append(text(0, H + 34, title, 22, 600, font=FONT_TITLE))
    words, line, lines = rule.split(" "), "", []
    for wd in words:
        if len(line) + len(wd) > 58:
            lines.append(line.strip())
            line = ""
        line += wd + " "
    lines.append(line.strip())
    body += [text(0, H + 60 + i * 20, ln, 14, fill=SEC) for i, ln in enumerate(lines)]
    return f'<g id="estado-{state}" transform="translate({x} {y})">{"".join(body)}</g>'


def sheet():
    w, cols = 1560, 3
    gap_x, gap_y = 60, 150
    rows = math.ceil(len(STATES) / cols)
    h = 220 + rows * (H + gap_y)
    b = [f'<rect width="{w}" height="{h}" fill="{P["niebla"]}"/>', text(60, 80, "Estados del ambiente del lote vivo", 40, 600, font=FONT_TITLE),
         text(60, 118, "El mismo lote (maíz en llenado) con la hora del día y el clima de ahora. El clima en vivo es ambiente: nunca cambia un resultado (decisión 7).", 16, fill=SEC),
         text(60, 142, "Se combinan por capas: hora del día (día, atardecer, noche) + condición (nublado, lluvia, viento, escarcha) + suelo (mojado o seco por «riego probable»).", 16, fill=SEC)]
    for i, (state, title, rule) in enumerate(STATES):
        x = 60 + (i % cols) * (W + gap_x)
        y = 190 + (i // cols) * (H + gap_y)
        b.append(card(state, title, rule, x, y))
    return svg(w, h, b)


if __name__ == "__main__":
    out = DIR / "svg"
    (out / "ambiente-estados.svg").write_text(sheet(), encoding="utf-8", newline="\n")
    print("ambiente-estados")
