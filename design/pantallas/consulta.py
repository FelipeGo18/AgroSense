"""Piezas compartidas de la consulta. No escribe pantallas: las de la consulta están en diagnostico.py y detalle.py.

- `tag`: el estado de una señal con forma, texto y color, nunca solo color (W2, R1);
- `kind`: los íconos de heladas, suelo, oferta y mercado (agua y calor están en senales.py);
- `mist`: la bruma de «sin datos»;
- `light`: el letrero del semáforo;
- `bars`, `frost_chart` y `ph_scale`: las gráficas del detalle de las señales (HU-093).
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401  (agrega design/kit y design/mascota al camino de importación)
from build_kit_svg import STATUS, facets, icon, kind_icon, sign  # noqa: E402
from ui import BORDE, D, P, SEC, WHITE, chamfer, group, inner, poly, shade, text  # noqa: E402

# ---------- Piezas ----------

TAGS = {  # forma + texto + color, nunca solo color (W2, R1)
    "favorable": ("Favorable", "octagon"),
    "moderado": ("Moderado", "triangle"),
    "desfavorable": ("Desfavorable", "square"),
    "insuficiente": ("Sin datos", None),
    "no-aplica": ("No aplica", None),
}


def tag(x, y, status, w=176, h=38, critical=False):
    label, shape = TAGS[status]
    if status == "no-aplica":
        body = [poly(chamfer(0, 0, w, h, 8), WHITE, D["cielo"], 2.5), f'<rect x="14" y="{h / 2 - 2:g}" width="16" height="4" fill="{D["cielo"]}"/>']
        ink = P["noche"]
    elif status == "insuficiente":
        body = [poly(chamfer(0, 0, w, h, 8), WHITE, D["cielo"], 2.5, "3 5"),
                text(22, h / 2 + 6, "?", 18, 700, D["cielo"], anchor="middle")]
        ink = P["noche"]
    else:
        st = STATUS[status]
        c = 0 if status == "desfavorable" else 8
        body = [poly(chamfer(0, 0, w, h, c), st["fill"])] + facets(0, 0, w, h, c, st["fill"]) + [poly(chamfer(0, 0, w, h, c), "none", st["stroke"], 2.5)]
        body += icon(shape, 12, h / 2 - 8, st["ink"], 16)
        ink = st["ink"]
    body.append(text(38, h / 2 + 6, label, 16, 700, ink))
    if critical:
        body += [poly(chamfer(w + 8, 4, 74, h - 8, 4), WHITE, P["rojo"], 2), text(w + 45, h / 2 + 5, "Crítica", 14, 700, P["rojo"], anchor="middle")]
    return [group(f"estado-{status}", body, x, y)]


def kind(k, x, y):
    if k == "oferta":
        return kind_icon("oferta", x, y)
    if k == "mercado":
        return kind_icon("mercado", x, y)
    if k == "heladas":  # cristal de hielo facetado
        cx, cy, out = x + 22, y + 22, []
        for i in range(6):
            a = math.radians(60 * i - 90)
            tip = (cx + 20 * math.cos(a), cy + 20 * math.sin(a))
            left = (cx + 7 * math.cos(a - 0.5), cy + 7 * math.sin(a - 0.5))
            right = (cx + 7 * math.cos(a + 0.5), cy + 7 * math.sin(a + 0.5))
            out.append(poly([(cx, cy), left, tip], P["niebla"], D["cielo"], 1.5))
            out.append(poly([(cx, cy), tip, right], shade(P["niebla"], -0.12)))
        return out
    if k == "suelo":  # terrón con capas
        return [poly([(x + 4, y + 16), (x + 40, y + 16), (x + 42, y + 24), (x + 2, y + 24)], P["brote"], D["brote"], 1.5),
                poly([(x + 2, y + 24), (x + 42, y + 24), (x + 40, y + 33), (x + 4, y + 33)], P["tierra"]),
                poly([(x + 4, y + 33), (x + 40, y + 33), (x + 36, y + 42), (x + 8, y + 42)], D["tierra"]),
                poly([(x + 12, y + 27), (x + 18, y + 27), (x + 16, y + 30)], shade(P["tierra"], 0.25)),
                poly([(x + 28, y + 36), (x + 34, y + 36), (x + 31, y + 39)], shade(D["tierra"], 0.3))]
    return []


def mist(w, h):
    """Bruma de «sin datos»: nubes de niebla, nunca color de riesgo (R1)."""
    out = []
    for cx, cy, k in ((w * 0.7, h - 40, 0.9), (w * 0.3, h - 26, 0.7)):
        cloud = [(cx - 90 * k, cy + 16 * k), (cx - 66 * k, cy - 8 * k), (cx - 24 * k, cy - 22 * k), (cx + 18 * k, cy - 26 * k),
                 (cx + 62 * k, cy - 10 * k), (cx + 90 * k, cy + 10 * k), (cx + 76 * k, cy + 20 * k)]
        out.append(poly(cloud, P["niebla"]))
    return out


def light(key, x, y, scale):
    return [f'<g id="semaforo" transform="translate({x:g} {y:g}) scale({scale:g})">{inner(sign(key))}</g>']


# ---------- Gráficas ----------

def bars(x, y, w, h, values, labels, color, stroke, unit, ref=None, ref_label="", last_label="", hatch_last=False, y_max=None):
    """Gráfica de barras con su unidad y su referencia; el último periodo se marca (HU-093)."""
    out = [text(0, -14, unit, 14, 700, SEC)]
    vmax = y_max or max(values + ([ref] if ref else [])) * 1.15
    n = len(values)
    bw = w / n * 0.62
    out.append(f'<rect x="0" y="{h}" width="{w}" height="2" fill="{P["noche"]}"/>')
    for t in (0.5, 1.0):
        ty = h - h * t
        out.append(f'<rect x="0" y="{ty:.1f}" width="{w}" height="1" fill="{BORDE}"/>')
        out.append(text(-8, ty + 5, f"{round(vmax * t):,}".replace(",", "."), 12, fill=SEC, anchor="end"))
    for i, v in enumerate(values):
        bx = i * w / n + (w / n - bw) / 2
        bh = h * v / vmax
        last = i == n - 1
        if last and hatch_last:
            out.append(poly(chamfer(bx, h - bh, bw, bh, 3), WHITE, stroke, 2, "4 3"))
        else:
            out.append(poly(chamfer(bx, h - bh, bw, bh, 3), P["calabaza"] if last else color, D["calabaza"] if last else stroke, 1.5))
        out.append(text(bx + bw / 2, h + 20, labels[i], 12, 700 if last else 400, P["noche"] if last else SEC, anchor="middle"))
    if ref:
        ry = h - h * ref / vmax
        out.append(f'<line x1="0" y1="{ry:.1f}" x2="{w}" y2="{ry:.1f}" stroke="{P["noche"]}" stroke-width="2" stroke-dasharray="8 5"/>')
        out.append(text(w, ry - 8, ref_label, 13, 700, anchor="end"))
    if last_label:
        lx = (n - 1) * w / n + w / n / 2
        out.append(text(lx, h + 38, last_label, 12, 700, D["calabaza"], anchor="middle"))
    return [group("grafica", out, x, y)]


def frost_chart(x, y, w, h, freq, sow, sensitive, short=False):
    months = "EFMAMJJASOND"
    out = [text(0, -14, "% de años con helada" if short else "% de años con al menos una helada (mínima menor que 2 °C)", 14, 700, SEC)]
    n, vmax = 12, 30
    s0, s1 = sensitive
    out.append(f'<rect x="{s0 * w / n:.1f}" y="0" width="{(s1 - s0 + 1) * w / n:.1f}" height="{h}" fill="{P["calabaza"]}" fill-opacity="0.16"/>')
    out.append(text((s0 + (s1 - s0 + 1) / 2) * w / n, 16, "etapa sensible", 12, 700, D["calabaza"], anchor="middle"))
    out.append(f'<rect x="0" y="{h}" width="{w}" height="2" fill="{P["noche"]}"/>')
    for t in (0.5, 1.0):
        ty = h - h * t
        out.append(f'<rect x="0" y="{ty:.1f}" width="{w}" height="1" fill="{BORDE}"/>')
        out.append(text(-8, ty + 5, f"{round(vmax * t)} %", 12, fill=SEC, anchor="end"))
    bw = w / n * 0.62
    for i, v in enumerate(freq):
        bx = i * w / n + (w / n - bw) / 2
        bh = max(2, h * v / vmax)
        hot = s0 <= i <= s1
        out.append(poly(chamfer(bx, h - bh, bw, bh, 2), D["cielo"] if hot else P["niebla"], D["cielo"], 1.5))
        out.append(text(bx + bw / 2, h + 20, months[i], 12, 700 if i == sow else 400, P["noche"] if i == sow else SEC, anchor="middle"))
    sx = sow * w / n + w / n / 2
    out += [poly([(sx - 7, h + 30), (sx + 7, h + 30), (sx, h + 24)], D["brote"]), text(sx, h + 46, "siembra", 12, 700, D["oliva"], anchor="middle")]
    return [group("grafica-heladas", out, x, y)]


def ph_scale(x, y, w, label="Suelo estimado de Samacá: 5,2 a 5,8"):
    """Escala de pH con el rango del cultivo y el intervalo estimado del suelo. `label` dice de quién es el suelo:
    el estimado del municipio (sin cuenta) o el del lote; siempre es una estimación de 250 m (R10)."""
    narrow = w < 400
    lo, hi = 4.0, 8.0
    X = lambda v: (v - lo) / (hi - lo) * w  # noqa: E731
    out = [text(0, -14, "pH del suelo, de 0 a 30 cm", 14, 700, SEC)]
    out.append(poly(chamfer(0, 0, w, 28, 6), P["niebla"]))
    out.append(f'<rect x="{X(4.8):.1f}" y="0" width="{X(7.0) - X(4.8):.1f}" height="28" fill="{P["trigo"]}" fill-opacity="0.55"/>')
    out.append(f'<rect x="{X(5.0):.1f}" y="0" width="{X(6.5) - X(5.0):.1f}" height="28" fill="{P["brote"]}"/>')
    for v in (4, 5, 6, 7, 8):
        out.append(text(X(v), 50, f"{v}", 12, fill=SEC, anchor="middle"))
    a, b = X(5.2), X(5.8)
    out += [f'<path d="M{a:.1f} -6 V34 M{b:.1f} -6 V34 M{a:.1f} 34 H{b:.1f}" stroke="{P["noche"]}" stroke-width="3" fill="none"/>',
            poly([(X(5.5), -2), (X(5.5) + 8, 8), (X(5.5), 18), (X(5.5) - 8, 8)], P["noche"])]
    out += [text(max(X(5.5), 130), 74, label, 14, 700, anchor="middle")]
    lx, ly = (0, 118) if narrow else (w / 2, 92)
    out += [poly(chamfer(0, 92, 16, 16, 3), P["brote"]), text(24, 105, "Óptimo para la papa", 13),
            poly(chamfer(lx, ly, 16, 16, 3), P["trigo"]), text(lx + 24, ly + 13, "Lo tolera", 13)]
    return [group("escala-ph", out, x, y)]
