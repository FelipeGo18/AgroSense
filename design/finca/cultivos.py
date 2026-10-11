"""Catálogo visual de cultivos y sus etapas, en el estilo diorama low-poly: lotes poblados, follaje frondoso.

Cada etapa muestra un lote sembrado de verdad: plantas en surcos que casi cubren la tierra, con la forma de la mata
real. La duración de cada etapa sale del catálogo (`crop_stages`, grados-día, HU-150); aquí solo se define cómo se
ve. El lote vivo de Mi finca (HU-187) usa estas mismas funciones. Se construye por lotes de cinco cultivos.

    python design/finca/cultivos.py     # escribe svg/cultivo-*.svg (una lámina por cultivo)
"""

import math
import random
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parent / "kit"))

from build_kit_svg import BORDE, D, P, WHITE, chamfer, poly, shade, svg  # noqa: E402
from sheet import FONT_TITLE, SEC, text  # noqa: E402

SOIL_TOP, SOIL_SIDE, SOIL_DEEP = "#6B4026", P["tierra"], D["tierra"]
GRASS, GRASS_D = "#8DBA4F", "#6E9A3A"
LEAF = {"papa": "#4F7F35", "maiz": "#6FA03C", "arveja": "#7DB04A", "zanahoria": "#5E9B3A", "cebolla": "#6E9C86"}


# ---------- Formas base ----------

def blob(x, y, r, color, seed=0, ry=None, light=0.14):
    """Masa de follaje facetada: polígono irregular con su cara en luz arriba a la izquierda."""
    rnd = random.Random(seed)
    ry = ry or r * 0.82
    n = 9
    pts = [(x + r * (0.82 + 0.18 * rnd.random()) * math.cos(2 * math.pi * i / n),
            y + ry * (0.82 + 0.18 * rnd.random()) * math.sin(2 * math.pi * i / n)) for i in range(n)]
    out = [poly(pts, color)]
    out.append(poly([pts[4], pts[5], pts[6], pts[7], (x, y)], shade(color, light)))
    out.append(poly([pts[0], pts[1], pts[2], (x, y)], shade(color, -0.16)))
    return out


def blade(x, y, ang, length, width, color, bend=0.0):
    """Hoja larga y curva (maíz, cebolla): se afina hacia la punta."""
    a = math.radians(ang)
    tip = (x + length * math.cos(a), y - length * math.sin(a) + bend * length)
    mid = (x + length * 0.5 * math.cos(a), y - length * 0.5 * math.sin(a) + bend * length * 0.2)
    nx, ny = -math.sin(a) * width / 2, -math.cos(a) * width / 2
    return [poly([(x - nx * 0.4, y - ny * 0.4), (mid[0] - nx, mid[1] - ny), tip, (mid[0] + nx, mid[1] + ny), (x + nx * 0.4, y + ny * 0.4)], color),
            poly([(x, y), (mid[0] + nx, mid[1] + ny), tip, mid], shade(color, -0.14))]


def leaf(x, y, ang, length, width, color, shade_side=True):
    """Hoja low-poly: rombo alargado con una mitad en sombra."""
    a = math.radians(ang)
    tip = (x + length * math.cos(a), y - length * math.sin(a))
    mid = (x + length * 0.45 * math.cos(a), y - length * 0.45 * math.sin(a))
    n = (math.cos(a + math.pi / 2) * width / 2, -math.sin(a + math.pi / 2) * width / 2)
    left, right = (mid[0] + n[0], mid[1] + n[1]), (mid[0] - n[0], mid[1] - n[1])
    out = [poly([(x, y), left, tip, right], color)]
    if shade_side:
        out.append(poly([(x, y), tip, right], shade(color, -0.14)))
    return out


def gem(x, y, r, color, ry=None):
    ry = ry or r
    pts = [(x + r * math.cos(math.pi / 3 * i), y + ry * math.sin(math.pi / 3 * i)) for i in range(6)]
    return [poly(pts, color), poly([pts[3], pts[4], pts[5], (x, y)], shade(color, 0.2))]


def flower(x, y, r, petal, center="#E8C34B"):
    return [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{petal}" stroke="{shade(petal, -0.25)}" stroke-width="0.8"/>',
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 0.38:.1f}" fill="{center}"/>']


# ---------- Lote: bloque de tierra con surcos y plantas en filas ----------

A, B, DEPTH = 100, 50, 50
RIM = 0.9  # la tierra ocupa el 90 % de la parcela; el resto es el borde de pasto


def corners(cx, cy):
    return (cx, cy - B), (cx + A, cy), (cx, cy + B), (cx - A, cy)


def at(cx, cy, u, v):
    """Punto de la cara superior: u a lo largo del surco (N→E), v entre surcos (N→W), ambos de 0 a 1."""
    N, E, _, W = corners(cx, cy)
    u, v = (1 - RIM) / 2 + u * RIM, (1 - RIM) / 2 + v * RIM
    return (N[0] + (E[0] - N[0]) * u + (W[0] - N[0]) * v, N[1] + (E[1] - N[1]) * u + (W[1] - N[1]) * v)


def block(cx, cy, rows, ridged=False, cut=None, top=None):
    N, E, S, W = corners(cx, cy)
    top = top or SOIL_TOP
    out = [poly([W, S, (S[0], S[1] + DEPTH), (W[0], W[1] + DEPTH)], SOIL_SIDE),
           poly([S, E, (E[0], E[1] + DEPTH), (S[0], S[1] + DEPTH)], SOIL_DEEP),
           poly([W, S, (S[0], S[1] + 8), (W[0], W[1] + 8)], GRASS_D), poly([S, E, (E[0], E[1] + 8), (S[0], S[1] + 8)], shade(GRASS_D, -0.15)),
           poly([N, E, S, W], GRASS),
           poly([at(cx, cy, 0, 0), at(cx, cy, 1, 0), at(cx, cy, 1, 1), at(cx, cy, 0, 1)], top)]
    for r in range(rows):  # surcos (o caballones aporcados para la papa)
        v = (r + 0.5) / rows
        p0, p1 = at(cx, cy, 0.04, v), at(cx, cy, 0.96, v)
        if ridged:
            out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" stroke="{shade(top, 0.12)}" stroke-width="9" stroke-linecap="round"/>')
            out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1] + 3:.1f}" x2="{p1[0]:.1f}" y2="{p1[1] + 3:.1f}" stroke="{shade(top, -0.12)}" stroke-width="3" stroke-linecap="round"/>')
        else:
            out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" stroke="{shade(top, -0.1)}" stroke-width="4" stroke-linecap="round"/>')
    if cut:
        out += cut(cx, cy)
    return out


def field(cx, cy, rows, cols, plant, s, seed=1, jitter=0.03, basin=False):
    """Plantas en filas, dibujadas de atrás hacia adelante para que se tapen bien."""
    rnd = random.Random(seed)
    spots = []
    for r in range(rows):
        for c in range(cols):
            u = (c + 0.5) / cols + rnd.uniform(-jitter, jitter)
            v = (r + 0.5) / rows + rnd.uniform(-jitter, jitter)
            spots.append(at(cx, cy, u, v) + (rnd.randint(0, 999),))
    out = []
    rx = A * RIM / cols * 0.55
    for x, y, sd in sorted(spots, key=lambda p: p[1]):
        if basin:  # plateo: círculo de tierra limpia alrededor del árbol
            out.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx * 0.95:.1f}" ry="{rx * 0.48:.1f}" fill="{SOIL_TOP}"/>')
        if s > 1:  # sombra de contacto: la planta pesa sobre la tierra
            out.append(f'<ellipse cx="{x + 2:.1f}" cy="{y + 1.5:.1f}" rx="{rx:.1f}" ry="{rx * 0.45:.1f}" fill="#000" fill-opacity="0.22"/>')
        out += plant(x, y, s, sd)
    return out


# ---------- Lote 1: cultivos del piloto (altiplano) ----------

def papa(x, y, s, sd):
    """Mata frondosa y redonda sobre el caballón; flores lila y blancas; amarillea al final."""
    g = LEAF["papa"]
    if s == 1:
        return blob(x, y - 4, 5, shade(g, 0.15), sd)
    k = (0, 0, 0.75, 1.0, 1.0, 0)[s]
    col = g if s < 4 else "#9A9A45"
    out = blob(x - 7 * k, y - 8 * k, 11 * k, shade(col, -0.05), sd) + blob(x + 7 * k, y - 9 * k, 11 * k, col, sd + 1) + blob(x, y - 17 * k, 12 * k, shade(col, 0.06), sd + 2)
    if s == 3:
        out += flower(x - 4, y - 26, 2.6, "#C9B3E6") + flower(x + 5, y - 23, 2.6, WHITE) + flower(x + 1, y - 29, 2.4, "#C9B3E6")
    if s == 4:
        out += [f'<circle cx="{x + 4:.1f}" cy="{y - 18:.1f}" r="3" fill="#D8C24A"/>']
    return out


def papa_harvest(cx, cy):
    """Cosecha: las matas se retiran y los tubérculos quedan sobre el caballón."""
    out = []
    rnd = random.Random(5)
    for r in range(4):
        for c in range(6):
            x, y = at(cx, cy, (c + 0.5) / 6 + rnd.uniform(-0.03, 0.03), (r + 0.5) / 4)
            out += gem(x - 3, y - 2, 4.2, "#D9A066", 3.2) + gem(x + 4, y + 1, 3.6, "#C98E54", 2.8)
    return out


def papa_cut(cx, cy):
    """Corte lateral en llenado: los tubérculos bajo el caballón."""
    return (gem(cx - 40, cy + 34, 6.5, "#D9A066", 4.8) + gem(cx - 62, cy + 26, 5.5, "#C98E54", 4) +
            gem(cx - 22, cy + 44, 5.5, "#D9A066", 4) + gem(cx + 30, cy + 40, 6, "#C98E54", 4.4))


def maiz(x, y, s, sd):
    """Caña alta con hojas largas que se arquean; espiga arriba y mazorca con pelo."""
    g = LEAF["maiz"]
    h = (0, 0, 26, 52, 58, 58)[s]
    if s == 1:
        return blade(x, y, 70, 9, 3, g) + blade(x, y, 110, 8, 3, shade(g, 0.1))
    col = g if s < 5 else "#C9A86A"
    stalk = shade(col, -0.25)
    out = [poly([(x - 1.6, y), (x + 1.6, y), (x + 1.2, y - h), (x - 1.2, y - h)], stalk)]
    for i in range(5 if s >= 3 else 4):
        yy = y - 6 - i * h / 5.5
        right = i % 2 == 0
        out += blade(x, yy, 25 if right else 155, 18 + (4 - i) * 2, 5, shade(col, 0.06 * (i % 2)), bend=0.35)
    if s >= 3:
        tas = "#D9C27A" if s < 5 else "#B8935A"
        out += blade(x, y - h, 80, 9, 2, tas) + blade(x, y - h, 105, 8, 2, tas) + blade(x, y - h, 60, 7, 2, tas)
    if s >= 4:
        ear = "#9CC152" if s == 4 else "#E3C04A"
        out += [poly([(x + 1, y - h * 0.48), (x + 7, y - h * 0.62), (x + 6, y - h * 0.36), (x + 1, y - h * 0.32)], ear, shade(ear, -0.3), 0.8)]
        out += [f'<line x1="{x + 7:.1f}" y1="{y - h * 0.62:.1f}" x2="{x + 10:.1f}" y2="{y - h * 0.7:.1f}" stroke="#C9764A" stroke-width="1.4"/>']
    return out


def arveja_trellis(cx, cy, rows, s):
    """Espaldera: postes al inicio y al final de cada surco con dos hilos."""
    out = []
    for r in range(rows):
        v = (r + 0.5) / rows
        a0, a1 = at(cx, cy, 0.03, v), at(cx, cy, 0.97, v)
        for p in (a0, a1):
            out.append(f'<line x1="{p[0]:.1f}" y1="{p[1]:.1f}" x2="{p[0]:.1f}" y2="{p[1] - 44:.1f}" stroke="{D["tierra"]}" stroke-width="2.4"/>')
        for hgt in (22, 40):
            out.append(f'<line x1="{a0[0]:.1f}" y1="{a0[1] - hgt:.1f}" x2="{a1[0]:.1f}" y2="{a1[1] - hgt:.1f}" stroke="#D8CDB8" stroke-width="1"/>')
    return out


def arveja(x, y, s, sd):
    """Enredadera que sube por la espaldera y forma un seto; flores blancas y vainas."""
    g = LEAF["arveja"]
    if s == 1:
        return blob(x, y - 3, 4, g, sd)
    h = (0, 0, 20, 36, 40, 40)[s]
    col = g if s < 5 else "#C9B07A"
    out = []
    for i in range(4):
        out += blob(x + (-2 if i % 2 else 2), y - 6 - i * h / 4.2, 7.5, shade(col, (-0.06, 0.04, 0.0, 0.07)[i]), sd + i, ry=6)
    if s == 3:
        out += flower(x + 4, y - h * 0.6, 2.4, WHITE) + flower(x - 3, y - h * 0.85, 2.2, WHITE)
    if s >= 4:
        pod = "#B7DA7A" if s == 4 else "#C9B07A"
        out += [f'<ellipse cx="{x + 5:.1f}" cy="{y - h * 0.45:.1f}" rx="2.2" ry="6" fill="{pod}" stroke="{shade(pod, -0.35)}" stroke-width="0.8"/>',
                f'<ellipse cx="{x - 5:.1f}" cy="{y - h * 0.7:.1f}" rx="2.2" ry="6" fill="{pod}" stroke="{shade(pod, -0.35)}" stroke-width="0.8"/>']
    return out


def zanahoria(x, y, s, sd):
    """Follaje fino y plumoso que cubre el surco; hombro naranja asomando; cosecha en manojos."""
    g = LEAF["zanahoria"]
    if s == 1:
        return blade(x, y, 80, 6, 2, g)
    if s == 5:
        return [poly([(x - 2, y), (x + 9, y - 3), (x - 1, y + 3)], "#E07B24")] + blade(x - 2, y, 140, 9, 3, g)
    k = (0, 0, 0.6, 0.85, 1.0)[s]
    out = []
    for ang in (55, 75, 95, 115, 135, 65, 125):
        out += blade(x, y, ang, 14 * k, 3 * k, shade(g, 0.05 * ((ang // 10) % 3 - 1)))
        tip = (x + 14 * k * math.cos(math.radians(ang)), y - 14 * k * math.sin(math.radians(ang)))
        out += blob(tip[0], tip[1], 3.2 * k, shade(g, 0.08), sd + ang, light=0.1)
    if s >= 3:
        out += [poly([(x - 2.5, y + 1), (x + 2.5, y + 1), (x + 1.5, y - 2), (x - 1.5, y - 2)], "#E07B24")]
    return out


def cebolla(x, y, s, sd):
    """Hojas huecas y erguidas, verde azulado; el bulbo morado engrosa en la base y al final las hojas se doblan."""
    g = LEAF["cebolla"]
    if s == 1:
        return blade(x, y, 88, 8, 2, g)
    k = (0, 0, 0.6, 0.9, 1.0, 1.0)[s]
    out = []
    if s >= 3:
        r = (0, 0, 0, 3.5, 5.5, 6)[s]
        out += gem(x, y - r * 0.6, r, "#9A3E66", r * 0.85)
    col = g if s < 5 else "#B7A86A"
    for i, ang in enumerate((76, 86, 96, 106, 82, 100)):
        out += blade(x, y - 2, ang if s < 5 else ang - 55, 22 * k, 2.6, shade(col, 0.05 * (i % 3 - 1)), bend=0.0 if s < 5 else 0.3)
    return out


# ---------- Lote 2: árboles frutales (huerto con pasto y plateo) ----------

TREE_SCALE = 1.85

TREES = {  # tronco, lóbulos de la copa (dx, dy, r), color de copa, flor, fruto verde y maduro, forma y tamaño del fruto, frutos
    "mango": dict(trunk=13, lobes=((-11, -1, 10), (11, -1, 10), (0, -8, 12), (-5, 5, 9), (6, 5, 9)), leaf="#2F6B2E",
                  flower="panicle", flower_col="#E8A26A", green="#7FA83A", ripe="#F2A33A", blush="#D9533A", shape="oval", size=3.0, n=7),
    "naranja": dict(trunk=10, lobes=((-8, 0, 9.5), (8, 0, 9.5), (0, -8, 10.5), (0, 6, 9)), leaf="#3E7D35",
                    flower="dots", flower_col="#FFFFFF", green="#7FA83A", ripe="#F28C28", shape="round", size=2.7, n=9),
    "limon": dict(trunk=9, lobes=((-9, 1, 8), (8, -1, 8.5), (-1, -8, 8.5), (3, 6, 7.5), (-6, -4, 6)), leaf="#5A9A3E",
                  flower="dots", flower_col="#F4E9F7", green="#6FB03A", ripe="#B9D94A", shape="oval", size=2.3, n=9),
    "mandarina": dict(trunk=8, lobes=((-7, 0, 8), (7, 0, 8), (0, -6, 9), (0, 5, 8)), leaf="#3F7A33",
                      flower="dots", flower_col="#FFFFFF", green="#7FA83A", ripe="#F07A1E", shape="flat", size=2.4, n=11),
    "tomate_arbol": dict(trunk=14, lobes=((-12, -2, 9), (12, -2, 9), (0, -6, 10), (-6, 2, 8), (6, 2, 8)), leaf="#4E8F3A",
                         flower="dots", flower_col="#F4D9E8", green="#7FA83A", ripe="#D9552A", shape="oval", size=3.0, n=8, hang=True),
    "aguacate": dict(trunk=15, lobes=((0, -15, 9.5), (-8, -5, 9.5), (8, -5, 9.5), (0, 4, 10.5), (-4, -11, 7)), leaf="#2E5E2A",
                     flower="dots", flower_col="#D7D98A", green="#4C7A2E", ripe="#2B2A3A", shape="pear", size=3.0, n=6),
}


def stem_line(x, y, h, color, w):
    return [f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y - h:.1f}" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>']


def fruit(x, y, spec, ripe):
    col = spec["ripe"] if ripe else spec["green"]
    r = spec["size"]
    if spec["shape"] == "round":
        return gem(x, y, r, col)
    if spec["shape"] == "flat":
        return gem(x, y, r * 1.1, col, r * 0.82)
    if spec["shape"] == "pear":
        return [f'<line x1="{x:.1f}" y1="{y - r * 2.2:.1f}" x2="{x:.1f}" y2="{y - r:.1f}" stroke="#5A4630" stroke-width="0.9"/>',
                poly([(x, y - r * 1.4), (x + r * 0.7, y - r * 0.4), (x + r, y + r * 0.6), (x, y + r * 1.2), (x - r, y + r * 0.6), (x - r * 0.7, y - r * 0.4)], col),
                poly([(x, y - r * 1.4), (x - r * 0.7, y - r * 0.4), (x - r, y + r * 0.6), (x, y + r * 1.2)], shade(col, 0.2))]
    out = [f'<line x1="{x:.1f}" y1="{y - r * 2.4:.1f}" x2="{x:.1f}" y2="{y - r:.1f}" stroke="#5A4630" stroke-width="0.9"/>'] if spec.get("blush") or spec.get("hang") else []
    out += gem(x, y, r * 0.8, col, r * 1.15)
    if ripe and spec.get("blush"):
        out.append(f'<ellipse cx="{x + r * 0.3:.1f}" cy="{y - r * 0.3:.1f}" rx="{r * 0.45:.1f}" ry="{r * 0.6:.1f}" fill="{spec["blush"]}" fill-opacity="0.8"/>')
    return out


def tree(kind):
    spec = TREES[kind]

    def draw(x, y, s, sd):
        """Árbol dibujado a escala 1 y agrandado desde su base, para que llene la parcela."""
        return [f'<g transform="translate({x:g} {y:g}) scale({TREE_SCALE}) translate({-x:g} {-y:g})">{"".join(draw1(x, y, s, sd))}</g>']

    def draw1(x, y, s, sd):
        rnd = random.Random(sd)
        if s == 0:  # plántula con su tutor
            return ([f'<line x1="{x + 3:.1f}" y1="{y:.1f}" x2="{x + 3:.1f}" y2="{y - 14:.1f}" stroke="#B8935A" stroke-width="1.4"/>'] +
                    stem_line(x, y, 9, "#6B4A2E", 1.6) + blob(x - 3, y - 10, 3.2, spec["leaf"], sd) + blob(x + 2, y - 12, 3.2, shade(spec["leaf"], 0.1), sd + 1))
        k = (0, 0.42, 0.7, 1.0, 1.0, 1.0)[s]
        th = spec["trunk"] * k
        cy0 = y - th - 6 * k
        out = [poly([(x - 2.2 * k, y), (x + 2.2 * k, y), (x + 1.6 * k, y - th - 2), (x - 1.6 * k, y - th - 2)], "#6B4A2E"),
               poly([(x, y), (x + 2.2 * k, y), (x + 1.6 * k, y - th - 2), (x, y - th - 2)], "#56391F")]
        lobes = sorted(spec["lobes"], key=lambda lb: lb[1])
        for i, (dx, dy, r) in enumerate(lobes):  # de atrás hacia adelante
            out += blob(x + dx * k, cy0 + dy * k, r * k, shade(spec["leaf"], (0.0, -0.06, 0.05, -0.03, 0.08)[i % 5]), sd + i, light=0.18)
        front = [(x + dx * k + rnd.uniform(-r, r) * 0.6 * k, cy0 + dy * k + rnd.uniform(-r, r) * 0.45 * k) for dx, dy, r in spec["lobes"] for _ in range(3)]
        rnd.shuffle(front)
        if s == 3:
            for fx, fy in front[:9]:
                if spec["flower"] == "panicle":
                    out.append(poly([(fx - 1.6, fy), (fx + 1.6, fy), (fx, fy - 6)], spec["flower_col"]))
                else:
                    out.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="1.5" fill="{spec["flower_col"]}"/>')
        if s >= 4:
            for fx, fy in front[: spec["n"]]:
                out += fruit(fx, fy + 2, spec, s == 5)
        return out

    return draw


# ---------- Lote 3: musáceas y enredaderas ----------

def scaled(fn, k):
    """Dibuja la planta a escala 1 y la agranda desde su base."""
    def draw(x, y, s, sd):
        return [f'<g transform="translate({x:g} {y:g}) scale({k}) translate({-x:g} {-y:g})">{"".join(fn(x, y, s, sd))}</g>']
    return draw


def musa_leaf(x, y, ang, length, color, torn=False):
    """Hoja de plátano: larga y ancha, con nervio central; las viejas se rasgan."""
    a = math.radians(ang)
    tip = (x + length * math.cos(a), y - length * math.sin(a) * 0.45 + length * 0.34)  # la hoja se arquea y cae
    nx, ny = -math.sin(a) * 4.5, -math.cos(a) * 4.5
    m1 = (x + (tip[0] - x) * 0.35, y + (tip[1] - y) * 0.35 - 2)
    m2 = (x + (tip[0] - x) * 0.7, y + (tip[1] - y) * 0.7 - 1)
    out = [poly([(x, y), (m1[0] + nx, m1[1] + ny), (m2[0] + nx, m2[1] + ny), tip, (m2[0] - nx * 0.8, m2[1] - ny * 0.8), (m1[0] - nx * 0.8, m1[1] - ny * 0.8)], color),
           poly([(x, y), (m1[0] - nx * 0.8, m1[1] - ny * 0.8), (m2[0] - nx * 0.8, m2[1] - ny * 0.8), tip], shade(color, -0.14)),
           f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{tip[0]:.1f}" y2="{tip[1]:.1f}" stroke="{shade(color, 0.25)}" stroke-width="0.8"/>']
    if torn:
        for t in (0.45, 0.62, 0.8):
            px, py = x + (tip[0] - x) * t, y + (tip[1] - y) * t
            out.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px + nx * 0.9:.1f}" y2="{py + ny * 0.9:.1f}" stroke="#FFFFFF" stroke-width="0.9" opacity="0.7"/>')
    return out


def musa(kind):
    """Plátano (racimo grande que se cosecha verde) y banano (racimo de dedos curvos que madura amarillo)."""
    ripe = {"platano": "#B8C24A", "banano": "#F0CE3A"}[kind]
    finger = {"platano": (3.2, 7.5), "banano": (2.4, 5.5)}[kind]

    def draw(x, y, s, sd):
        rnd = random.Random(sd)
        if s == 0:  # hijuelo
            return [poly([(x - 2, y), (x + 2, y), (x + 1.5, y - 8), (x - 1.5, y - 8)], "#7E9B4A")] + musa_leaf(x, y - 8, 60, 10, "#6FB04A") + musa_leaf(x, y - 8, 140, 9, "#5FA34A")
        k = (0, 0.45, 0.75, 1.0, 1.0, 1.0)[s]
        h = 30 * k
        out = [poly([(x - 3.4 * k, y), (x + 3.4 * k, y), (x + 2.4 * k, y - h), (x - 2.4 * k, y - h)], "#7E9B4A"),
               poly([(x, y), (x + 3.4 * k, y), (x + 2.4 * k, y - h), (x, y - h)], "#6A8540")]
        for j in range(1, 4):  # vainas del pseudotallo
            out.append(f'<line x1="{x - 3 * k:.1f}" y1="{y - h * j / 4:.1f}" x2="{x + 3 * k:.1f}" y2="{y - h * j / 4 - 2:.1f}" stroke="#5E7438" stroke-width="0.8"/>')
        top = (x, y - h)
        for i, ang in enumerate((20, 160, 60, 120, 95, 40, 140)[: 4 + min(3, s)]):
            col = ("#5FA34A", "#6FB04A", "#4E9240", "#7DBB55")[i % 4]
            if i == 6 and s >= 4:
                col = "#9C9A45"  # hoja vieja que amarillea
            out += musa_leaf(top[0], top[1], ang, (24 + rnd.uniform(-3, 3)) * k, col, torn=s >= 3 and i % 3 == 0)
        if s >= 3:  # pedúnculo con la bellota morada al final
            bx, by = x + 6 * k, y - h * 0.62
            out.append(f'<path d="M{x + 1:.1f} {y - h + 2:.1f} Q{x + 10 * k:.1f} {y - h * 0.9:.1f} {bx:.1f} {by:.1f}" stroke="#6A8540" stroke-width="1.6" fill="none"/>')
            if s == 3:
                out += [poly([(bx - 3, by), (bx + 3, by), (bx, by + 9)], "#7A2E4A"), poly([(bx, by), (bx + 3, by), (bx, by + 9)], "#5E2238")]
            else:
                col = ripe if s == 5 else "#7FA83A"
                for row in range(4):  # manos del racimo
                    ry = by - 6 + row * 4.2
                    for c in range(-2, 3):
                        fx = bx - 1 + c * finger[0] * 0.8
                        out.append(poly([(fx, ry), (fx + finger[0] * 0.5, ry - finger[1] * 0.75), (fx + finger[0], ry - finger[1] * 0.6), (fx + finger[0] * 0.6, ry)], shade(col, (c % 2) * -0.08)))
                out += [poly([(bx - 2, by + 11), (bx + 2, by + 11), (bx, by + 16)], "#7A2E4A")]  # bellota restante
        return out

    return draw


def emparrado(cx, cy, rows, s):
    """Emparrado (granadilla): postes en las esquinas y una malla de alambre arriba."""
    H = 52
    pts = [at(cx, cy, u, v) for u, v in ((0.02, 0.02), (0.98, 0.02), (0.98, 0.98), (0.02, 0.98))]
    out = []
    for i, (px, py) in enumerate(pts):
        if i != 2:  # el poste del frente se dibuja al final para que quede delante
            out.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px:.1f}" y2="{py - H:.1f}" stroke="{D["tierra"]}" stroke-width="2.6"/>')
    for t in (0.02, 0.35, 0.65, 0.98):
        a0, a1 = at(cx, cy, t, 0.02), at(cx, cy, t, 0.98)
        b0, b1 = at(cx, cy, 0.02, t), at(cx, cy, 0.98, t)
        out.append(f'<line x1="{a0[0]:.1f}" y1="{a0[1] - H:.1f}" x2="{a1[0]:.1f}" y2="{a1[1] - H:.1f}" stroke="#D8CDB8" stroke-width="0.9"/>')
        out.append(f'<line x1="{b0[0]:.1f}" y1="{b0[1] - H:.1f}" x2="{b1[0]:.1f}" y2="{b1[1] - H:.1f}" stroke="#D8CDB8" stroke-width="0.9"/>')
    return out


def emparrado_front(cx, cy):
    px, py = at(cx, cy, 0.98, 0.98)
    return [f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px:.1f}" y2="{py - 52:.1f}" stroke="{D["tierra"]}" stroke-width="2.6"/>']


def passiflora(kind):
    """Granadilla en emparrado (techo de hojas, frutos colgando) y maracuyá en espaldera (cortina en el hilo de arriba)."""
    roof = kind == "granadilla"
    fruit_ripe = {"granadilla": "#F0A43A", "maracuya": "#E8C93A"}[kind]
    corona = {"granadilla": "#7A4AA8", "maracuya": "#5B3A8C"}[kind]

    def draw(x, y, s, sd):
        rnd = random.Random(sd)
        H = 52 if roof else 44
        if s == 0:
            return [f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y - 10:.1f}" stroke="#6E9C4A" stroke-width="1.4"/>'] + blob(x, y - 10, 3, "#6FB04A", sd)
        reach = (0, 0.35, 0.75, 1.0, 1.0, 1.0)[s]
        top = y - H * min(1.0, reach * 1.2)
        out = [f'<path d="M{x:.1f} {y:.1f} Q{x + 4:.1f} {(y + top) / 2:.1f} {x:.1f} {top:.1f}" stroke="#5E7438" stroke-width="1.5" fill="none"/>']
        if s >= 2:
            spread = 24 * reach if roof else 16 * reach
            for i in range(14 if roof else 11):  # follaje tupido
                dx = rnd.uniform(-spread, spread)
                dy = rnd.uniform(-5, 5) if roof else rnd.uniform(-2, 20)  # techo plano o cortina colgante
                out += blob(x + dx, top + dy, 7.2 if roof else 6.4, ("#4E8F3A", "#5FA34A", "#6FB04A", "#3F7F33")[i % 4], sd + i, ry=5.2 if roof else 5.8)
        else:
            out += blob(x, top, 4, "#6FB04A", sd)
        if s == 3:  # flor de pasiflora: pétalos blancos y corona morada
            for _ in range(4):
                fx, fy = x + rnd.uniform(-16, 16), top + (rnd.uniform(4, 9) if roof else rnd.uniform(4, 16))
                out += [f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="3" fill="#FFFFFF" stroke="#D8CDE8" stroke-width="0.6"/>',
                        f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="1.9" fill="none" stroke="{corona}" stroke-width="1.1"/>']
        if s >= 4:
            col = fruit_ripe if s == 5 else "#7FA83A"
            for _ in range(5):
                fx, fy = x + rnd.uniform(-18, 18), top + (rnd.uniform(8, 13) if roof else rnd.uniform(8, 22))
                out.append(f'<line x1="{fx:.1f}" y1="{fy - 4:.1f}" x2="{fx:.1f}" y2="{fy - 2.5:.1f}" stroke="#5E7438" stroke-width="0.8"/>')
                out += gem(fx, fy, 3.1, col, 3.5 if kind == "maracuya" else 3.1)
                if kind == "granadilla" and s == 5:
                    out.append(f'<circle cx="{fx + 0.8:.1f}" cy="{fy - 0.6:.1f}" r="0.6" fill="#FFFFFF" opacity="0.8"/>')
        return out

    return draw


def espaldera(height, posts_color=None):
    def draw(cx, cy, rows, s):
        out = []
        for r in range(rows):
            v = (r + 0.5) / rows
            a0, a1 = at(cx, cy, 0.03, v), at(cx, cy, 0.97, v)
            for p in (a0, a1):
                out.append(f'<line x1="{p[0]:.1f}" y1="{p[1]:.1f}" x2="{p[0]:.1f}" y2="{p[1] - height:.1f}" stroke="{posts_color or D["tierra"]}" stroke-width="2.4"/>')
            for hgt in (height * 0.5, height * 0.95):
                out.append(f'<line x1="{a0[0]:.1f}" y1="{a0[1] - hgt:.1f}" x2="{a1[0]:.1f}" y2="{a1[1] - hgt:.1f}" stroke="#D8CDB8" stroke-width="1"/>')
        return out
    return draw


def vid(x, y, s, sd):
    """Uva en espaldera: tronco leñoso, hojas palmeadas a lo largo del hilo y racimos que pasan de verde a morado."""
    rnd = random.Random(sd)
    if s == 0:
        return [f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y - 12:.1f}" stroke="#6B4A2E" stroke-width="2"/>']
    k = (0, 0.4, 0.75, 1.0, 1.0, 1.0)[s]
    out = [f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y - 20:.1f}" stroke="#6B4A2E" stroke-width="2.6"/>']
    for i in range(int(6 * k) + 1):  # brazos sobre el hilo y hojas palmeadas
        dx, dy = rnd.uniform(-10, 10), -20 - rnd.uniform(0, 18) * k
        col = ("#5FA34A", "#4E8F3A", "#6FB04A")[i % 3]
        out += blob(x + dx, y + dy, 5.2, col, sd + i, ry=4.6)
        out += [poly([(x + dx - 2, y + dy - 4), (x + dx, y + dy - 7), (x + dx + 2, y + dy - 4)], shade(col, 0.15))]  # punta de la hoja
    if s == 3:
        for _ in range(3):
            fx, fy = x + rnd.uniform(-8, 8), y - 18 - rnd.uniform(0, 10)
            out.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="1.4" fill="#D9E6A0"/>')
    if s >= 4:
        col = "#9CC152" if s == 4 else "#5B2A5E"
        for _ in range(3):  # racimos: triángulo de bayas
            gx, gy = x + rnd.uniform(-9, 9), y - 14 - rnd.uniform(0, 6)
            for row, n in enumerate((4, 3, 2, 1)):
                for c in range(n):
                    out.append(f'<circle cx="{gx - n * 1.3 + c * 2.6 + 1.3:.1f}" cy="{gy + row * 2.4:.1f}" r="1.45" fill="{shade(col, (c % 2) * 0.12)}"/>')
    return out


# ---------- Lote 4: raíces y hortalizas de hoja ----------

def palmate(x, y, r, color, lobes=7, spread=150, start=15):
    """Hoja palmeada (yuca): lóbulos finos que salen de un punto."""
    out = []
    for i in range(lobes):
        ang = start + spread * i / (lobes - 1)
        out += leaf(x, y, ang, r, r * 0.28, shade(color, (0.0, 0.06, -0.05)[i % 3]), shade_side=False)
    return out


def yuca(x, y, s, sd):
    """Tallos leñosos con nudos, pecíolo rojizo y hoja palmeada arriba; raíces que engrosan bajo tierra."""
    rnd = random.Random(sd)
    if s == 1:
        return [poly([(x - 1.5, y), (x + 1.5, y), (x + 1.2, y - 8), (x - 1.2, y - 8)], "#8A6A4A")] + palmate(x, y - 8, 6, "#5FA34A", 5)
    if s == 5:  # cosecha: raíces arrancadas sobre la tierra
        out = []
        for d in (-1, 1):
            out += [poly([(x, y), (x + 14 * d, y + 2), (x + 15 * d, y + 5), (x + 1, y + 3)], "#8A5A34"), poly([(x, y), (x + 14 * d, y + 2), (x + 8 * d, y + 1)], "#A87148")]
        out.append(poly([(x - 1.2, y), (x + 1.2, y), (x + 1, y - 10), (x - 1, y - 10)], "#8A6A4A"))
        return out
    k = (0, 0, 0.6, 0.85, 1.0)[s]
    h = 34 * k
    out = []
    for dx in (-3, 3):
        out.append(poly([(x + dx - 1.4, y), (x + dx + 1.4, y), (x + dx * 1.8 + 1, y - h), (x + dx * 1.8 - 1, y - h)], "#8A6A4A"))
        for j in range(1, 4):
            out.append(f'<circle cx="{x + dx * (1 + 0.8 * j / 4):.1f}" cy="{y - h * j / 4:.1f}" r="1" fill="#6B4E34"/>')
    for i in range(5):
        tx = x + rnd.uniform(-9, 9)
        ty = y - h + rnd.uniform(-6, 4)
        out.append(f'<line x1="{x:.1f}" y1="{y - h * 0.8:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" stroke="#B5463A" stroke-width="0.9"/>')
        out += palmate(tx, ty, 9 * k + 2, ("#4E8F3A", "#5FA34A", "#3F7F33")[i % 3], 7)
    return out


def yuca_cut(cx, cy):
    out = []
    for dx, dy in ((-46, 30), (-26, 42), (24, 40)):
        x, y = cx + dx, cy + dy
        out += [poly([(x, y - 6), (x + 3, y - 4), (x + 1, y + 10), (x - 2, y + 10)], "#8A5A34"),
                poly([(x + 4, y - 5), (x + 7, y - 3), (x + 9, y + 9), (x + 6, y + 9)], "#A87148")]
    return out


def arracacha(x, y, s, sd):
    """Mata tupida tipo apio: pecíolos largos con base morada y hojas recortadas; raíz amarilla."""
    rnd = random.Random(sd)
    if s == 1:
        return blob(x, y - 4, 4, "#6FB04A", sd)
    if s == 5:
        return [poly([(x - 2, y), (x + 10, y - 2), (x + 11, y + 3), (x - 1, y + 3)], "#E8C34B"), poly([(x - 2, y), (x - 10, y + 1), (x - 9, y + 4)], "#D9B23A")] + blob(x, y - 4, 4, "#8DBA4F", sd)
    k = (0, 0, 0.6, 0.85, 1.0)[s]
    out = []
    for i, ang in enumerate((40, 65, 90, 115, 140, 78, 102)):
        a = math.radians(ang)
        tx, ty = x + 16 * k * math.cos(a), y - 18 * k * math.sin(a)
        out.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" stroke="{"#8A4A7A" if i % 2 else "#6E9C4A"}" stroke-width="1.4"/>')
        out += blob(tx, ty, 5 * k + 1, ("#5FA34A", "#6FB04A", "#4E8F3A")[i % 3], sd + i, ry=(5 * k + 1) * 0.7)
    if s >= 3:
        out += [poly([(x - 3, y + 1), (x + 3, y + 1), (x + 2, y - 2), (x - 2, y - 2)], "#E8C34B")]
    return out


def tomate(x, y, s, sd):
    """Planta tutorada: estaca con su cuerda, hoja compuesta, flor amarilla y racimos de verde a rojo."""
    rnd = random.Random(sd)
    if s == 0:
        return [poly([(x, y - 3), (x + 2.5, y), (x, y + 2), (x - 2.5, y)], "#E8D9B0")]
    h = (0, 10, 30, 46, 50, 50)[s]
    out = [f'<line x1="{x + 4:.1f}" y1="{y:.1f}" x2="{x + 4:.1f}" y2="{y - 54:.1f}" stroke="#B8935A" stroke-width="1.6"/>'] if s >= 2 else []
    out.append(f'<path d="M{x:.1f} {y:.1f} Q{x + 3:.1f} {y - h / 2:.1f} {x + 1:.1f} {y - h:.1f}" stroke="#4E7A2E" stroke-width="1.8" fill="none"/>')
    for i in range(max(1, int(h / 7))):
        yy = y - 5 - i * 7
        out += blob(x + (5 if i % 2 else -4), yy, 5.2, ("#4E8F3A", "#5FA34A", "#3F7F33")[i % 3], sd + i, ry=4)
    if s == 3:
        for _ in range(4):
            out += flower(x + rnd.uniform(-6, 6), y - rnd.uniform(10, h), 1.8, "#F2D23A", "#E09A2A")
    if s >= 4:
        for j in range(3):
            cy0 = y - 10 - j * 12
            for c in range(3):
                col = "#8CC152" if s == 4 else ("#E0402F" if (c + j) % 3 else "#F07A3A")
                out += gem(x - 3 + c * 3.2 + rnd.uniform(-1, 1), cy0 + (c % 2) * 2.4, 2.4, col)
    return out


def lechuga(x, y, s, sd):
    """Roseta de hojas rizadas verde claro que se cierra en cabeza."""
    if s == 1:
        return blob(x, y - 2, 3.5, "#9CCB5A", sd)
    k = (0, 0, 0.6, 0.85, 1.0, 1.0)[s]
    out = []
    for i, ang in enumerate((0, 45, 90, 135, 180, 225, 270, 315)):
        a = math.radians(ang)
        out += blob(x + 7 * k * math.cos(a), y - 4 * k + 3.5 * k * math.sin(a), 6 * k, ("#8DC456", "#A6D46A", "#7AB34A")[i % 3], sd + i, ry=4.2 * k)
    out += blob(x, y - 6 * k, 6.5 * k, "#C2E07A", sd + 9, ry=5 * k)
    if s == 5:
        out.append(f'<line x1="{x - 10:.1f}" y1="{y + 4:.1f}" x2="{x + 10:.1f}" y2="{y + 4:.1f}" stroke="{P["noche"]}" stroke-width="1" stroke-dasharray="3 2"/>')
    return out


def repollo(x, y, s, sd):
    """Hojas externas grandes verde azulado y una cabeza redonda y apretada en el centro."""
    if s == 1:
        return blob(x, y - 2, 3.5, "#7FAE8C", sd)
    k = (0, 0, 0.6, 0.85, 1.0, 1.0)[s]
    out = []
    for i, ang in enumerate((10, 60, 120, 170, 220, 320)):
        a = math.radians(ang)
        out += blob(x + 9 * k * math.cos(a), y - 3 * k + 4.5 * k * math.sin(a), 7.5 * k, ("#6E9C86", "#7FAE8C", "#5E8C78")[i % 3], sd + i, ry=4.8 * k)
    if s >= 3:
        hr = (0, 0, 0, 5, 7, 7.5)[s]
        out += gem(x, y - 6 * k, hr, "#B9D9A0", hr * 0.85) + [f'<path d="M{x - hr * 0.6:.1f} {y - 6 * k:.1f} Q{x:.1f} {y - 6 * k - hr * 0.7:.1f} {x + hr * 0.6:.1f} {y - 6 * k:.1f}" stroke="#8DB57A" stroke-width="0.9" fill="none"/>']
    return out


# ---------- Lote 5: más hortalizas ----------

def frijol(x, y, s, sd):
    """Fríjol de mata: hojas de tres foliolos, flor lila y vainas que maduran jaspeadas de rojo (tipo cargamanto)."""
    rnd = random.Random(sd)
    if s == 1:
        return leaf(x, y - 3, 45, 6, 5, "#7DB04A") + leaf(x, y - 3, 135, 6, 5, "#6FA03C")
    k = (0, 0, 0.65, 0.9, 1.0, 1.0)[s]
    col = "#5FA34A" if s < 5 else "#B9A55A"
    out = []
    for i in range(6):  # trifolios en la mata
        bx, by = x + rnd.uniform(-8, 8) * k, y - rnd.uniform(4, 18) * k
        for d in (-35, 0, 35):
            out += leaf(bx, by, 90 + d, 6.5 * k, 5 * k, shade(col, (0.0, 0.07, -0.06)[i % 3]))
    if s == 3:
        for _ in range(4):
            out += flower(x + rnd.uniform(-7, 7), y - rnd.uniform(8, 18), 1.8, "#B9A0E0", "#8A6AC0")
    if s >= 4:
        for _ in range(4):
            px, py = x + rnd.uniform(-8, 8), y - rnd.uniform(4, 12)
            pod = "#8CC152" if s == 4 else "#E8D9B0"
            out.append(f'<ellipse cx="{px:.1f}" cy="{py:.1f}" rx="1.6" ry="5" fill="{pod}" transform="rotate(20 {px:.1f} {py:.1f})"/>')
            if s == 5:
                out.append(f'<line x1="{px - 1:.1f}" y1="{py - 3:.1f}" x2="{px + 1:.1f}" y2="{py + 2:.1f}" stroke="#C0392B" stroke-width="0.9"/>')
    return out


def brocoli(x, y, s, sd):
    """Hojas grandes verde azulado y, en el centro, la cabeza de floretes verde oscuro."""
    if s == 1:
        return blob(x, y - 2, 3.5, "#6E9C86", sd)
    k = (0, 0, 0.6, 0.85, 1.0, 1.0)[s]
    out = []
    for i, ang in enumerate((20, 70, 110, 160, 220, 320)):
        a = math.radians(ang)
        out += leaf(x, y - 3 * k, ang, 13 * k, 7 * k, ("#5E8C78", "#6E9C86", "#7FAE8C")[i % 3])
    if s >= 3:
        hr = (0, 0, 0, 4.5, 7, 7.5)[s]
        head = "#6E9A3E" if s < 5 else "#5A8A36"  # floretes: verde más vivo que las hojas, con grano claro
        for dx, dy in ((-hr * 0.5, 0), (hr * 0.5, 0), (0, -hr * 0.5), (-hr * 0.25, -hr * 0.2), (hr * 0.3, -hr * 0.3)):
            out += blob(x + dx, y - 10 * k + dy, hr * 0.6, head, sd + int(dx * 10), light=0.25)
        for i in range(6):
            a = 2 * math.pi * i / 6
            out.append(f'<circle cx="{x + math.cos(a) * hr * 0.5:.1f}" cy="{y - 10 * k - hr * 0.2 + math.sin(a) * hr * 0.3:.1f}" r="0.9" fill="#A8C870"/>')
    return out


def espinaca(x, y, s, sd):
    """Roseta densa de hojas oscuras en forma de pala."""
    if s == 1:
        return leaf(x, y - 1, 60, 5, 4, "#3F7F33") + leaf(x, y - 1, 120, 5, 4, "#4E8F3A")
    k = (0, 0, 0.6, 0.85, 1.0, 1.0)[s]
    out = []
    for i, ang in enumerate((15, 50, 85, 120, 155, 35, 140)):
        out += leaf(x, y, ang, 10 * k, 7.5 * k, ("#2F6B2E", "#3F7F33", "#4E8F3A")[i % 3])
    if s == 5:
        out.append(f'<line x1="{x - 8:.1f}" y1="{y + 3:.1f}" x2="{x + 8:.1f}" y2="{y + 3:.1f}" stroke="{P["noche"]}" stroke-width="1" stroke-dasharray="3 2"/>')
    return out


def pepino(x, y, s, sd):
    """Enredadera en espaldera: hojas anchas, flor amarilla y pepinos largos que cuelgan."""
    rnd = random.Random(sd)
    if s == 0:
        return [poly([(x, y - 3), (x + 2.5, y), (x, y + 2), (x - 2.5, y)], "#E8D9B0")]
    reach = (0, 0.3, 0.7, 1.0, 1.0, 1.0)[s]
    H = 40
    top = y - H * reach
    out = [f'<path d="M{x:.1f} {y:.1f} Q{x + 4:.1f} {(y + top) / 2:.1f} {x:.1f} {top:.1f}" stroke="#5E7438" stroke-width="1.5" fill="none"/>']
    for i in range(int(8 * reach) + 1):
        bx, by = x + rnd.uniform(-9, 9), top + rnd.uniform(0, H * reach * 0.9)
        out += blob(bx, by, 5.5, ("#4E8F3A", "#5FA34A", "#6FB04A")[i % 3], sd + i, ry=4.6)
    if s == 3:
        for _ in range(4):
            out += flower(x + rnd.uniform(-8, 8), top + rnd.uniform(4, 30), 1.9, "#F2D23A", "#E0A82A")
    if s >= 4:
        for _ in range(3):
            cx0, cy0 = x + rnd.uniform(-8, 8), top + rnd.uniform(10, 30)
            col = "#B9D77A" if s == 4 else "#4E7F2E"
            cx0 = x + (10 if cx0 > x else -10)  # el fruto cuelga por fuera del follaje, para que se vea
            out += [poly([(cx0 - 2.2, cy0), (cx0 + 2.2, cy0), (cx0 + 1.9, cy0 + 13), (cx0 - 1.9, cy0 + 13)], col, shade(col, -0.35), 0.8),
                    f'<line x1="{cx0 - 0.6:.1f}" y1="{cy0 + 1:.1f}" x2="{cx0 - 0.6:.1f}" y2="{cy0 + 12:.1f}" stroke="#D8E9A8" stroke-width="0.8"/>']
    return out


def papa_criolla(x, y, s, sd):
    """Como la papa, con matas más pequeñas; al cosechar, tubérculos redondos y amarillos."""
    if s == 5:
        return []
    out = papa(x, y, s, sd)
    return [f'<g transform="translate({x:g} {y:g}) scale(0.82) translate({-x:g} {-y:g})">{"".join(out)}</g>']


def criolla_harvest(cx, cy):
    out = []
    rnd = random.Random(7)
    for r in range(5):
        for c in range(7):
            x, y = at(cx, cy, (c + 0.5) / 7 + rnd.uniform(-0.02, 0.02), (r + 0.5) / 5)
            out += gem(x - 2, y - 1, 3, "#F2C94C") + gem(x + 3, y + 1, 2.6, "#E8B83A")
    return out


def criolla_cut(cx, cy):
    return gem(cx - 40, cy + 34, 4.5, "#F2C94C") + gem(cx - 58, cy + 26, 4, "#E8B83A") + gem(cx - 24, cy + 44, 4, "#F2C94C") + gem(cx + 30, cy + 40, 4.5, "#E8B83A")


# ---------- Lote 6: frutas andinas ----------

def beds(cx, cy, rows):
    """Camas elevadas cubiertas con plástico (fresa): franjas grises sobre cada surco."""
    out = []
    for r in range(rows):
        v = (r + 0.5) / rows
        p0, p1 = at(cx, cy, 0.03, v), at(cx, cy, 0.97, v)
        out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1] + 2:.1f}" x2="{p1[0]:.1f}" y2="{p1[1] + 2:.1f}" stroke="#4A3428" stroke-width="12" stroke-linecap="round"/>')
        out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" stroke="#5C6670" stroke-width="10" stroke-linecap="round"/>')
        out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1] - 2:.1f}" x2="{p1[0]:.1f}" y2="{p1[1] - 2:.1f}" stroke="#7D8892" stroke-width="2.5" stroke-linecap="round"/>')
    return out


def fresa(x, y, s, sd):
    """Roseta baja de hojas de tres foliolos aserrados; flor blanca; fresas que cuelgan sobre el plástico."""
    rnd = random.Random(sd)
    if s == 0:
        return leaf(x, y - 1, 60, 5, 4, "#5FA34A") + leaf(x, y - 1, 120, 5, 4, "#4E8F3A")
    k = (0, 0.55, 0.8, 1.0, 1.0, 1.0)[s]
    out = []
    for i, ang in enumerate((25, 70, 110, 155, 50, 130)):
        a = math.radians(ang)
        bx, by = x + 7 * k * math.cos(a), y - 4 * k - 5 * k * math.sin(a)
        for d in (-28, 0, 28):
            out += leaf(bx, by, ang + d, 5.5 * k, 4.5 * k, ("#4E8F3A", "#5FA34A", "#3F7F33")[i % 3])
    if s == 3:
        for _ in range(3):
            out += flower(x + rnd.uniform(-7, 7), y - rnd.uniform(2, 8), 2, "#FFFFFF", "#F2D23A")
    if s >= 4:
        for _ in range(4):
            fx, fy = x + rnd.uniform(-9, 9), y + rnd.uniform(0, 3)
            col = "#C9E08A" if s == 4 else "#D8322E"
            out += [poly([(fx - 2.4, fy - 2), (fx + 2.4, fy - 2), (fx, fy + 4)], col), poly([(fx, fy - 2), (fx + 2.4, fy - 2), (fx, fy + 4)], shade(col, -0.15)),
                    poly([(fx - 1.8, fy - 2), (fx + 1.8, fy - 2), (fx, fy - 4)], "#3F7F33")]
            if s == 5:
                out.append(f'<circle cx="{fx - 0.6:.1f}" cy="{fy:.1f}" r="0.4" fill="#F7E58A"/>')
    return out


def mora(x, y, s, sd):
    """Cañas arqueadas en espaldera; flor blanca; bayas que pasan de rojo a negro."""
    rnd = random.Random(sd)
    if s == 0:
        return blob(x, y - 3, 3.5, "#5FA34A", sd)
    k = (0, 0.4, 0.75, 1.0, 1.0, 1.0)[s]
    out = []
    for i in range(4):  # cañas arqueadas
        d = -1 if i % 2 else 1
        ex, ey = x + d * (10 + i * 3) * k, y - (14 + i * 6) * k
        out.append(f'<path d="M{x:.1f} {y:.1f} Q{x + d * 2:.1f} {ey - 6 * k:.1f} {ex:.1f} {ey:.1f}" stroke="#7A4A5A" stroke-width="1.3" fill="none"/>')
        for t in (0.45, 0.75, 1.0):
            px, py = x + (ex - x) * t, y + (ey - y) * t - 4 * k * (1 - abs(0.6 - t))
            out += blob(px, py, 4.5 * k + 1, ("#3F7F33", "#4E8F3A", "#5FA34A")[(i + int(t * 4)) % 3], sd + i * 7 + int(t * 10), ry=3.8 * k + 1)
    if s == 3:
        for _ in range(4):
            out += flower(x + rnd.uniform(-12, 12), y - rnd.uniform(10, 26), 1.8, "#FFFFFF", "#E8E0C8")
    if s >= 4:
        for _ in range(5):
            bx, by = x + rnd.uniform(-12, 12), y - rnd.uniform(8, 24)
            col = "#D8322E" if s == 4 else "#2A1A2E"
            for dx, dy in ((0, 0), (1.6, 0.4), (0.8, 1.6), (-0.8, 1.2)):
                out.append(f'<circle cx="{bx + dx:.1f}" cy="{by + dy:.1f}" r="1.25" fill="{shade(col, 0.1 if dx > 0 else 0)}"/>')
    return out


def uchuva(x, y, s, sd):
    """Arbusto de hoja aterciopelada; frutos dentro de un capuchón de papel que pasa de verde a pajizo."""
    rnd = random.Random(sd)
    if s == 0:
        return blob(x, y - 3, 3.5, "#7FA65A", sd)
    k = (0, 0.45, 0.75, 1.0, 1.0, 1.0)[s]
    out = []
    for i in range(6):
        out += blob(x + rnd.uniform(-9, 9) * k, y - rnd.uniform(5, 20) * k, 6.5 * k + 1, ("#6E9A4A", "#7FA65A", "#5E8C40")[i % 3], sd + i)
    if s == 3:
        for _ in range(4):
            out += flower(x + rnd.uniform(-8, 8), y - rnd.uniform(6, 18), 1.8, "#F2E27A", "#6B4A2E")
    if s >= 4:
        for _ in range(5):
            lx, ly = x + rnd.uniform(-10, 10), y - rnd.uniform(4, 18)
            husk = "#A8C870" if s == 4 else "#D9C27A"
            out += [poly([(lx, ly - 4), (lx + 3, ly - 1), (lx + 2, ly + 3), (lx - 2, ly + 3), (lx - 3, ly - 1)], husk, shade(husk, -0.3), 0.6)]
            if s == 5:
                out.append(f'<circle cx="{lx:.1f}" cy="{ly + 0.6:.1f}" r="1.3" fill="#F28C28"/>')
    return out


def arandano(x, y, s, sd):
    """Arbusto de muchas hojas pequeñas y ramas rojizas; flor en campanita; bayas azules con polvo claro."""
    rnd = random.Random(sd)
    if s == 0:
        return blob(x, y - 3, 3.2, "#3F7F33", sd)
    k = (0, 0.45, 0.75, 1.0, 1.0, 1.0)[s]
    out = []
    for i in range(4):
        d = (i - 1.5) * 4
        out.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + d * k:.1f}" y2="{y - 20 * k:.1f}" stroke="#8A3A3A" stroke-width="1.1"/>')
    for i in range(10):
        out += blob(x + rnd.uniform(-10, 10) * k, y - rnd.uniform(6, 22) * k, 4 * k + 0.8, ("#2F6B2E", "#3F7F33", "#4E8F3A")[i % 3], sd + i, ry=3.4 * k + 0.6)
    if s == 3:
        for _ in range(5):
            bx, by = x + rnd.uniform(-9, 9), y - rnd.uniform(8, 20)
            out.append(poly([(bx - 1.4, by), (bx + 1.4, by), (bx + 1, by + 2.6), (bx - 1, by + 2.6)], "#FFF4F0"))
    if s >= 4:
        for _ in range(6):
            bx, by = x + rnd.uniform(-10, 10), y - rnd.uniform(6, 20)
            col = "#A8C870" if s == 4 else "#3B4F8F"
            for dx in (-1.4, 1.4):
                out += [f'<circle cx="{bx + dx:.1f}" cy="{by:.1f}" r="1.5" fill="{col}"/>']
            if s == 5:
                out.append(f'<circle cx="{bx - 1.6:.1f}" cy="{by - 0.6:.1f}" r="0.5" fill="#B8C6E8"/>')
    return out


# ---------- Catálogo ----------

STAGES = {
    "anual": ("Siembra", "Emergencia", "Desarrollo", "Floración", "Llenado", "Cosecha"),
    "raiz": ("Siembra", "Emergencia", "Hojas", "Crecimiento", "Engrose", "Cosecha"),
    "perenne": ("Plántula", "Joven", "Crecimiento", "Floración", "Fruto verde", "Cosecha"),
    "musa": ("Hijuelo", "Joven", "Crecimiento", "Bellota", "Racimo verde", "Cosecha"),
    "estaca": ("Estaca", "Brotación", "Hojas", "Crecimiento", "Engrose", "Cosecha"),
    "hoja": ("Siembra", "Emergencia", "Hojas", "Roseta", "Cabeza", "Cosecha"),
}

# (clave, nombre, arquetipo, etapas, planta, filas, columnas, ¿caballones?, extras por etapa, ¿piloto?, nota)
CROPS = (
    ("papa", "Papa", "tuber", "anual", papa, 4, 6, True, {4: ("cut", papa_cut), 5: ("ground", papa_harvest)}, True,
     "Matas frondosas sobre caballones aporcados; flor lila o blanca; los tubérculos se forman bajo el suelo"),
    ("maiz", "Maíz", "cereal", "anual", maiz, 4, 5, False, {}, True, "Caña alta de hojas largas; espiga arriba y mazorca con pelo en el tallo"),
    ("arveja", "Arveja", "climbing_legume", "anual", arveja, 3, 7, False, {"all": ("trellis", arveja_trellis)}, True,
     "Enredadera en espaldera de postes e hilos; flor blanca y vainas verdes"),
    ("zanahoria", "Zanahoria", "root", "raiz", zanahoria, 5, 8, False, {}, True, "Follaje plumoso y denso; la raíz naranja engrosa bajo tierra"),
    ("cebolla", "Cebolla de bulbo", "bulb", "raiz", cebolla, 5, 8, False, {}, True, "Hojas huecas verde azulado; el bulbo morado engrosa en la base"),
    ("mango", "Mango", "tree_fruit", "perenne", tree("mango"), 2, 2, False, {"orchard": True}, False,
     "Copa ancha en cúpula, verde oscuro; flor en panículas rosadas; frutos que cuelgan y maduran amarillos con rubor rojo"),
    ("naranja", "Naranja", "tree_fruit", "perenne", tree("naranja"), 2, 2, False, {"orchard": True}, False,
     "Copa redonda y densa; azahar blanco; frutos redondos que pasan de verde a naranja"),
    ("limon", "Limón Tahití", "tree_fruit", "perenne", tree("limon"), 2, 2, False, {"orchard": True}, False,
     "Copa más abierta y clara; flor blanca; frutos pequeños y ovalados, verdes al cosecharse"),
    ("mandarina", "Mandarina", "tree_fruit", "perenne", tree("mandarina"), 2, 2, False, {"orchard": True}, False,
     "Copa compacta; muchos frutos achatados de naranja intenso"),
    ("aguacate", "Aguacate Hass", "tree_fruit", "perenne", tree("aguacate"), 2, 2, False, {"orchard": True}, False,
     "Árbol alto de copa irregular y hoja grande; flor verde amarillenta; fruto en forma de pera que madura casi negro"),
    ("platano", "Plátano", "musa", "musa", scaled(musa("platano"), 1.9), 2, 2, False, {"orchard": True}, False,
     "Pseudotallo y hojas largas que se rasgan; la bellota da un racimo de dedos grandes que se cosecha verde"),
    ("banano", "Banano", "musa", "musa", scaled(musa("banano"), 1.9), 2, 2, False, {"orchard": True}, False,
     "Como el plátano, con dedos más pequeños y curvos que maduran amarillos"),
    ("granadilla", "Granadilla", "passiflora", "perenne", scaled(passiflora("granadilla"), 1.0), 3, 3, False,
     {"all": ("emparrado", lambda cx, cy, rows, s: emparrado(cx, cy, rows, s)), "front": emparrado_front}, False,
     "Enredadera en emparrado: techo de hojas, flor de pasiflora y frutos naranja que cuelgan por debajo"),
    ("maracuya", "Maracuyá", "passiflora", "perenne", scaled(passiflora("maracuya"), 1.0), 3, 4, False, {"all": ("espaldera", espaldera(44))}, False,
     "Enredadera en espaldera: cortina de hojas desde el hilo de arriba; frutos que pasan de verde a amarillo"),
    ("uva", "Uva", "vine", "perenne", scaled(vid, 1.25), 3, 6, False, {"all": ("espaldera", espaldera(36, "#8A6A44"))}, False,
     "Vid en espaldera: tronco leñoso, hoja palmeada y racimos que pasan de verde a morado"),
    ("yuca", "Yuca", "root", "estaca", scaled(yuca, 1.5), 3, 4, False, {4: ("cut", yuca_cut)}, False,
     "Tallos leñosos con nudos y hoja palmeada de lóbulos finos; las raíces engrosan bajo tierra"),
    ("arracacha", "Arracacha", "root", "raiz", scaled(arracacha, 1.3), 4, 5, False, {}, False,
     "Mata tupida tipo apio, con pecíolos de base morada; raíz amarilla"),
    ("tomate", "Tomate", "staked", "anual", scaled(tomate, 1.15), 3, 5, False, {}, False,
     "Plantas tutoradas con estaca; flor amarilla y racimos que pasan de verde a rojo"),
    ("lechuga", "Lechuga", "leafy", "hoja", scaled(lechuga, 1.35), 5, 6, False, {}, False, "Rosetas de hoja rizada verde claro que se cierran en cabeza"),
    ("repollo", "Repollo", "leafy", "hoja", scaled(repollo, 1.3), 4, 5, False, {}, False, "Hojas externas grandes verde azulado y cabeza redonda y apretada"),
    ("frijol", "Fríjol", "bush_legume", "anual", scaled(frijol, 1.3), 4, 6, False, {}, False,
     "Fríjol de mata: hojas de tres foliolos, flor lila y vainas que maduran jaspeadas de rojo"),
    ("brocoli", "Brócoli", "brassica", "hoja", scaled(brocoli, 1.3), 4, 5, False, {}, False, "Hojas grandes verde azulado y la cabeza de floretes en el centro"),
    ("espinaca", "Espinaca", "leafy", "hoja", scaled(espinaca, 1.25), 5, 7, False, {}, False, "Rosetas densas de hojas oscuras en forma de pala"),
    ("pepino", "Pepino", "climbing_vine", "anual", scaled(pepino, 1.05), 3, 5, False, {"all": ("espaldera", espaldera(42))}, False,
     "Enredadera en espaldera: hoja ancha, flor amarilla y frutos largos que cuelgan"),
    ("papa_criolla", "Papa criolla", "tuber", "anual", papa_criolla, 5, 7, True, {4: ("cut", criolla_cut), 5: ("ground", criolla_harvest)}, False,
     "Matas más pequeñas que la papa; tubérculos redondos y amarillos"),
    ("fresa", "Fresa", "creeping", "perenne", scaled(fresa, 1.35), 4, 6, False, {"beds": True, "transplant": True}, False,
     "En camas cubiertas con plástico: roseta baja, flor blanca y fresas que cuelgan sobre el plástico"),
    ("tomate_arbol", "Tomate de árbol", "tree_fruit", "perenne", tree("tomate_arbol"), 2, 2, False, {"orchard": True}, False,
     "Arbolito de hoja grande y copa en sombrilla; frutos en forma de huevo que cuelgan y maduran rojo anaranjado"),
    ("mora", "Mora", "bramble", "perenne", scaled(mora, 1.3), 3, 5, False, {"all": ("espaldera", espaldera(34)), "transplant": True}, False,
     "Cañas arqueadas en espaldera; flor blanca; bayas que pasan de rojo a negro"),
    ("uchuva", "Uchuva", "shrub", "perenne", scaled(uchuva, 1.35), 3, 4, False, {"transplant": True}, False,
     "Arbusto de hoja aterciopelada; el fruto naranja crece dentro de un capuchón que pasa de verde a pajizo"),
    ("arandano", "Arándano", "shrub", "perenne", scaled(arandano, 1.35), 3, 4, False, {"transplant": True}, False,
     "Arbusto de hoja pequeña y ramas rojizas; flor en campanita; bayas azules con polvo claro"),
)


def stage_cell(crop, s, cx, cy):
    key, _, _, _, plant, rows, cols, ridged, extras, *_ = crop
    if extras.get("orchard"):  # huerto: pasto entre los árboles y plateo en cada uno
        out = block(cx, cy, 0, top=shade(GRASS, -0.08))
        return out + field(cx, cy, rows, cols, plant, s, seed=sum(map(ord, key)), jitter=0.0, basin=True)
    out = block(cx, cy, rows, ridged=ridged, cut=extras[4][1] if s == 4 and 4 in extras and extras[4][0] == "cut" else None)
    if extras.get("beds"):
        out += beds(cx, cy, rows)
    structure = "all" in extras and extras["all"][0] in ("emparrado", "espaldera")
    if extras.get("transplant") or structure:  # se trasplanta: la etapa 1 ya es una plántula
        if "all" in extras:
            out += extras["all"][1](cx, cy, rows, s)
        return out + field(cx, cy, rows, cols, plant, s, seed=sum(map(ord, key))) + (extras["front"](cx, cy) if "front" in extras else [])
    if s == 0:  # siembra: semillas marcadas sobre el surco
        rnd = random.Random(3)
        for r in range(rows):
            for c in range(cols):
                x, y = at(cx, cy, (c + 0.5) / cols, (r + 0.5) / rows)
                out.append(poly([(x, y - 3), (x + 2.5, y), (x, y + 2), (x - 2.5, y)], "#E8D9B0" if rnd.random() > 0.5 else "#D9C79A"))
    if "all" in extras and (s > 0 or extras["all"][0] in ("emparrado", "espaldera")):
        out += extras["all"][1](cx, cy, rows, s)
    if s == 5 and 5 in extras and extras[5][0] == "ground":
        out += extras[5][1](cx, cy)
    elif s > 0 or "all" in extras:
        out += field(cx, cy, rows, cols, plant, s, seed=sum(map(ord, key)))
    if "front" in extras:
        out += extras["front"](cx, cy)
    return out


def crop_sheet(crop):
    key, name, archetype, group, *_, pilot, note = crop
    w, h = 1440, 600
    labels = STAGES[group]
    b = [f'<rect width="{w}" height="{h}" fill="{P["niebla"]}"/>', text(48, 70, name, 40, 600, font=FONT_TITLE)]
    tag_w = len(archetype) * 9 + 120
    b += [poly(chamfer(48, 92, tag_w, 32, 8), WHITE, BORDE, 1.5), text(62, 114, f"Arquetipo: {archetype}", 15, 700)]
    if pilot:
        b += [poly(chamfer(60 + tag_w, 92, 150, 32, 8), "#E3EECF", D["oliva"], 1.5), text(76 + tag_w, 114, "Catálogo piloto", 15, 700, D["oliva"])]
    b.append(text(48, 150, note + ".", 15, fill=SEC))
    for s in range(6):
        cx, cy = 150 + s * 228, 410
        cell = [poly(chamfer(cx - 106, 176, 212, 390, 14), WHITE, BORDE, 1.5)] + stage_cell(crop, s, cx, cy)
        cell.append(text(cx, 548, f"{s + 1} · {labels[s]}", 15, 700, anchor="middle"))
        b.append(f'<g id="etapa-{s + 1}">{"".join(cell)}</g>')
    return svg(w, h, b)


if __name__ == "__main__":
    out = DIR / "svg"
    out.mkdir(exist_ok=True)
    for old in out.glob("cultivo-*.svg"):
        old.unlink()
    for c in CROPS:
        (out / f"cultivo-{c[0]}.svg").write_text(crop_sheet(c), encoding="utf-8", newline="\n")
        print("cultivo-" + c[0])
