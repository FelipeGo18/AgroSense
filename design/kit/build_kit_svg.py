"""Geometría del kit de componentes en estilo diorama low-poly (HU-153).

Genera un SVG por pieza en design/kit/svg/ y una vista previa (preview.html).
Los SVG solo llevan formas; los textos se ponen aparte en Figma para que sigan siendo editables.
Colores: los de design/tokens/tokens.json. Solo usa la biblioteca estándar.

    python design/kit/build_kit_svg.py
"""

import json
from pathlib import Path

DIR = Path(__file__).parent
OUT = DIR / "svg"
TOKENS = json.loads((DIR.parent / "tokens" / "tokens.json").read_text(encoding="utf-8"))

P = {k: v["$value"] for k, v in TOKENS["color"]["paleta"].items() if not k.startswith("$")}
D = {k: v["$value"] for k, v in TOKENS["color"]["oscuro"].items() if not k.startswith("$")}
BORDE = "#B4C3CC"
OLIVA_BORDE = "#3A4A1D"
TRIGO_BORDE = "#B8862E"
ROJO_BORDE = "#7E251B"
WHITE = "#FFFFFF"


def shade(hex_color, f):
    """Aclara (f > 0) u oscurece (f < 0) un color; sirve para las facetas."""
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    if f >= 0:
        r, g, b = (round(c + (255 - c) * f) for c in (r, g, b))
    else:
        r, g, b = (round(c * (1 + f)) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def pts(points):
    return " ".join(f"{x:g},{y:g}" for x, y in points)


def chamfer(x, y, w, h, c):
    """Rectángulo con las cuatro esquinas biseladas: la firma visual del kit."""
    if c <= 0:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return [(x + c, y), (x + w - c, y), (x + w, y + c), (x + w, y + h - c),
            (x + w - c, y + h), (x + c, y + h), (x, y + h - c), (x, y + c)]


def poly(points, fill, stroke=None, sw=0, dash=None):
    extra = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"' if stroke else ""
    if dash:
        extra += f' stroke-dasharray="{dash}"'
    return f'<polygon points="{pts(points)}" fill="{fill}"{extra}/>'


def svg(w, h, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(body)}</svg>'


def facets(x, y, w, h, c, base):
    """Cara triangulada low-poly: tiras de triángulos con tonos alternos y puntas biseladas
    (punta izquierda con luz, derecha en sombra, como la luz lateral del moodboard)."""
    out = []
    if c > 0:
        out.append(poly([(x + c, y), (x + c, y + h), (x, y + h - c), (x, y + c)], shade(base, 0.12)))
        out.append(poly([(x + w - c, y), (x + w, y + c), (x + w, y + h - c), (x + w - c, y + h)], shade(base, -0.12)))
    x0, x1 = x + max(c, 0), x + w - max(c, 0)
    span = x1 - x0
    top = [x0 + span * t for t in (0, 0.22, 0.47, 0.71, 1)]
    bot = [x0 + span * t for t in (0, 0.11, 0.35, 0.6, 0.86, 1)]
    tones = (0.06, -0.015, 0.035, -0.05, 0.015, -0.03, 0.045, -0.065, 0.0)
    tris = []
    for i in range(len(top) - 1):
        tris.append([(top[i], y), (top[i + 1], y), (bot[i + 1], y + h)])
        tris.append([(top[i], y), (bot[i + 1], y + h), (bot[i], y + h)])
    tris.append([(top[-1], y), (bot[-1], y + h), (bot[-2], y + h)])
    for tri, f in zip(tris, tones):
        out.append(poly(tri, shade(base, f)))
    return out


# ---------- Botón: un bloque con cara superior facetada y canto inferior ----------

def button(top, side, depth=6, w=240, h=52, c=10, faceted=True, ring=False):
    pad = 6 if ring else 0
    W, H = w + 2 * pad, h + 6 + 2 * pad
    body = []
    if ring:
        body.append(poly(chamfer(1.5, 1.5, W - 3, H - 3, c + 4), "none", P["noche"], 3))
    ox, oy = pad, pad + (6 - depth)
    if depth:
        body.append(poly(chamfer(ox, oy + depth, w, h, c), side))
    body.append(poly(chamfer(ox, oy, w, h, c), top))
    if faceted:
        body += facets(ox, oy, w, h, c, top)
    return svg(W, H, body)


def spinner(color, size=22):
    # Hexágono facetado que gira en código; en Figma queda quieto.
    import math
    cx = cy = size / 2
    r = size / 2 - 1
    hexa = [(cx + r * math.cos(math.pi / 3 * i - math.pi / 2), cy + r * math.sin(math.pi / 3 * i - math.pi / 2)) for i in range(6)]
    half = [hexa[0], hexa[1], hexa[2], hexa[3], (cx, cy)]
    return svg(size, size, [poly(hexa, "none", color, 2.5), poly(half, color)])


# ---------- Semáforo: letrero clavado en la parcela ----------

LIGHTS = {
    "verde": dict(fill=P["brote"], stroke=D["brote"], c=26, icon="octagon", ink=P["noche"], dash=None),
    "amarillo": dict(fill=P["trigo"], stroke=D["trigo"], c=10, icon="triangle", ink=P["noche"], dash=None),
    "rojo": dict(fill=P["rojo"], stroke=ROJO_BORDE, c=0, icon="square", ink=WHITE, dash=None),
    "no-evaluable": dict(fill=P["niebla"], stroke=D["cielo"], c=10, icon="ring", ink=P["noche"], dash="9 6"),
    "cargando": dict(fill=P["niebla"], stroke=BORDE, c=10, icon="spinner", ink=D["cielo"], dash=None),
}


def icon(kind, x, y, ink, s=20):
    import math
    if kind == "octagon":
        r = s / 2
        cx, cy = x + r, y + r
        pts8 = [(cx + r * math.cos(math.pi / 4 * i + math.pi / 8), cy + r * math.sin(math.pi / 4 * i + math.pi / 8)) for i in range(8)]
        return [poly(pts8, ink)]
    if kind == "triangle":
        return [poly([(x + s / 2, y), (x + s, y + s * 0.9), (x, y + s * 0.9)], ink)]
    if kind == "square":
        return [poly([(x + 2, y + 2), (x + s - 2, y + 2), (x + s - 2, y + s - 2), (x + 2, y + s - 2)], ink)]
    if kind == "ring":
        r = s / 2 - 1.5
        cx, cy = x + s / 2, y + s / 2
        pts8 = [(cx + r * math.cos(math.pi / 4 * i + math.pi / 8), cy + r * math.sin(math.pi / 4 * i + math.pi / 8)) for i in range(8)]
        return [poly(pts8, "none", ink, 2.5, "4 3")]
    if kind == "spinner":
        r = s / 2 - 1
        cx, cy = x + s / 2, y + s / 2
        hexa = [(cx + r * math.cos(math.pi / 3 * i - math.pi / 2), cy + r * math.sin(math.pi / 3 * i - math.pi / 2)) for i in range(6)]
        return [poly(hexa, "none", ink, 2.5), poly([hexa[0], hexa[1], hexa[2], hexa[3], (cx, cy)], ink)]
    return []


def sign(key, w=320, h=56):
    s = LIGHTS[key]
    post_h, post_w = 34, 16
    W, H = w + 6, h + post_h + 6
    body = []
    px = W / 2 - post_w / 2
    post = [(px, h - 4), (px + post_w, h - 4), (px + post_w, H - 8), (px + post_w / 2, H), (px, H - 8)]
    if key == "no-evaluable":
        body.append(poly(post, "none", D["cielo"], 2.5, "6 4"))
    else:
        body.append(poly(post, P["tierra"]))
        body.append(poly([(px + post_w / 2, h - 4), (px + post_w, h - 4), (px + post_w, H - 8), (px + post_w / 2, H)], D["tierra"]))
    board = chamfer(3, 3, w, h, s["c"])
    body.append(poly(board, s["fill"], s["stroke"], 3, s["dash"]))
    if key not in ("no-evaluable", "cargando"):
        body += facets(3, 3, w, h, s["c"], s["fill"])
        body.append(poly(board, "none", s["stroke"], 3))
    body += icon(s["icon"], 3 + max(s["c"], 14) + 4, 3 + h / 2 - 10, s["ink"])
    return svg(W, H, body)


# ---------- Tarjeta de señal: letrero de campo con banderín de estado ----------

STATUS = {
    "favorable": dict(fill=P["brote"], stroke=D["brote"], icon="octagon", ink=P["noche"]),
    "moderado": dict(fill=P["trigo"], stroke=D["trigo"], icon="triangle", ink=P["noche"]),
    "desfavorable": dict(fill=P["rojo"], stroke=ROJO_BORDE, icon="square", ink=WHITE),
    "insuficiente": dict(fill=WHITE, stroke=D["cielo"], icon="question", ink=P["noche"]),
}


def kind_icon(kind, x, y):
    """Ícono low-poly del tipo de señal, 44 × 44."""
    if kind == "clima":  # nube facetada con gota
        return [
            poly([(x + 6, y + 26), (x + 12, y + 14), (x + 22, y + 10), (x + 32, y + 14), (x + 38, y + 24), (x + 34, y + 30), (x + 10, y + 30)], P["niebla"], D["cielo"], 2),
            poly([(x + 12, y + 14), (x + 22, y + 10), (x + 20, y + 30), (x + 10, y + 30)], shade(P["niebla"], -0.06)),
            poly([(x + 24, y + 33), (x + 28, y + 40), (x + 24, y + 44), (x + 20, y + 40)], D["cielo"]),
        ]
    if kind == "oferta":  # brote en un surco
        return [
            poly([(x + 2, y + 34), (x + 42, y + 34), (x + 38, y + 42), (x + 6, y + 42)], P["tierra"]),
            poly([(x + 21, y + 34), (x + 23, y + 34), (x + 23, y + 16), (x + 21, y + 16)], D["brote"]),
            poly([(x + 22, y + 22), (x + 8, y + 12), (x + 12, y + 26)], P["brote"]),
            poly([(x + 22, y + 18), (x + 38, y + 6), (x + 34, y + 22)], shade(P["brote"], -0.1)),
        ]
    if kind == "mercado":  # costal facetado
        return [
            poly([(x + 14, y + 8), (x + 30, y + 8), (x + 26, y + 14), (x + 38, y + 30), (x + 34, y + 42), (x + 10, y + 42), (x + 6, y + 30), (x + 18, y + 14)], P["trigo"], D["trigo"], 2),
            poly([(x + 18, y + 14), (x + 26, y + 14), (x + 22, y + 42), (x + 10, y + 42), (x + 6, y + 30)], shade(P["trigo"], 0.12)),
            poly([(x + 16, y + 14), (x + 28, y + 14), (x + 28, y + 17), (x + 16, y + 17)], D["trigo"]),
        ]
    return []


def card(kind, status, w=500, h=250, loading=False):
    W, H = w + 6, h + 40
    c = 16
    body = []
    for px in (60, w - 76):  # dos estacas
        body.append(poly([(px, h - 6), (px + 16, h - 6), (px + 16, H - 8), (px + 8, H), (px, H - 8)], P["tierra"]))
        body.append(poly([(px + 8, h - 6), (px + 16, h - 6), (px + 16, H - 8), (px + 8, H)], D["tierra"]))
    board = chamfer(3, 3, w, h, c)
    insufficient = status == "insuficiente"
    body.append(poly(board, WHITE, D["cielo"] if insufficient else BORDE, 3, "3 5" if insufficient else None))
    if insufficient:  # bruma: nubes facetadas de niebla, nunca color de riesgo (R1)
        for cx, cy, k in ((w * 0.62, 196, 1.0), (w * 0.25, 214, 0.8), (w * 0.86, 222, 0.7)):
            cloud = [(cx - 90 * k, cy + 18 * k), (cx - 70 * k, cy - 6 * k), (cx - 30 * k, cy - 20 * k), (cx + 14 * k, cy - 26 * k),
                     (cx + 60 * k, cy - 12 * k), (cx + 92 * k, cy + 8 * k), (cx + 80 * k, cy + 20 * k)]
            body.append(poly(cloud, P["niebla"]))
            body.append(poly([cloud[2], cloud[3], cloud[4], (cx + 10 * k, cy + 20 * k)], shade(P["niebla"], -0.05)))
    if loading:
        body.append(poly(chamfer(28, 82, 220, 52, 10), P["niebla"]))
        body.append(poly(chamfer(28, 152, w - 56, 18, 4), P["niebla"]))
        body.append(poly(chamfer(28, 182, w - 140, 18, 4), P["niebla"]))
    else:
        st = STATUS[status]
        tag = chamfer(28, 82, 240, 52, 10 if status != "desfavorable" else 0)
        body.append(poly(tag, st["fill"], st["stroke"], 3, None))
        if not insufficient:
            body += facets(28, 82, 240, 52, 10 if status != "desfavorable" else 0, st["fill"])
            body.append(poly(tag, "none", st["stroke"], 3))
        else:
            body.append(poly(tag, "none", st["stroke"], 3, "3 5"))
        if st["icon"] != "question":
            body += icon(st["icon"], 46, 98, st["ink"])
    body += kind_icon(kind, w - 60, 20)
    return svg(W, H, body)


# ---------- Prioridad: «nada» + cinco semillas que se tocan ----------

def seed(x, y, filled, focus=False):
    w, h = 26, 38
    cx = x + 22
    shape = [(cx, y + 3), (cx + w / 2, y + 14), (cx + w / 2, y + 26), (cx, y + 3 + h), (cx - w / 2, y + 26), (cx - w / 2, y + 14)]
    body = []
    if focus:
        body.append(poly(chamfer(x - 2, y - 2, 48, 48, 10), "none", P["noche"], 3))
    if filled:
        body.append(poly(shape, P["brote"], D["brote"], 2.5))
        body.append(poly([shape[0], shape[1], shape[2], shape[3]], shade(P["brote"], -0.14)))
    else:
        body.append(poly(shape, WHITE, D["cielo"], 2))
    return body


def priority_row(value, focus_index=None):
    body = []
    zero_on = value == 0
    body.append(poly(chamfer(2, 2, 44, 44, 8), P["niebla"] if zero_on else WHITE, P["noche"] if zero_on else BORDE, 2.5))
    for i in range(5):
        body += seed(56 + i * 50, 2, i < value, focus=(focus_index == i))
    return svg(56 + 5 * 50 + 4, 50, body)


# ---------- Selector con autocompletado ----------

def field(state):
    w, h, c = 500, 52, 10
    stroke = {"focus": P["noche"], "normal": BORDE, "disabled": BORDE}[state]
    fill = P["niebla"] if state == "disabled" else WHITE
    body = [poly(chamfer(2, 2, w, h, c), fill, stroke, 3)]
    if state != "disabled":  # canto interior: el campo parece hundido en el terreno
        body.append(poly([(2 + c, 3.5), (2 + w - c, 3.5), (2 + w - c - 3, 8), (2 + c + 3, 8)], P["niebla"]))
    return svg(w + 4, h + 4, body)


def dropdown(rows=2, active=0):
    w, row = 500, 52
    h = rows * row + 12
    body = [poly(chamfer(2, 8, w, h, 12), BORDE), poly(chamfer(2, 2, w, h, 12), WHITE, BORDE, 2)]
    for i in range(rows):
        if i == active:
            y = 8 + i * row
            body.append(poly(chamfer(8, y, w - 12, row - 4, 8), shade(P["brote"], 0.72)))
            body.append(poly([(20, y + 16), (28, y + 24), (20, y + 32), (12, y + 24)], D["brote"]))
    return svg(w + 4, h + 10, body)


# ---------- Rótulos ----------

def example_tag(w=300, h=40):
    body = [
        poly([(14, 2), (w, 2), (w, h), (14, h), (2, h / 2)], P["calabaza"], D["calabaza"], 2),
        poly([(14, 2), (w * 0.45, 2), (w * 0.3, h), (14, h), (2, h / 2)], shade(P["calabaza"], 0.1)),
    ]
    body.append(f'<circle cx="16" cy="{h / 2}" r="4" fill="{WHITE}" stroke="{D["calabaza"]}" stroke-width="2"/>')
    return svg(w + 2, h + 2, body)


def estimate_board(w=760, h=48):
    body = [poly(chamfer(2, 2, w, h, 10), P["niebla"], D["cielo"], 2)]
    x, y = 16, 10  # gota low-poly
    body.append(poly([(x + 12, y), (x + 22, y + 16), (x + 18, y + 26), (x + 6, y + 26), (x + 2, y + 16)], P["cielo"], D["cielo"], 2))
    body.append(poly([(x + 12, y), (x + 22, y + 16), (x + 18, y + 26), (x + 12, y + 26)], D["cielo"]))
    return svg(w + 4, h + 4, body)


def panel(w, h):
    """Panel de sección: tabla biselada con canto, como un bloque más del diorama."""
    return svg(w + 2, h + 10, [poly(chamfer(1, 9, w, h, 24), BORDE), poly(chamfer(1, 1, w, h, 24), WHITE)])


PIECES = {
    "boton-primario": button(D["oliva"], OLIVA_BORDE),
    "boton-primario-presionado": button(D["oliva"], OLIVA_BORDE, depth=1),
    "boton-primario-foco": button(D["oliva"], OLIVA_BORDE, ring=True),
    "boton-deshabilitado": button(P["niebla"], P["niebla"], depth=0, faceted=False),
    "boton-secundario": button(P["trigo"], TRIGO_BORDE),
    "spinner-blanco": spinner(WHITE),
    **{f"semaforo-{k}": sign(k) for k in LIGHTS},
    "senal-clima-favorable": card("clima", "favorable"),
    "senal-oferta-desfavorable": card("oferta", "desfavorable"),
    "senal-mercado-insuficiente": card("mercado", "insuficiente"),
    "senal-clima-cargando": card("clima", None, loading=True),
    "prioridad-3": priority_row(3),
    "prioridad-5-foco": priority_row(5, focus_index=4),
    "prioridad-2": priority_row(2),
    "prioridad-0": priority_row(0),
    "campo-foco": field("focus"),
    "campo-normal": field("normal"),
    "campo-deshabilitado": field("disabled"),
    "lista-2": dropdown(2, 0),
    "lista-vacia": dropdown(1, -1),
    "rotulo-ejemplo": example_tag(),
    "rotulo-estimacion": estimate_board(),
    "panel-1140x480": panel(1140, 480),
    "panel-1140x460": panel(1140, 460),
    "panel-2320x420": panel(2320, 420),
    "panel-2320x190": panel(2320, 190),
}


def main():
    OUT.mkdir(exist_ok=True)
    for name, markup in PIECES.items():
        (OUT / f"{name}.svg").write_text(markup, encoding="utf-8", newline="\n")
    tiles = "".join(
        f'<figure><img src="svg/{n}.svg" alt=""><figcaption>{n}</figcaption></figure>' for n in PIECES if not n.startswith("panel")
    )
    (DIR / "preview.html").write_text(
        "<!doctype html><html lang=es><meta charset=utf-8><title>Kit diorama</title>"
        "<style>body{margin:0;padding:32px;background:#8FA9B8;font:14px system-ui;display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start}"
        "figure{margin:0;padding:12px;background:#DCE5EA88}figcaption{color:#1E2A3A;margin-top:6px}</style>"
        f"{tiles}</html>",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{len(PIECES)} piezas en {OUT}")


if __name__ == "__main__":
    main()
