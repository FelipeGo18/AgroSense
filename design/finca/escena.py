"""Escena del lote vivo por capas: hora del día + clima de ahora + suelo, con los cuadros de su animación (tanda 6).

Capas: hora (día, amanecer o atardecer, noche) · condición (nublado, lluvia, viento, escarcha; se pueden sumar) ·
suelo (normal, mojado, seco por «riego probable»). La animación: el viento pasa en ráfagas, la lluvia cae, las nubes
derivan, las estrellas titilan, la escarcha se derrite al salir el sol y de vez en cuando cruza una mariposa.
En modo ligero o con movimiento reducido, la escena es la imagen fija del estado de ahora.

    python design/finca/escena.py     # escribe svg/ambiente-combinaciones.svg y svg/ambiente-animacion.svg
"""

import math
import random
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))
sys.path.insert(0, str(DIR.parent / "kit"))

import ambiente as am  # noqa: E402
import cultivos as cv  # noqa: E402
from build_kit_svg import BORDE, D, P, WHITE, chamfer, poly, shade, svg  # noqa: E402
from sheet import FONT_TITLE, SEC, ridges, text  # noqa: E402

CROP = next(c for c in cv.CROPS if c[0] == "maiz")


# ---------- Cielo según hora y condición ----------

def sky_colors(time, conds):
    if "lluvia" in conds:
        return {"dia": ("#5E6B78", "#8E9AA4"), "atardecer": ("#4E4A6A", "#A8786A"), "noche": ("#0B1020", "#26303F")}[time]
    if "nublado" in conds:
        return {"dia": ("#8D9AA6", "#C9D2D8"), "atardecer": ("#6A6280", "#D9A07A"), "noche": ("#121826", "#2A3446")}[time]
    if "escarcha" in conds and time == "noche":
        return am.SKIES["escarcha"]
    return {"dia": am.SKIES["dia"], "atardecer": am.SKIES["atardecer"], "noche": am.SKIES["noche"]}[time]


# ---------- Mariposa ----------

def butterfly(x, y, wing=1.0, scale=1.0, color="#F2C232", edge="#3A2A1E"):
    """Mariposa low-poly vista desde arriba. `wing` de 1 (alas abiertas) a 0.15 (cerradas)."""
    k = scale
    out = [f'<g transform="translate({x:g} {y:g}) scale({k:g})">']
    for d in (-1, 1):
        fw = 9 * wing
        out.append(poly([(0, -1), (d * fw, -8), (d * fw * 1.15, -2), (d * fw * 0.5, 1)], color, edge, 1))
        out.append(poly([(0, 1), (d * fw * 0.8, 3), (d * fw * 0.6, 8), (d * 1.5, 5)], shade(color, -0.12), edge, 1))
        out.append(f'<circle cx="{d * fw * 0.7:.1f}" cy="-4" r="{1.1 * max(wing, 0.3):.1f}" fill="{edge}"/>')
    out.append(f'<rect x="-0.8" y="-6" width="1.6" height="13" rx="0.8" fill="{edge}"/>')
    out.append(f'<path d="M-0.5 -6 q-2 -4 -3 -5 M0.5 -6 q2 -4 3 -5" stroke="{edge}" stroke-width="0.6" fill="none"/>')
    out.append("</g>")
    return out


# ---------- Lote ----------

def lote(cx, cy, scale, soil="normal", wind=None, frost=0.0):
    """El lote de maíz. `wind(x)` da la inclinación en grados según la posición; `frost` de 0 a 1."""
    _, _, _, _, plant, rows, cols, ridged, _, *_ = CROP
    top = {"mojado": "#4A2A18", "seco": "#9A6A40"}.get(soil)
    if frost:
        top = top or "#6B5048"
    out = cv.block(0, 0, rows, ridged=ridged, top=top)
    if soil == "seco":
        rnd = random.Random(4)
        for _ in range(14):
            x, y = cv.at(0, 0, rnd.random(), rnd.random())
            out.append(f'<path d="M{x:.1f} {y:.1f} l4 2 l-2 3 l5 2" stroke="#6B4528" stroke-width="1" fill="none"/>')
    if soil == "mojado":
        for u, v, r in ((0.3, 0.7, 9), (0.7, 0.35, 7), (0.55, 0.85, 6)):
            x, y = cv.at(0, 0, u, v)
            out.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{r}" ry="{r * 0.45}" fill="#8EB4D0" fill-opacity="0.7"/>')
    if frost:
        corners = [cv.at(0, 0, 0, 0), cv.at(0, 0, 1, 0), cv.at(0, 0, 1, 1), cv.at(0, 0, 0, 1)]
        out.append(poly(corners, "#E8F0FF").replace('fill="#E8F0FF"', f'fill="#E8F0FF" fill-opacity="{0.45 * frost:.2f}"'))

    def plant_state(x, y, s, sd):
        body = "".join(plant(x, y, s, sd))
        skew = wind(x) if wind else 0
        if soil == "seco":
            return [f'<g transform="translate({x:g} {y:g}) skewX({skew:.1f}) scale(1 0.9) translate({-x:g} {-y:g})" opacity="0.92">{body}</g>']
        if skew:
            return [f'<g transform="translate({x:g} {y:g}) skewX({skew:.1f}) translate({-x:g} {-y:g})">{body}</g>']
        return [body]

    out += cv.field(0, 0, rows, cols, plant_state, am.STAGE, seed=sum(map(ord, "maiz")))
    if frost:
        rnd = random.Random(9)
        for _ in range(int(140 * frost)):
            x, y = cv.at(0, 0, rnd.random(), rnd.random())
            out.append(f'<circle cx="{x:.1f}" cy="{y - rnd.uniform(0, 70):.1f}" r="{rnd.choice((0.7, 1.0, 1.3))}" fill="#FFFFFF" fill-opacity="{rnd.uniform(0.6, 1):.2f}"/>')
    return [f'<g id="lote" transform="translate({cx:g} {cy:g}) scale({scale:g})">{"".join(out)}</g>']


# ---------- Escena por capas ----------

def scene(w, h, time, conds=(), soil="normal", chips=(), gust_x=None, rain_phase=0.0, frost=None, sun_y=None, butterflies=(), seed=1):
    conds = set(conds)
    rnd = random.Random(seed)
    top, bottom = sky_colors(time, conds)
    gid = f"cielo-{time}-{'-'.join(sorted(conds)) or 'despejado'}-{seed}"
    b = [f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient></defs>',
         f'<rect width="{w}" height="{h}" fill="url(#{gid})"/>']
    k = w / am.W
    covered = conds & {"nublado", "lluvia"}
    if time == "noche" and not covered:
        b += [s.replace('cx="', 'cx="') for s in am.stars(rnd, int(70 * k))] + am.moon(int(w * 0.77), int(70 * k))
    elif time == "atardecer" and "lluvia" not in conds:
        b += am.sun(int(w * 0.75), sun_y or int(h * 0.45), 22 * k, "#F28C4A", "#F7C08A")
    elif time == "dia" and not covered:
        b += am.sun(int(w * 0.8), sun_y or int(66 * k), 18 * k)
    if covered:
        col = "#E3E8EB" if "lluvia" not in conds else ("#7E8A96" if time != "noche" else "#3A4454")
        for x, y, r, sd in ((0.2, 70, 30, 1), (0.57, 50, 36, 2), (0.86, 95, 28, 3), (0.39, 120, 24, 4)):
            b += am.cloud(w * x, y * k, r * k, col, sd)
    elif time != "noche":
        for x, y, r, sd in ((0.2, 80, 18, 5), (0.5, 120, 14, 6)):
            b += am.cloud(w * x + (30 * k if "viento" in conds else 0), y * k, r * k, "#FFFFFF" if time == "dia" else "#F2C9A8", sd)
    hy = h * 0.447
    b.append(f'<g transform="translate(0 {hy:.0f})" opacity="{0.55 if time == "noche" else 0.9}">{"".join(ridges(w, 0, 90 * k))}</g>')
    f = frost if frost is not None else (1.0 if "escarcha" in conds else 0.0)
    grass = "#9DB6A8" if f > 0.6 else ("#8FAF7A" if f > 0 else shade(cv.GRASS, -0.15))
    b.append(f'<rect y="{hy + 90 * k:.0f}" width="{w}" height="{h}" fill="{grass}"/>')

    if gust_x is not None:  # la ráfaga dobla las matas a su paso, en ola
        def wind(x):
            return -18 * max(0.0, 1 - abs(x * 1.55 * k + w / 2 - gust_x) / (70 * k))
    elif "viento" in conds:
        def wind(x):
            return -16
    else:
        wind = None
    b += lote(w / 2, h * 0.617, 1.55 * k, soil, wind, f)

    if "lluvia" in conds:
        slant = -14 if "viento" in conds else -6
        rr = random.Random(seed + 7)
        for _ in range(int(90 * k * k + 20)):
            x, y = rr.uniform(-10, w + 10), rr.uniform(60 * k, h - 40)
            y = 60 * k + ((y - 60 * k + rain_phase * 40) % (h - 100 * k))
            b.append(f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x + slant * k:.0f}" y2="{y + 14 * k:.0f}" stroke="#DCE8F2" stroke-width="1.3" stroke-opacity="0.75" stroke-linecap="round"/>')
        if rain_phase:  # salpicaduras donde caen gotas
            for _ in range(6):
                x, y = rr.uniform(w * 0.25, w * 0.75), rr.uniform(h * 0.6, h * 0.82)
                b.append(f'<path d="M{x - 4:.0f} {y:.0f} q4 -5 8 0" stroke="#DCE8F2" stroke-width="1.2" fill="none"/>')
    if "viento" in conds and gust_x is None:
        b += am.wind_streaks(random.Random(seed + 3)) if k == 1 else []
    if gust_x is not None:
        for dy in (-20, 0, 18):
            b.append(f'<path d="M{gust_x - 70 * k:.0f} {h * 0.42 + dy * k:.0f} q{50 * k:.0f} -8 {100 * k:.0f} 0 t{30 * k:.0f} 6" stroke="#FFFFFF" stroke-width="2" stroke-opacity="0.8" fill="none" stroke-linecap="round"/>')
        for i in range(3):
            b += cv.leaf(gust_x + 20 * k + i * 12 * k, h * 0.4 + i * 10 * k, 30 + i * 50, 7 * k, 4 * k, ("#6FA03C", "#9CC152", "#C9A86A")[i])
    for bx, by, wing in butterflies:
        b += butterfly(bx, by, wing, 2.0 * k)
    if time == "noche":
        b += am.tint("#0B1A3A", 0.28).copy() if k == 1 else [f'<rect width="{w}" height="{h}" fill="#0B1A3A" fill-opacity="0.28"/>']
    if time == "atardecer":
        b.append(f'<rect width="{w}" height="{h}" fill="#F28C4A" fill-opacity="0.1"/>')
    if f:
        b.append(f'<rect width="{w}" height="{h}" fill="#BFD8FF" fill-opacity="{0.08 * f:.2f}"/>')
    cy0 = h - 46
    for i, (label, kind) in enumerate(chips):
        if kind == "riego":
            b += am.chip(16, cy0 - i * 38, label, WHITE, P["noche"], BORDE, None, "gota")
        elif kind == "neutro":
            b += am.chip(16, cy0 - i * 38, label, WHITE, P["noche"], D["cielo"], "4 3")
        else:
            b += am.chip(16, cy0 - i * 38, label, WHITE, P["noche"])
    return b


def framed(body, w, h, cid):
    return (f'<defs><clipPath id="{cid}"><path d="M14 0 H{w - 14} L{w} 14 V{h - 14} L{w - 14} {h} H14 L0 {h - 14} V14 Z"/></clipPath></defs>'
            f'<g clip-path="url(#{cid})">{"".join(body)}</g>' + poly(chamfer(0, 0, w, h, 14), "none", BORDE, 2))


def caption(x, y, title, rule, width_chars=58, size=22):
    out = [text(x, y, title, size, 600, font=FONT_TITLE)]
    words, line, lines = rule.split(" "), "", []
    for wd in words:
        if len(line) + len(wd) > width_chars:
            lines.append(line.strip())
            line = ""
        line += wd + " "
    lines.append(line.strip())
    out += [text(x, y + 26 + i * 20, ln, 14, fill=SEC) for i, ln in enumerate(lines)]
    return out


# ---------- Lámina de combinaciones ----------

COMBOS = (
    ("noche-lluvia", "Noche con lluvia", "noche", ("lluvia",), "mojado", [("Ahora en Samacá: lloviendo de noche", "vivo")],
     "La hora pone la noche y la condición, la lluvia: sin estrellas, nubes oscuras y el suelo mojado"),
    ("aguacero-viento", "Aguacero con viento", "dia", ("lluvia", "viento"), "mojado", [("Ahora en Samacá: aguacero con viento", "vivo")],
     "Lluvia y viento a la vez: las gotas caen inclinadas y las matas se doblan"),
    ("amanecer-escarcha", "Escarcha al amanecer", "atardecer", ("escarcha",), "normal", [("Ahora en Samacá: escarcha · 0 °C", "vivo")],
     "La helada típica del altiplano: cielo de amanecer y hielo que empieza a derretirse con el sol"),
    ("atardecer-nublado", "Atardecer nublado", "atardecer", ("nublado",), "normal", [("Ahora en Samacá: nublado", "vivo")],
     "Las nubes tapan el sol bajo; queda el tono cálido del atardecer"),
    ("noche-viento", "Noche con viento", "noche", ("viento",), "normal", [("Ahora en Samacá: viento de noche", "vivo")],
     "Estrellas y luna, con las matas inclinadas por el viento"),
    ("noche-nublada", "Noche nublada", "noche", ("nublado",), "normal", [("Ahora en Samacá: noche nublada", "vivo")],
     "Sin luna ni estrellas: nubes oscuras y la escena más fría"),
    ("nublado-riego", "Nublado y riego probable", "dia", ("nublado",), "seco", [("Riego probable este mes · estimación", "riego"), ("Ahora en Samacá: nublado", "vivo")],
     "El clima de ahora y la estimación de riego son capas distintas: puede estar nublado y el mes ser seco"),
    ("lluvia-riego", "Llueve hoy, pero el mes es seco", "dia", ("lluvia",), "mojado", [("Riego probable este mes · estimación", "riego"), ("Ahora en Samacá: lloviendo", "vivo")],
     "Caso borde: el suelo se ve mojado por la lluvia de ahora, pero el plan de agua sigue marcando déficit del mes. Se muestran los dos rótulos, sin contradecirse"),
    ("noche-sin-datos", "Noche sin datos en vivo", "noche", (), "normal", [("Sin condición en vivo · clima neutro", "neutro")],
     "De noche la hora sí se sabe (se calcula en el navegador); solo falta el clima: noche sin nubes ni lluvia, rotulada"),
)


def combinations_sheet():
    W, H = am.W, am.H
    cols, gap_x, gap_y = 3, 60, 170
    rows = math.ceil(len(COMBOS) / cols)
    wsheet, hsheet = 60 * 2 + cols * W + (cols - 1) * gap_x, 210 + rows * (H + gap_y)
    b = [f'<rect width="{wsheet}" height="{hsheet}" fill="{P["niebla"]}"/>', text(60, 80, "Combinaciones del ambiente", 40, 600, font=FONT_TITLE),
         text(60, 118, "Las capas se suman: hora del día + clima de ahora + suelo. Una sola escena, sin ventanas aparte. El clima de ahora nunca cambia un resultado (decisión 7).", 16, fill=SEC),
         text(60, 142, "Si el clima no llega, la hora sigue: el día y la noche se calculan en el navegador con la posición del municipio.", 16, fill=SEC)]
    for i, (key, title, time, conds, soil, chips, rule) in enumerate(COMBOS):
        x, y = 60 + (i % cols) * (W + gap_x), 190 + (i // cols) * (H + gap_y)
        body = scene(W, H, time, conds, soil, chips, frost=0.55 if key == "amanecer-escarcha" else None, sun_y=int(H * 0.38) if key == "amanecer-escarcha" else None, seed=i + 11)
        b.append(f'<g id="combinacion-{key}" transform="translate({x} {y})">{framed(body, W, H, "rc-" + key)}{"".join(caption(0, H + 34, title, rule))}</g>')
    return svg(wsheet, hsheet, b)


# ---------- Lámina del guion de animación ----------

FW, FH = 330, 290  # cuadro de animación

SEQUENCES = (
    ("rafaga", "Viento: la ráfaga pasa", "Cada 4 a 8 s (según la velocidad del viento) una ráfaga cruza de izquierda a derecha; las matas se doblan en ola a su paso y vuelven; algunas hojas viajan con ella.",
     [dict(time="dia", conds=("viento",), gust_x=x) for x in (60, 165, 270)], ("0 s", "0,6 s", "1,2 s")),
    ("lluvia", "Lluvia: cae y salpica", "Las gotas caen en bucle continuo (más rápidas si llueve más) y salpican al tocar la tierra; tras unos segundos de lluvia aparecen los charcos.",
     [dict(time="dia", conds=("lluvia",), soil="mojado", rain_phase=p) for p in (0.0, 0.33, 0.66)], ("bucle · 0", "1/3", "2/3")),
    ("mariposa", "Mariposa ocasional", "De día, sin lluvia ni viento fuerte, cada 20 a 40 s una mariposa cruza el lote en vuelo ondulado (6 a 8 s) y, si el cultivo está en floración, se posa un instante.",
     [dict(time="dia", butterflies=((x, y, wg),)) for x, y, wg in ((40, 110, 1.0), (130, 70, 0.45), (178, 112, 0.15))], ("entra", "aletea en ondas", "se posa (alas cerradas)")),
    ("escarcha", "Escarcha: se derrite al salir el sol", "Con la helada, los cristales titilan; al salir el sol la escarcha se derrite en unos segundos (se desvanece) y la escena pasa al día.",
     [dict(time="atardecer", conds=("escarcha",), frost=1.0, sun_y=int(FH * 0.6)),
      dict(time="atardecer", conds=("escarcha",), frost=0.5, sun_y=int(FH * 0.36)),
      dict(time="dia", frost=0.0, sun_y=int(FH * 0.2))], ("madrugada", "sale el sol", "deshielo, ya de día")),
)

TIMELINE = (
    ("Viento", "Ráfaga que cruza y ola en las matas", "4–8 s entre ráfagas", "Viento > 25 km/h", "Matas inclinadas, sin ráfaga"),
    ("Lluvia", "Gotas en bucle, salpicaduras, charcos", "Continuo", "Lluvia > 0,2 mm", "Gotas quietas y suelo mojado"),
    ("Nubes", "Derivan despacio", "60–90 s para cruzar", "Siempre que hay nubes", "Quietas"),
    ("Estrellas", "Titilan", "2–4 s, al azar", "Noche despejada", "Quietas"),
    ("Escarcha", "Cristales que titilan; deshielo al salir el sol", "Deshielo de 3 s", "Mínima < 2 °C", "Capa de hielo quieta"),
    ("Mariposa", "Cruza en vuelo ondulado y se posa", "Cada 20–40 s, vuelo de 6–8 s", "Día, sin lluvia ni viento fuerte", "No aparece"),
    ("Sol y luna", "Su posición sigue la hora real", "Tiempo real", "Siempre", "Posición de ahora"),
    ("Riego probable", "El rótulo aparece con un fundido", "0,4 s", "Déficit del mes (R10)", "Rótulo fijo"),
)


def animation_sheet():
    w = 60 * 2 + 3 * FW + 2 * 24 + 380
    row_h = FH + 90
    h = 200 + len(SEQUENCES) * row_h + 120 + len(TIMELINE) * 40 + 80
    b = [f'<rect width="{w}" height="{h}" fill="{P["niebla"]}"/>', text(60, 80, "Guion de animación del ambiente", 40, 600, font=FONT_TITLE),
         text(60, 118, "Lo que se mueve en el lote vivo y cuándo. Hecho con GSAP en 2D y con React Three Fiber en 3D; se pausa cuando la pestaña no se ve.", 16, fill=SEC),
         text(60, 142, "Modo ligero y movimiento reducido: escena estática, la imagen fija del estado de ahora, con los mismos rótulos.", 16, 700)]
    for r, (key, title, rule, frames, labels) in enumerate(SEQUENCES):
        y = 190 + r * row_h
        for i, params in enumerate(frames):
            x = 60 + i * (FW + 24)
            body = scene(FW, FH, seed=r * 10 + i, **params)
            b.append(f'<g id="anim-{key}-{i + 1}" transform="translate({x} {y})">{framed(body, FW, FH, f"ra-{key}-{i}")}'
                     f'{text(FW / 2, FH + 26, labels[i], 14, 700, anchor="middle")}</g>')
            if i < 2:
                ax = x + FW + 4
                b.append(poly([(ax, y + FH / 2 - 7), (ax + 14, y + FH / 2), (ax, y + FH / 2 + 7)], P["noche"]))
        b += caption(60 + 3 * (FW + 24) + 10, y + 40, title, rule, 40, 20)
        if key == "mariposa":  # la mariposa en grande, con sus tres poses
            for j, wing in enumerate((1.0, 0.55, 0.15)):
                b += butterfly(60 + 3 * (FW + 24) + 50 + j * 90, y + 210, wing, 3.2)
    ty = 190 + len(SEQUENCES) * row_h + 30
    b.append(text(60, ty, "Tiempos y versión estática", 28, 600, font=FONT_TITLE))
    cols = (60, 260, 720, 960, 1260)
    for x, hd in zip(cols, ("Elemento", "Qué se mueve", "Ritmo", "Cuándo aparece", "Modo ligero y movimiento reducido")):
        b.append(text(x, ty + 44, hd, 14, 700, SEC))
    for i, row in enumerate(TIMELINE):
        yy = ty + 64 + i * 40
        b.append(poly(chamfer(48, yy - 8, w - 96, 34, 8), WHITE, BORDE, 1))
        for x, cell in zip(cols, row):
            b.append(text(x, yy + 14, cell, 14, 700 if x == 60 else 400))
    b += [text(60, h - 60, "Rendimiento: en móvil, máximo 120 gotas y 30 cuadros por segundo; las partículas se crean una vez y se reciclan.", 14, fill=SEC)]
    return svg(w, h, b)


if __name__ == "__main__":
    out = DIR / "svg"
    (out / "ambiente-combinaciones.svg").write_text(combinations_sheet(), encoding="utf-8", newline="\n")
    (out / "ambiente-animacion.svg").write_text(animation_sheet(), encoding="utf-8", newline="\n")
    print("ok")
