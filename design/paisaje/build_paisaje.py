"""Fondos de los recorridos como capas vectoriales (HU-154 y HU-155, versión 2D).

Escenas de 1440 × 900, cada una en capas con nombre (cielo, lejano, medio, niebla, cercano…)
para moverlas con paralaje. Todo es SVG generado: pesa unos KB, no pierde calidad y se puede
recolorear para día, noche o lluvia. Sin aleatoriedad libre: mismo código, mismo dibujo.

    python design/paisaje/build_paisaje.py     # escribe svg/*.svg e imprime su peso
"""

import gzip
import math
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parent / "kit"))

from build_kit_svg import D, P, poly, pts, shade, svg  # noqa: E402

W, H = 1440, 900
PARCELS = (P["brote"], P["trigo"], P["oliva"], P["tierra"], shade(P["brote"], -0.15), shade(P["trigo"], 0.12))
HAZE = "#D2E2EA"
WALL, WATER = "#F6F1E6", "#8FC1DB"


class Rng:
    """Generador determinista: la misma semilla da siempre el mismo paisaje."""

    def __init__(self, seed):
        self.s = seed

    def next(self):
        self.s = (self.s * 1103515245 + 12345) % 2147483648
        return self.s / 2147483648

    def between(self, a, b):
        return a + (b - a) * self.next()

    def pick(self, items):
        return items[int(self.next() * len(items)) % len(items)]


def mix(a, b, t):
    ca, cb = (int(a[i : i + 2], 16) for i in (1, 3, 5)), (int(b[i : i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def layer(name, body):
    return f'<g id="{name}">{"".join(body)}</g>'


def soft(points, fill, opacity):
    return f'<polygon points="{pts(points)}" fill="{fill}" fill-opacity="{opacity}"/>'


def sky(gid, top, bottom):
    """Capa de cielo con su degradado. El id debe ser único en toda la lámina."""
    grad = f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>'
    return layer("cielo", [f"<defs>{grad}</defs>", f'<rect width="{W}" height="{H}" fill="url(#{gid})"/>'])


def ridge(rng, base, amp, n, color, fog=0.0, bottom=H, fog_color=HAZE):
    """Cordillera facetada. Cerros de ancho y alto desiguales, con hombros: nada de dientes de sierra."""
    color = mix(color, fog_color, fog)
    widths = [rng.between(0.55, 1.6) for _ in range(n)]
    total = sum(widths)
    xs = [-40.0]
    for w in widths:
        xs.append(xs[-1] + w / total * (W + 80))
    valleys = [base + rng.between(-amp * 0.1, amp * 0.18) for _ in xs]
    out = []
    for i in range(n):
        x0, x1 = xs[i], xs[i + 1]
        span = x1 - x0
        height = amp * rng.between(0.3, 1.0) * min(1.0, 0.55 + widths[i] * 0.4)
        px, py = x0 + span * rng.between(0.36, 0.64), base - height
        v0, v1 = (x0, valleys[i]), (x1, valleys[i + 1])
        sl = (x0 + (px - x0) * rng.between(0.4, 0.6), valleys[i] - (valleys[i] - py) * rng.between(0.5, 0.72))
        sr = (px + (x1 - px) * rng.between(0.4, 0.6), valleys[i + 1] - (valleys[i + 1] - py) * rng.between(0.38, 0.6))
        foot = (px + span * rng.between(-0.1, 0.1), bottom)
        out.append(poly([v0, sl, (px, py), foot, (x0, bottom)], shade(color, 0.06)))
        out.append(poly([(px, py), sr, v1, (x1, bottom), foot], shade(color, -0.09)))
        out.append(poly([sl, (px, py), ((sl[0] + foot[0]) / 2, (sl[1] + bottom) / 2)], shade(color, 0.12)))
        out.append(poly([(px, py), sr, ((sr[0] + foot[0]) / 2, (sr[1] + bottom) / 2)], shade(color, -0.03)))
    return out


def fog_band(rng, y, count, opacity=0.55, color="#FFFFFF"):
    out = []
    for _ in range(count):
        cx, w, h = rng.between(-100, W + 100), rng.between(260, 560), rng.between(20, 46)
        out.append(soft([(cx - w / 2, y + h * 0.5), (cx - w * 0.3, y - h * 0.3), (cx, y - h * 0.5), (cx + w * 0.34, y - h * 0.2), (cx + w / 2, y + h * 0.5)], color, opacity))
    return out


def clouds(rng, y, count, size, color="#FFFFFF", opacity=1.0):
    out = []
    for _ in range(count):
        x, w = rng.between(-60, W + 60), size * rng.between(0.7, 1.4)
        h = w * rng.between(0.2, 0.3)
        top = [(x - w / 2, y), (x - w * 0.36, y - h * 0.55), (x - w * 0.16, y - h * 0.95), (x + w * 0.08, y - h), (x + w * 0.3, y - h * 0.6), (x + w / 2, y)]
        out.append(soft(top, color, opacity))
        out.append(soft([(x - w / 2, y), (x + w / 2, y), (x + w * 0.3, y - h * 0.34), (x - w * 0.28, y - h * 0.3)], shade(color, -0.08), opacity))
    return out


def stars(rng, count, y_max):
    out = []
    for _ in range(count):
        x, y, r = rng.between(0, W), rng.between(0, y_max), rng.between(1.2, 3.4)
        out.append(poly([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], "#FFF4D6"))
    return out


def sprout(x, y, s, color=None, flower=False):
    color = color or P["brote"]
    out = [
        poly([(x - 1.5 * s, y), (x + 1.5 * s, y), (x + 1.5 * s, y - 12 * s), (x - 1.5 * s, y - 12 * s)], shade(color, -0.45)),
        poly([(x, y - 9 * s), (x - 12 * s, y - 18 * s), (x - 5 * s, y - 5 * s)], color),
        poly([(x, y - 11 * s), (x + 13 * s, y - 21 * s), (x + 6 * s, y - 6 * s)], shade(color, -0.12)),
    ]
    if flower:  # flor de leguminosa: la rotación
        out.append(poly([(x, y - 27 * s), (x + 5 * s, y - 21 * s), (x, y - 15 * s), (x - 5 * s, y - 21 * s)], "#FFFFFF"))
    return out


def tree(x, y, s, color=None):
    color = color or P["oliva"]
    return [
        poly([(x - 4 * s, y), (x + 4 * s, y), (x + 3 * s, y - 26 * s), (x - 3 * s, y - 26 * s)], D["tierra"]),
        poly([(x, y - 84 * s), (x + 28 * s, y - 20 * s), (x - 28 * s, y - 20 * s)], shade(color, 0.05)),
        poly([(x, y - 84 * s), (x + 28 * s, y - 20 * s), (x + 2 * s, y - 20 * s)], shade(color, -0.14)),
    ]


def house(x, y, s, wall=WALL, trim=None):
    """Casa de campo: muros claros, techo de teja y zócalo de color, como en el altiplano."""
    w, h = 96 * s, 56 * s
    out = [
        poly([(x, y - h), (x + w, y - h), (x + w, y), (x, y)], wall),
        poly([(x + w, y - h), (x + w + 22 * s, y - h - 12 * s), (x + w + 22 * s, y - 12 * s), (x + w, y)], shade(wall, -0.14)),
        poly([(x - 8 * s, y - h), (x + w * 0.5, y - h - 34 * s), (x + w + 8 * s, y - h)], P["tierra"]),
        poly([(x + w * 0.5, y - h - 34 * s), (x + w + 8 * s, y - h), (x + w + 30 * s, y - h - 12 * s), (x + w * 0.5 + 22 * s, y - h - 46 * s)], D["tierra"]),
        poly([(x + w * 0.4, y - 30 * s), (x + w * 0.6, y - 30 * s), (x + w * 0.6, y), (x + w * 0.4, y)], shade(D["tierra"], -0.2)),
    ]
    if trim:
        out.append(poly([(x, y - 10 * s), (x + w, y - 10 * s), (x + w, y), (x, y)], trim))
    return out


def church(x, y, s):
    return [
        poly([(x - 60 * s, y - 80 * s), (x + 60 * s, y - 80 * s), (x + 60 * s, y), (x - 60 * s, y)], WALL),
        poly([(x - 70 * s, y - 80 * s), (x, y - 124 * s), (x + 70 * s, y - 80 * s)], P["tierra"]),
        poly([(x - 18 * s, y - 190 * s), (x + 18 * s, y - 190 * s), (x + 18 * s, y - 100 * s), (x - 18 * s, y - 100 * s)], "#FFFFFF"),
        poly([(x - 24 * s, y - 190 * s), (x, y - 236 * s), (x + 24 * s, y - 190 * s)], D["tierra"]),
        poly([(x - 14 * s, y - 44 * s), (x, y - 58 * s), (x + 14 * s, y - 44 * s), (x + 14 * s, y), (x - 14 * s, y)], shade(D["tierra"], -0.2)),
    ]


def frailejon(x, y, s):
    cx, cy = x, y - 50 * s
    rosette = [(cx + (24 if k % 2 == 0 else 11) * s * math.cos(math.pi / 8 * k), cy + (24 if k % 2 == 0 else 11) * s * math.sin(math.pi / 8 * k)) for k in range(16)]
    return [
        poly([(x - 6 * s, y), (x + 6 * s, y), (x + 4 * s, y - 42 * s), (x - 4 * s, y - 42 * s)], "#5A4A3A"),
        poly(rosette, "#B9C79A"),
        poly([(cx + 9 * s * math.cos(math.pi / 4 * k), cy + 9 * s * math.sin(math.pi / 4 * k)) for k in range(8)], "#E6EBC9"),
    ]


def patchwork(rng, top, highlight=None, rows=9):
    """Mosaico de parcelas en ladera, en perspectiva. `highlight` marca una parcela (fila, columna)."""
    out, hi = [], []
    vx = W * 0.52
    ys = [top + (H - top) * (i / rows) ** 1.7 for i in range(rows + 1)]

    def edge(y, k, n):
        spread = 0.75 + 1.6 * (y - top) / (H - top)
        return vx + (k / n - 0.5) * W * spread + 26 * math.sin(y * 0.02 + k)

    for r in range(rows):
        cols = 5 + r
        y0, y1 = ys[r], ys[r + 1]
        for c in range(cols):
            quad = [(edge(y0, c, cols), y0 + 6 * math.sin(c + r)), (edge(y0, c + 1, cols), y0 + 6 * math.sin(c + 1 + r)),
                    (edge(y1, c + 1, cols), y1 + 6 * math.sin(c + 2 + r)), (edge(y1, c, cols), y1 + 6 * math.sin(c + r + 1))]
            color = shade(rng.pick(PARCELS), rng.between(-0.06, 0.06))
            out.append(poly(quad, color, shade(P["oliva"], -0.3), 2))
            out.append(poly([quad[0], quad[1], quad[3]], shade(color, 0.07)))
            if highlight == (r, c):
                hi.append(poly(quad, "none", P["calabaza"], 6))
    return out, hi


# ---------- Recorrido A · del satélite al lote ----------

def orbita():
    rng = Rng(11)
    cx, cy, R = 720, 1560, 1000
    ocean, land = "#2B6A99", "#5E9B4F"

    def at(deg, r):
        return (cx + r * math.cos(math.radians(deg)), cy + r * math.sin(math.radians(deg)))

    earth = []
    rings, segs = 4, 14  # océano en facetas grandes y de tono parejo: sin efecto de tablero
    for r in range(rings):
        for s in range(segs):
            a0, a1 = -132 + s * 84 / segs, -132 + (s + 1) * 84 / segs
            quad = [at(a0, R - r * 110), at(a1, R - r * 110), at(a1, R - (r + 1) * 110), at(a0, R - (r + 1) * 110)]
            earth.append(poly(quad, shade(ocean, rng.between(-0.045, 0.045) - r * 0.02)))
    continents = (
        [(-98, 986), (-93, 994), (-87, 991), (-82, 978), (-79, 944), (-82, 902), (-86, 862), (-90, 846), (-93, 872), (-96, 912), (-100, 952)],  # norte de Suramérica
        [(-110, 990), (-104, 995), (-99, 987), (-101, 974), (-106, 968), (-110, 976)],  # istmo
        [(-67, 987), (-61, 980), (-56, 952), (-60, 924), (-66, 940), (-70, 966)],
        [(-124, 978), (-118, 987), (-114, 968), (-118, 950), (-123, 958)],
    )
    for shape in continents:
        polygon = [at(a, r) for a, r in shape]
        gx, gy = sum(p[0] for p in polygon) / len(polygon), sum(p[1] for p in polygon) / len(polygon)
        for i in range(len(polygon)):  # abanico de facetas desde el centro
            earth.append(poly([(gx, gy), polygon[i], polygon[(i + 1) % len(polygon)]], shade(land, (0.1, -0.02, 0.05, -0.1, 0.0)[i % 5])))
    andes = [at(-96, 950), at(-93, 968), at(-91, 930), at(-89, 900), at(-92, 910)]
    earth.append(poly(andes, shade(P["tierra"], 0.1)))  # la cordillera
    for a, r, w in ((-104, 930, 150), (-84, 880, 190), (-73, 960, 130), (-116, 900, 120), (-92, 800, 170)):  # nubes
        x, y = at(a, r)
        earth.append(soft([(x - w / 2, y), (x - w * 0.3, y - 22), (x + w * 0.1, y - 30), (x + w / 2, y - 6), (x + w * 0.3, y + 14), (x - w * 0.2, y + 12)], "#FFFFFF", 0.85))
    mx, my = at(-93.5, 958)
    marker = [f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="22" fill="{P["calabaza"]}" fill-opacity="0.3"/>', f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="8" fill="{P["calabaza"]}" stroke="#FFFFFF" stroke-width="3"/>']
    glow = [at(a, R + 14) for a in range(-132, -47, 2)]
    atmosphere = [f'<polyline points="{pts(glow)}" fill="none" stroke="#9FD3FF" stroke-width="20" stroke-opacity="0.35"/>']
    night = [soft([at(-132, R), at(-118, R), at(-124, R - 440), at(-132, R - 440)], "#0B1226", 0.35)]  # el lado en sombra
    return svg(W, H, [sky("cielo-orbita", "#0B1226", "#1B3358"), layer("estrellas", stars(rng, 90, 600)), layer("atmosfera", atmosphere),
                      layer("tierra", earth + night), layer("aqui", marker)])


def atmosfera():
    rng = Rng(17)
    sun = [(1090 + 60 * math.cos(math.pi / 4 * k + math.pi / 8), 250 + 60 * math.sin(math.pi / 4 * k + math.pi / 8)) for k in range(8)]
    return svg(W, H, [
        sky("cielo-atmosfera", "#14305C", "#A9CFE3"),
        layer("estrellas", stars(rng, 26, 220)),
        layer("sol", [f'<circle cx="1090" cy="250" r="120" fill="#FFF4D6" fill-opacity="0.25"/>', poly(sun, "#FFF1C9")]),
        layer("nubes-lejanas", clouds(rng, 470, 7, 260, "#DCEAF2", 0.9)),
        layer("nubes-medias", clouds(rng, 650, 5, 460, "#EEF5F9", 0.95)),
        layer("nubes-cercanas", clouds(rng, 880, 4, 760, "#FFFFFF", 1.0)),
    ])


def region():
    rng = Rng(23)
    return svg(W, H, [
        sky("cielo-region", "#7FA6BC", "#D6E6EE"),
        layer("lejano", ridge(rng, 440, 230, 5, P["oliva"], 0.62)),
        layer("niebla-lejana", fog_band(rng, 480, 4, 0.5)),
        layer("medio", ridge(rng, 570, 190, 6, P["oliva"], 0.34)),
        layer("niebla-media", fog_band(rng, 620, 3, 0.55)),
        layer("cercano", ridge(rng, 720, 170, 4, P["brote"], 0.1)),
        layer("primer-plano", ridge(rng, 860, 120, 6, P["oliva"], 0.0)),
    ])


def valle():
    rng = Rng(29)
    fields, _ = patchwork(rng, 560, rows=7)
    river = [(704, 560), (722, 560), (772, 660), (700, 770), (830, 900), (690, 900), (640, 780), (716, 664)]
    left = [(0, 250), (210, 380), (400, 610), (330, 900), (0, 900)]
    right = [(1440, 220), (1190, 400), (1030, 640), (1120, 900), (1440, 900)]
    flanks = [poly(left, shade(P["oliva"], -0.18)), poly([(0, 250), (210, 380), (120, 900), (0, 900)], shade(P["oliva"], -0.08)),
              poly(right, shade(P["oliva"], -0.28)), poly([(1440, 220), (1190, 400), (1300, 900), (1440, 900)], shade(P["oliva"], -0.2))]
    return svg(W, H, [
        sky("cielo-valle", "#84ABC1", "#DAE8EE"),
        layer("lejano", ridge(rng, 420, 200, 5, P["oliva"], 0.55, bottom=580)),
        layer("medio", ridge(rng, 520, 130, 6, P["brote"], 0.28, bottom=590)),
        layer("niebla", fog_band(rng, 560, 4, 0.6)),
        layer("parcelas", fields),
        layer("rio", [poly(river, WATER), poly(river[:4] + [river[-1]], shade(WATER, 0.12))]),
        layer("laderas", flanks),
    ])


def municipio():
    rng = Rng(37)
    fields, hi = patchwork(rng, 430, highlight=(5, 6))
    town = [p for dx, dy, k in ((0, 0, 1.0), (40, 8, 0.8), (-34, 10, 0.85), (74, 4, 0.7), (-66, 6, 0.7)) for p in house(960 + dx * 1.3, 512 + dy, 0.3 * k)]
    return svg(W, H, [
        sky("cielo-municipio", "#86AEC3", "#DCE9EF"),
        layer("lejano", ridge(rng, 330, 190, 5, P["oliva"], 0.5, bottom=470)),
        layer("medio", ridge(rng, 420, 120, 6, P["oliva"], 0.22, bottom=480)),
        layer("niebla", fog_band(rng, 440, 4, 0.6)),
        layer("parcelas", fields),
        layer("pueblo", town + church(986, 500, 0.24)),
        layer("lote-resaltado", hi),
    ])


def vereda():
    rng = Rng(41)
    horizon = 460
    plots = (  # parcelas grandes, cerca: (esquinas, color)
        ([(-40, horizon), (430, horizon), (300, 640), (-200, 640)], P["trigo"]),
        ([(430, horizon), (930, horizon), (980, 640), (300, 640)], P["brote"]),
        ([(930, horizon), (1480, horizon), (1640, 640), (980, 640)], P["oliva"]),
        ([(-200, 640), (300, 640), (150, 900), (-420, 900)], P["tierra"]),
        ([(300, 640), (980, 640), (1100, 900), (150, 900)], shade(P["brote"], -0.12)),
        ([(980, 640), (1640, 640), (1900, 900), (1100, 900)], P["trigo"]),
    )
    ground = []
    for quad, color in plots:
        ground.append(poly(quad, color, shade(P["oliva"], -0.35), 3))
        ground.append(poly([quad[0], quad[1], quad[3]], shade(color, 0.07)))
    road = [(600, horizon), (640, horizon), (1010, 900), (760, 900)]
    trees = [p for x, y, s in ((120, 470, 0.9), (190, 476, 0.7), (1260, 474, 1.0), (1330, 480, 0.75), (860, 468, 0.6)) for p in tree(x, y, s)]
    return svg(W, H, [
        sky("cielo-vereda", "#8AB1C6", "#E0ECF1"),
        layer("lejano", ridge(rng, 380, 210, 4, P["oliva"], 0.5, bottom=horizon + 10)),
        layer("medio", ridge(rng, 440, 110, 6, P["brote"], 0.2, bottom=horizon + 10)),
        layer("niebla", fog_band(rng, horizon - 6, 3, 0.55)),
        layer("parcelas", ground),
        layer("camino", [poly(road, "#D9B88A"), poly([road[0], ((road[0][0] + road[1][0]) / 2, horizon), (885, 900), road[3]], "#E6CBA2")]),
        layer("arboles", trees),
        layer("casa", house(1040, 560, 1.25, trim=D["brote"])),
        layer("lote-resaltado", [poly(plots[4][0], "none", P["calabaza"], 7)]),
    ])


def lote(gid="cielo-lote", sky_colors=("#8FB4C8", "#E4EEF2"), plant=1.0, color=None, flower=False, rain=False, sacks=False, soil=0.0):
    """El lote a ras de suelo. Los parámetros cambian la estación: lo usa el recorrido «El año del cultivo»."""
    rng = Rng(53)
    horizon, vx = 470, 760
    earth = shade(P["tierra"], soil)
    ground, plants = [poly([(0, horizon), (W, horizon), (W, H), (0, H)], shade(earth, -0.1))], []
    rows = 13
    for i in range(rows):  # surcos que convergen en el horizonte
        x0, x1 = -500 + i * (W + 1000) / rows, -500 + (i + 0.55) * (W + 1000) / rows
        t0, t1 = vx + (x0 - vx) * 0.04, vx + (x1 - vx) * 0.04
        ground.append(poly([(t0, horizon), (t1, horizon), (x1, H), (x0, H)], shade(earth, 0.06 if i % 2 else 0.14)))
        for k in range(1, 8):
            f = (k / 8) ** 1.9
            plants.append((horizon + (H - horizon) * f, (t0 + t1) / 2 + ((x0 + x1) / 2 - (t0 + t1) / 2) * f, 0.5 + 3.4 * f))
    crop = [p for y, x, s in sorted(plants) for p in sprout(x, y, s * plant, color, flower)] if plant > 0 else []
    fence = []
    for k in range(6):
        f = (k / 6) ** 1.6
        x, y, s = 250 - 330 * f, horizon + 20 + (H - horizon - 60) * f, 0.5 + 1.6 * f
        fence.append(poly([(x, y), (x + 9 * s, y), (x + 9 * s, y - 70 * s), (x + 4.5 * s, y - 80 * s), (x, y - 70 * s)], P["tierra"]))
        fence.append(poly([(x + 4.5 * s, y), (x + 9 * s, y), (x + 9 * s, y - 70 * s), (x + 4.5 * s, y - 80 * s)], D["tierra"]))
    extra = []
    if sacks:  # costales de la cosecha
        for x, y, s in ((1090, 800, 2.6), (1200, 840, 3.0), (1010, 850, 2.2)):
            extra.append(poly([(x - 14 * s, y), (x - 18 * s, y - 26 * s), (x - 6 * s, y - 44 * s), (x - 10 * s, y - 52 * s), (x + 10 * s, y - 52 * s), (x + 6 * s, y - 44 * s), (x + 18 * s, y - 26 * s), (x + 14 * s, y)], P["trigo"], D["trigo"], 3))
            extra.append(poly([(x - 6 * s, y - 44 * s), (x + 6 * s, y - 44 * s), (x, y), (x - 14 * s, y), (x - 18 * s, y - 26 * s)], shade(P["trigo"], 0.14)))
    if rain:
        for _ in range(70):
            x, y, ln = rng.between(-40, W), rng.between(0, H - 60), rng.between(26, 54)
            extra.append(f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x - ln * 0.3:.0f}" y2="{y + ln:.0f}" stroke="#DCEFFA" stroke-width="3" stroke-opacity="0.7" stroke-linecap="round"/>')
    return svg(W, H, [
        sky(gid, *sky_colors),
        layer("lejano", ridge(rng, 400, 230, 4, P["oliva"], 0.5, bottom=horizon + 10)),
        layer("medio", ridge(rng, 450, 130, 6, P["brote"], 0.2, bottom=horizon + 10)),
        layer("niebla", fog_band(rng, horizon - 8, 4, 0.55)),
        layer("suelo", ground),
        layer("cultivo", crop),
        layer("cerca", fence),
        layer("estacion", extra),
    ])


# ---------- Recorrido C · travesía por la cordillera ----------

def paramo():
    rng = Rng(61)
    moor = "#9A9358"
    lake = [(820, 560), (1000, 548), (1090, 575), (1000, 606), (840, 600)]
    plants = sorted(((rng.between(500, 880), rng.between(-40, W + 40)) for _ in range(26)))
    fr = [p for y, x in plants for p in frailejon(x, y, 0.5 + (y - 500) / 380 * 2.2)]
    return svg(W, H, [
        sky("cielo-paramo", "#93A9B6", "#E3EAED"),
        layer("lejano", ridge(rng, 380, 170, 4, moor, 0.6, bottom=520)),
        layer("niebla-alta", fog_band(rng, 420, 5, 0.7)),
        layer("medio", ridge(rng, 500, 110, 5, moor, 0.3, bottom=600)),
        layer("suelo", [poly([(0, 540), (W, 520), (W, H), (0, H)], moor), poly([(0, 540), (700, 530), (300, H), (0, H)], shade(moor, 0.08))]),
        layer("laguna", [poly(lake, "#5D8FA8"), poly([lake[0], lake[1], lake[4]], "#7FB0C6")]),
        layer("frailejones", fr),
        layer("niebla-baja", fog_band(rng, 700, 3, 0.45)),
    ])


def ladera():
    rng = Rng(67)
    slope = [(0, 420), (520, 520), (1000, 660), (W, 760), (W, H), (0, H)]
    forest = sorted(((rng.between(470, 880), rng.between(-20, W)) for _ in range(46)))
    trees = [p for y, x in forest if y > 430 + x * 0.22 for p in tree(x, y, 0.6 + (y - 470) / 410 * 1.5, rng.pick((P["oliva"], shade(P["oliva"], -0.2), D["brote"])))]
    stream = [(980, 520), (1000, 520), (1090, 700), (1180, 900), (1100, 900), (1040, 710)]
    return svg(W, H, [
        sky("cielo-ladera", "#86AEC3", "#DCE9EF"),
        layer("lejano", ridge(rng, 400, 210, 4, P["oliva"], 0.55, bottom=640)),
        layer("medio", ridge(rng, 520, 150, 5, P["brote"], 0.25, bottom=700)),
        layer("niebla", fog_band(rng, 560, 3, 0.55)),
        layer("pendiente", [poly(slope, shade(P["oliva"], -0.05)), poly([(0, 420), (520, 520), (260, H), (0, H)], shade(P["oliva"], 0.05))]),
        layer("quebrada", [poly(stream, WATER)]),
        layer("bosque", trees),
    ])


def pueblo():
    rng = Rng(71)
    plaza = [(0, 600), (W, 600), (W, H), (0, H)]
    row = [p for x, s, trim in ((60, 1.5, D["brote"]), (260, 1.3, "#2E6F9E"), (1040, 1.3, D["rojo"]), (1230, 1.5, D["brote"])) for p in house(x, 640, s, trim=trim)]
    return svg(W, H, [
        sky("cielo-pueblo", "#8AB1C6", "#E0ECF1"),
        layer("lejano", ridge(rng, 400, 230, 4, P["oliva"], 0.5, bottom=620)),
        layer("medio", ridge(rng, 500, 150, 5, P["brote"], 0.2, bottom=620)),
        layer("plaza", [poly(plaza, "#D9D2C2"), poly([(0, 600), (W, 600), (W * 0.7, H), (W * 0.3, H)], "#E6E0D2")]),
        layer("iglesia", church(720, 640, 1.5)),
        layer("casas", row),
        layer("arboles", tree(520, 700, 1.4) + tree(930, 700, 1.4)),
    ])


SCENES = {
    "a1-orbita": orbita, "a2-atmosfera": atmosfera, "a3-region": region, "a4-valle": valle,
    "a5-municipio": municipio, "a6-vereda": vereda, "a7-lote": lote,
    "c1-paramo": paramo, "c2-ladera": ladera, "c4-pueblo": pueblo,
}

# Recorrido B: el mismo lote a lo largo del año.
YEAR = {
    "b1-preparar": dict(gid="cielo-b1", sky_colors=("#A7B4BD", "#E6E9E6"), plant=0, soil=-0.12),
    "b2-sembrar": dict(gid="cielo-b2", sky_colors=("#6F8A9C", "#C3D2DA"), plant=0.42, rain=True, soil=-0.2),
    "b3-crecer": dict(gid="cielo-b3", sky_colors=("#7FB0CC", "#E4F0F5"), plant=1.25),
    "b4-cosechar": dict(gid="cielo-b4", sky_colors=("#E0A65A", "#F7E3B4"), plant=1.3, color=P["trigo"], sacks=True),
    "b5-rotar": dict(gid="cielo-b5", sky_colors=("#8FB4C8", "#E4EEF2"), plant=0.9, color="#B5D96A", flower=True),
}
for _name, _kw in YEAR.items():
    SCENES[_name] = (lambda kw: lambda: lote(**kw))(_kw)


def main():
    out = DIR / "svg"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.svg"):
        old.unlink()
    total = packed = 0
    for name, draw in SCENES.items():
        data = draw().encode("utf-8")
        (out / f"{name}.svg").write_bytes(data)
        total, packed = total + len(data), packed + len(gzip.compress(data))
        print(f"{name}.svg  {len(data) / 1024:6.1f} KB")
    print(f"{len(SCENES)} escenas: {total / 1024:.0f} KB en total, {packed / 1024:.0f} KB comprimidas")


if __name__ == "__main__":
    main()
