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


def field(cx, cy, rows, cols, plant, s, seed=1, jitter=0.03):
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


# ---------- Catálogo ----------

STAGES = {
    "anual": ("Siembra", "Emergencia", "Desarrollo", "Floración", "Llenado", "Cosecha"),
    "raiz": ("Siembra", "Emergencia", "Hojas", "Crecimiento", "Engrose", "Cosecha"),
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
)


def stage_cell(crop, s, cx, cy):
    key, _, _, _, plant, rows, cols, ridged, extras, *_ = crop
    out = block(cx, cy, rows, ridged=ridged, cut=extras[4][1] if s == 4 and 4 in extras and extras[4][0] == "cut" else None)
    if s == 0:  # siembra: semillas marcadas sobre el surco
        rnd = random.Random(3)
        for r in range(rows):
            for c in range(cols):
                x, y = at(cx, cy, (c + 0.5) / cols, (r + 0.5) / rows)
                out.append(poly([(x, y - 3), (x + 2.5, y), (x, y + 2), (x - 2.5, y)], "#E8D9B0" if rnd.random() > 0.5 else "#D9C79A"))
    if "all" in extras and s > 0:
        out += extras["all"][1](cx, cy, rows, s)
    if s == 5 and 5 in extras and extras[5][0] == "ground":
        out += extras[5][1](cx, cy)
    elif s > 0:
        out += field(cx, cy, rows, cols, plant, s, seed=sum(map(ord, key)))
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
