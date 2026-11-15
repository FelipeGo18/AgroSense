"""Pantalla final «Dibujar mi lote en el mapa» (tanda 2, HU-164). Escritorio y móvil, con sus estados.

Pregunta «¿Este lote tiene riego?» (`irrigated`) con «Sí», «No» y «Todavía no sé» (rediseño, tanda 4).

El mapa es real: MapLibre GL JS con la base de OpenStreetMap (OpenFreeMap) y el dibujo con Terra Draw.
Aquí se simula con un mapa plano de parcelas, vías y río; el panel y los controles siguen el kit diorama.
El polígono es el que el agricultor verá después en Mi finca. Los nombres y las cifras son de muestra.

    python design/pantallas/lote.py     # escribe svg/descenso-02-dibujar-lote-*.svg
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401  (agrega design/kit y design/mascota al camino de importación)
from inicio import stepper  # noqa: E402
from ui import (BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, field, frame, group, link,  # noqa: E402
                mascot, paragraph, poly, pts, text, topbar)

# Colores del mapa base (estilo OpenStreetMap, aplanado para que el dibujo mande).
LAND, FIELDS = "#EEF0E4", ("#DDE8C6", "#E7EACB", "#D3E2B7", "#EEE5C7", "#E1ECD1", "#E9E2C2")
WATER, ROAD, ROAD_CASE, MAIN, MAIN_CASE, TOWN = "#AFCDE6", "#FFFFFF", "#C9CCC0", "#F7D894", "#D6B163", "#DAD6CF"
LOT, LOT_INK = P["calabaza"], D["calabaza"]
M_PER_PX = 1.1  # escala del mundo simulado: un píxel del mundo son 1,1 m

# Lote de muestra en coordenadas del mundo: cerrado (dentro de Samacá) y mal ubicado (se sale del límite).
LOT_OK = [(842, 498), (968, 482), (1004, 590), (936, 652), (850, 628)]
LOT_OUT = [(318, 520), (452, 506), (470, 616), (402, 668), (296, 640)]
LOT_DRAWING = LOT_OK[:3]
BOUNDARY = [(380, -20), (360, 200), (400, 420), (372, 640), (410, 860), (390, 1220)]


def area_ha(points):
    s = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]))
    return abs(s) / 2 * M_PER_PX**2 / 10_000


def fmt_ha(v):
    return f"{v:.2f}".replace(".", ",") + " ha"


def fmt_m2(v):
    return f"{round(v * 10_000 / 100) * 100:,}".replace(",", ".") + " m²"


# ---------- Mapa base ----------

def world():
    """Un pedazo de campo alrededor del casco urbano: parcelas, río, vías y el límite municipal (DANE)."""
    rnd = random.Random(7)
    cols, rows, cw, rh = 18, 13, 108, 100
    out = [f'<rect x="-900" y="-600" width="3400" height="2400" fill="{LAND}"/>']
    grid = [[(c * cw + rnd.uniform(-22, 22), r * rh + rnd.uniform(-20, 20)) for c in range(-6, cols + 1)] for r in range(-2, rows + 3)]
    for r in range(len(grid) - 1):
        for c in range(len(grid[0]) - 1):
            if 18 <= c and 2 <= r <= 5:
                continue  # casco urbano
            q = [grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]]
            out.append(poly(q, rnd.choice(FIELDS), WHITE, 2.5))
    # Casco urbano: manzanas.
    for i in range(6):
        for j in range(4):
            out.append(poly(chamfer(1320 + i * 72, 30 + j * 72, 58, 58, 0), TOWN, "#C4BFB6", 1.5))
    # Río y quebrada.
    river = "M -40 300 C 200 340, 360 260, 560 380 S 860 440, 1080 380 S 1500 470, 1900 420"
    out.append(f'<path d="{river}" fill="none" stroke="{WATER}" stroke-width="16" stroke-linecap="round"/>')
    out.append(f'<path d="M 700 1240 C 720 1000, 640 860, 700 720 S 760 520, 720 410" fill="none" stroke="{WATER}" stroke-width="6" stroke-linecap="round"/>')
    # Vías: la principal hacia el pueblo y dos destapadas.
    def road(d, w, fill, case, dash=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        return [f'<path d="{d}" fill="none" stroke="{case}" stroke-width="{w + 4}" stroke-linecap="round"/>',
                f'<path d="{d}" fill="none" stroke="{fill}" stroke-width="{w}" stroke-linecap="round"{extra}/>']
    out += road("M -40 760 C 300 700, 600 720, 820 700 S 1180 420, 1360 200 S 1600 120, 1900 140", 10, MAIN, MAIN_CASE)
    out += road("M 560 -40 C 600 200, 520 460, 600 720 S 560 1000, 620 1240", 6, ROAD, ROAD_CASE)
    out += road("M 820 700 C 1000 760, 1160 900, 1400 960 S 1700 1000, 1900 1060", 6, ROAD, ROAD_CASE)
    out.append('<path d="M 1060 380 C 1080 520, 1040 620, 1100 760" fill="none" stroke="#BFA77A" stroke-width="3" stroke-dasharray="8 6"/>')
    # Límite municipal del DANE.
    b = " ".join(f"{x},{y}" for x, y in BOUNDARY)
    out.append(f'<polyline points="{b}" fill="none" stroke="{WHITE}" stroke-width="9" stroke-linejoin="round" opacity="0.8"/>')
    out.append(f'<polyline points="{b}" fill="none" stroke="#6B4E8C" stroke-width="3.5" stroke-dasharray="14 7" stroke-linejoin="round"/>')
    # Rótulos del mapa (de muestra).
    label = 'font-family="Atkinson Hyperlegible" paint-order="stroke" stroke="#FFFFFF" stroke-width="4"'
    out.append(f'<text x="1480" y="200" {label} font-size="26" font-weight="700" fill="#4A4A48" text-anchor="middle">Samacá</text>')
    out.append(f'<text {label} font-size="15" font-style="italic" fill="#3F73A5" transform="translate(1180 418) rotate(-6)">Río Teatinos</text>')
    out.append(f'<text {label} font-size="14" fill="#6B5A2E" transform="translate(1010 560) rotate(-48)">Vía a Tunja</text>')
    out.append(f'<text {label} font-size="13" font-weight="700" fill="#6B4E8C" transform="translate(404 800) rotate(-82)">Límite de Samacá (DANE)</text>')
    out.append(f'<text {label} font-size="13" fill="#6B4E8C" transform="translate(366 800) rotate(-82)">Fuera del municipio</text>')
    return out


def lot_shape(points, closed=True, error_from=None, cursor=None, s=1.0):
    """El dibujo de Terra Draw con el estilo del kit: puntos en rombo, como la semilla del selector.

    `s` deshace la escala del mapa para que los puntos y los trazos se vean del mismo tamaño en todo zoom."""
    ink = D["rojo"] if error_from is not None else LOT_INK
    out = []
    if closed:  # el lote se lee como un solo terreno: tapa las lindes de las parcelas de abajo
        out.append(f'<polygon points="{pts(points)}" fill="{FIELDS[0]}"/>')
        out.append(f'<polygon points="{pts(points)}" fill="{D["rojo"] if error_from is not None else LOT}" fill-opacity="0.32" '
                   f'stroke="{ink}" stroke-width="{3.5 / s:g}" stroke-linejoin="round"/>')
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):  # puntos medios: arrastrarlos agrega una esquina
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            out.append(f'<circle cx="{mx:g}" cy="{my:g}" r="{5 / s:g}" fill="{WHITE}" stroke="{ink}" stroke-width="{2 / s:g}" opacity="0.85"/>')
    else:
        out.append(f'<polyline points="{pts(points)}" fill="none" stroke="{ink}" stroke-width="{3.5 / s:g}" stroke-linejoin="round"/>')
        if cursor:
            (lx, ly), (cx, cy) = points[-1], cursor
            out.append(f'<line x1="{lx}" y1="{ly}" x2="{cx}" y2="{cy}" stroke="{ink}" stroke-width="{2.5 / s:g}" stroke-dasharray="{8 / s:g} {6 / s:g}"/>')
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{22 / s:g}" fill="{LOT}" fill-opacity="0.25" stroke="{ink}" stroke-width="{2 / s:g}"/>')
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{6 / s:g}" fill="{ink}"/>')
    for i, (x, y) in enumerate(points):
        bad = error_from is not None and x < error_from
        r = (13 if i == 0 and not closed else 10) / s
        fill = D["rojo"] if bad else (P["calabaza"] if i == 0 and not closed else WHITE)
        out.append(poly([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], fill, P["noche"], 2.5 / s))
    return out


def area_chip(points, s, bad=False):
    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    label = fmt_ha(area_ha(points))
    w = (len(label) * 9 + 24) / s
    body = [poly(chamfer(-w / 2, -16 / s, w, 32 / s, 6 / s), D["rojo"] if bad else P["noche"]),
            f'<text x="0" y="{6 / s:g}" font-family="Atkinson Hyperlegible" font-weight="700" font-size="{16 / s:g}" fill="{WHITE}" text-anchor="middle">{label}</text>']
    return [f'<g transform="translate({cx:g} {cy:g})">{"".join(body)}</g>']


def map_view(w, h, center, zoom, extra, clip_id):
    """Ventana del mapa: el mundo centrado en `center` con `zoom` y lo dibujado encima."""
    ox, oy = w / 2 - center[0] * zoom, h / 2 - center[1] * zoom
    body = f'<g transform="translate({ox:g} {oy:g}) scale({zoom:g})">{"".join(world() + extra)}</g>'
    return [f'<defs><clipPath id="{clip_id}"><rect width="{w}" height="{h}"/></clipPath></defs><g id="mapa" clip-path="url(#{clip_id})">{body}</g>']


# ---------- Controles del mapa ----------

def tool_button(x, y, glyph, active=False, size=48, name="control"):
    body = [poly(chamfer(0, 5, size, size, 9), BORDE), poly(chamfer(0, 0, size, size, 9), P["noche"] if active else WHITE)]
    ink = WHITE if active else P["noche"]
    body += [g.replace("INK", ink) for g in glyph]
    return [group(name, body, x, y)]


G = {
    "mas": ['<path d="M24 14v20M14 24h20" stroke="INK" stroke-width="3.5" stroke-linecap="round"/>'],
    "menos": ['<path d="M14 24h20" stroke="INK" stroke-width="3.5" stroke-linecap="round"/>'],
    "dibujar": ['<path d="M12 34 L18 14 L36 18 L32 34 Z" fill="none" stroke="INK" stroke-width="2.5" stroke-linejoin="round"/>'
                '<path d="M12 30 l4 4 -4 4 -4 -4z M18 10 l4 4 -4 4 -4 -4z M36 14 l4 4 -4 4 -4 -4z" fill="INK"/>'],
    "mover": ['<path d="M24 10v28M10 24h28M24 10l-5 5M24 10l5 5M24 38l-5-5M24 38l5-5M10 24l5-5M10 24l5 5M38 24l-5-5M38 24l-5 5" '
              'stroke="INK" stroke-width="2.8" stroke-linecap="round" fill="none"/>'],
    "deshacer": ['<path d="M18 16 L11 23 L18 30" fill="none" stroke="INK" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
                 '<path d="M12 23 H28 a8 8 0 0 1 0 16 H20" fill="none" stroke="INK" stroke-width="3" stroke-linecap="round"/>'],
    "borrar": ['<path d="M15 17h18M20 17v-4h8v4M17 17l2 20h10l2-20" fill="none" stroke="INK" stroke-width="2.8" stroke-linejoin="round" stroke-linecap="round"/>'],
}


def zoom_controls(x, y):
    """Acercar y alejar. No hay «mi ubicación»: ninguna spec pide geolocalización (ningún control sin función)."""
    return [group("controles-mapa", tool_button(0, 0, G["mas"], name="acercar") + tool_button(0, 58, G["menos"], name="alejar"), x, y)]


def draw_toolbar(x, y, mode, mobile=False):
    """Barra de dibujo (modos de Terra Draw) con el nombre de cada herramienta debajo."""
    tools = (("dibujar", "Dibujar"), ("mover", "Mover puntos"), ("deshacer", "Deshacer"), ("borrar", "Borrar"))
    step = 82 if mobile else 104
    w = step * len(tools) + 16
    body = [poly(chamfer(0, 7, w, 92, 14), BORDE), poly(chamfer(0, 0, w, 92, 14), WHITE)]
    for i, (key, label) in enumerate(tools):
        bx = 8 + i * step + (step - 48) / 2
        body += tool_button(bx, 8, G[key], key == mode, name=f"herramienta-{key}")
        body.append(text(bx + 24, 80, label, 13, 700 if key == mode else 400, anchor="middle"))
    return [group("barra-de-dibujo", body, x, y)], w


def attribution(x, y, anchor="end"):
    label = "© OpenStreetMap · OpenFreeMap · MapLibre"
    w = len(label) * 6.4 + 16
    x0 = x - w if anchor == "end" else x
    return [group("atribucion", [f'<rect x="0" y="0" width="{w:g}" height="22" fill="{WHITE}" fill-opacity="0.85"/>', text(8, 15, label, 12, fill="#4A4A48")], x0, y)]


def scale_bar(x, y, zoom, meters=100):
    px = meters / M_PER_PX * zoom
    body = [f'<rect x="0" y="0" width="{px + 16:g}" height="30" fill="{WHITE}" fill-opacity="0.85"/>',
            f'<path d="M8 10v10h{px:g}v-10" fill="none" stroke="{P["noche"]}" stroke-width="2.5"/>', text(8 + px / 2, 16, f"{meters} m", 12, 700, anchor="middle")]
    return [group("escala", body, x, y)]


def choice(x, y, w, left, right, on_left=True):
    return options(x, y, w, (left, right), 0 if on_left else 1)


def options(x, y, w, labels, on, size=18):
    """Botones de una sola elección, del mismo ancho; `on` es el índice elegido."""
    n = len(labels)
    bw = (w - 12 * (n - 1)) / n
    out = []
    for i, label in enumerate(labels):
        bx = x + i * (bw + 12)
        sel = i == on
        out += [poly(chamfer(bx, y, bw, 48, 10), D["oliva"] if sel else WHITE, None if sel else BORDE, 0 if sel else 2.5),
                text(bx + bw / 2, y + 31, label, size, 700, WHITE if sel else P["noche"], anchor="middle")]
    return [group("eleccion", out)]


IRRIGATION = ("Sí", "No", "Todavía no sé")
SOWN_ON = "2 de agosto de 2026"  # la papa de El Alto; el mismo formato en escritorio y en móvil
# HU-164: sin dibujo, el área se escribe. El enlace cambia el panel al campo «Área (ha)» y guarda el lote sin polígono
# (pantalla pendiente de diseño: «Lote sin dibujar», mapa.py).
NO_DRAWING = "Escribir el área a mano"


def irrigation_question(x, y, w, on=1, compact=False):
    """«¿Este lote tiene riego?» (`irrigated`: verdadero, falso o nulo). Devuelve las piezas y el alto."""
    out = [text(0, 0, "¿Este lote tiene riego?", 18, 700)]
    out += options(0, 16, w, IRRIGATION, on, 16)
    rows = (["Con riego, la falta de lluvia no se cuenta como", "riesgo; le mostramos una estimación, en rangos,", "de cuánto riego haría falta. Puede cambiarlo", "después."] if compact else
            ["Con riego, la falta de lluvia no se cuenta como riesgo;", "le mostramos una estimación, en rangos, de cuánto", "riego haría falta. Puede cambiarlo después."])
    out += paragraph(0, 88, rows, 14, 20, fill=SEC)
    return [group("pregunta-riego", out, x, y)], 88 + 20 * len(rows)


def steps_list(x, y, done, rows):
    out = []
    for i, row in enumerate(rows):
        ry = y + i * 30
        ok = i < done
        out.append(poly([(x + 10, ry - 16), (x + 20, ry - 6), (x + 10, ry + 4), (x, ry - 6)], D["brote"] if ok else WHITE, D["oliva"] if ok else P["cielo"], 2))
        out.append(text(x + 32, ry, row, 16, 400, P["noche"] if ok or i == done else SEC))
    return [group("pasos", out)]


def area_box(x, y, w, points):
    ha = area_ha(points)
    body = [poly(chamfer(0, 0, w, 82, 12), "#FFF1DF", LOT, 2.5),
            text(20, 30, "Área calculada con su dibujo", 15, 700, LOT_INK),
            text(20, 66, fmt_ha(ha), 30, 600, font=FONT_TITLE),
            text(w - 20, 66, fmt_m2(ha), 16, fill=SEC, anchor="end")]
    return [group("area", body, x, y)]


def alert(x, y, w, rows, title):
    h = 44 + len(rows) * 22
    body = [poly(chamfer(0, 0, w, h, 12), "#FBE6E2", D["rojo"], 2.5), poly([(22, 14), (34, 36), (10, 36)], D["rojo"]),
            text(22, 32, "!", 15, 700, WHITE, anchor="middle"), text(46, 32, title, 16, 700, D["rojo"])]
    body += [text(20, 58 + i * 22, r, 15) for i, r in enumerate(rows)]
    return [group("alerta", body, x, y)], h


# ---------- Pantallas ----------

def desktop(error=False):
    w, h = DESKTOP[0], DESKTOP[1] + (314 if error else 264)
    zoom = 1.5
    shape = LOT_OUT if error else LOT_OK
    center = (sum(x for x, _ in shape) / 5 - 200 / zoom, sum(y for _, y in shape) / 5 + 30 / zoom)  # deja libre la columna del panel
    drawn = lot_shape(shape, error_from=BOUNDARY[3][0] + 12 if error else None, s=zoom) + area_chip(shape, zoom, error)
    b = map_view(w, h, center, zoom, drawn, "recorte-mapa" + ("-e" if error else ""))
    b += topbar(w, user="Rosa")
    b += stepper(500, 112, 520, 3)
    b += zoom_controls(w - 88, 116)  # sin selector de capa: la satelital no está decidida (regla: ningún control sin función)
    bar, bw = draw_toolbar(0, 0, "mover")
    b += [group("dibujo", bar, 470 + (w - 470 - bw) / 2, h - 132)]
    b += scale_bar(470, h - 44, zoom)
    b += attribution(w - 12, h - 30)

    x, y, cw, pad = 32, 112, 420, 30
    fw = cw - 2 * pad
    c = [text(pad, 48, "PASO 2 DE 2", 15, 700, SEC), text(pad, 92, "Dibuje su lote", 34, 600, font=FONT_TITLE)]
    c += steps_list(pad, 134, 3, ["Acerque el mapa hasta ver su lote.", "Toque cada esquina del lote.", "Toque el primer punto para cerrarlo."])
    top = 214
    if error:
        al, ah = alert(pad, top, fw, ["Mueva los puntos rojos dentro de la", "línea punteada morada."], "Su lote se sale de Samacá")
        c += al
        top += ah + 28
    else:
        c += area_box(pad, top, fw, shape)
        top += 112
    c += field(pad, top + 6, fw, "Nombre del lote", "El Alto", name="campo-nombre")
    rq, rh = irrigation_question(pad, top + 112, fw)
    c += rq
    top += rh + 26
    c.append(text(pad, top + 112, "¿Ya sembró algo en este lote?", 18, 700))
    c += [group("opciones", choice(pad, top + 128, fw, "Sí", "Todavía no"))]
    c += field(pad, top + 210, fw, "Cultivo", "Papa", trailing="▾", name="campo-cultivo")
    c += field(pad, top + 314, fw, "Sembrado el", SOWN_ON, trailing="▾", name="campo-fecha")
    c += button(pad, top + 404, fw, "Guardar lote", "disabled" if error else "primary")
    c += link(pad, top + 490, NO_DRAWING)
    ch = top + 514
    b += card(x, y, cw, ch) + [group("panel", c, x, y)]
    if not error:
        b += mascot(372, 96, 0.42, "guia")
    return frame((w, h), b)


def mobile_drawing():
    """Móvil, mientras dibuja: lleva tres puntos y el dedo está por poner el cuarto."""
    w, h = MOBILE
    zoom = 1.6
    cursor = (942, 650)
    center = (920, 624)
    drawn = lot_shape(LOT_DRAWING, closed=False, cursor=cursor, s=zoom)
    b = map_view(w, h, center, zoom, drawn, "recorte-mapa-m")
    b += topbar(w)
    b.append(group("buscador", [poly(chamfer(0, 5, 280, 48, 10), BORDE), poly(chamfer(0, 0, 280, 48, 10), WHITE),
                                poly([(22, 14), (30, 24), (22, 34), (14, 24)], D["brote"]), text(42, 31, "Samacá, Boyacá", 17, 700)], 12, 86))
    b += zoom_controls(w - 60, 86)
    b += attribution(w - 8, 474)
    sy = 500
    s = [poly(chamfer(0, 8, w, h - sy + 30, 20), BORDE), poly(chamfer(0, 0, w, h - sy + 30, 20), WHITE),
         poly(chamfer(w / 2 - 28, 10, 56, 6, 3), BORDE)]
    s += [text(22, 54, "PASO 2 DE 2", 14, 700, SEC), text(22, 88, "Toque las esquinas de su lote", 23, 600, font=FONT_TITLE)]
    s += paragraph(22, 118, ["Lleva 3 puntos. Para cerrarlo, toque el", "primer punto (el naranja)."], 16, 23)
    bar, bw = draw_toolbar(0, 0, "dibujar", mobile=True)
    s += [group("dibujo", bar, (w - bw) / 2, 160)]
    s += button(22, 278, w - 44, "Cerrar el lote")
    b += [group("hoja", s, 0, sy)]
    return frame((w, h), b)


def mobile_closed():
    """Móvil, lote cerrado: la hoja sube con el área y los datos del lote."""
    w = MOBILE[0]
    zoom = 1.2
    center = (sum(x for x, _ in LOT_OK) / 5, sum(y for _, y in LOT_OK) / 5 - 30)
    drawn = lot_shape(LOT_OK, s=zoom) + area_chip(LOT_OK, zoom)
    mh = 360
    b = map_view(w, mh + 40, center, zoom, drawn, "recorte-mapa-mc")
    b += topbar(w)
    b += [group("editar", tool_button(0, 0, G["mover"], True, name="mover-puntos"), w - 60, 86)]
    b += attribution(w - 8, mh - 4)
    pad, fw = 22, w - 44
    s = [poly(chamfer(0, 0, w, 1200, 20), WHITE), poly(chamfer(w / 2 - 28, 10, 56, 6, 3), BORDE)]
    s += [text(pad, 52, "PASO 2 DE 2", 14, 700, SEC), text(pad, 88, "Su lote en Samacá", 26, 600, font=FONT_TITLE)]
    s += area_box(pad, 110, fw, LOT_OK)
    s += link(pad, 232, "Ajustar los puntos", 16)
    s += field(pad, 280, fw, "Nombre del lote", "El Alto", name="campo-nombre")
    rq, rh = irrigation_question(pad, 384, fw, compact=True)
    s += rq
    d = rh + 30
    s.append(text(pad, 384 + d, "¿Ya sembró algo en este lote?", 18, 700))
    s += [group("opciones", choice(pad, 400 + d, fw, "Sí", "Todavía no"))]
    s += field(pad, 486 + d, fw, "Cultivo", "Papa", trailing="▾", name="campo-cultivo")
    s += field(pad, 590 + d, fw, "Sembrado el", SOWN_ON, trailing="▾", name="campo-fecha")
    s += paragraph(pad, 694 + d, ["Con la fecha estimamos la etapa del cultivo", "con la temperatura de la zona."], 15, 22, fill=SEC)
    s += button(pad, 742 + d, fw, "Guardar lote")
    s += link(pad, 836 + d, NO_DRAWING)
    h = mh + 870 + d
    b += [group("hoja", s, 0, mh)]
    return frame((w, h), b)


SCREENS = {
    "descenso-02-dibujar-lote-escritorio": lambda: desktop(),
    "descenso-02-dibujar-lote-error-escritorio": lambda: desktop(error=True),
    "descenso-02-dibujar-lote-movil": mobile_drawing,
    "descenso-02-dibujar-lote-cerrado-movil": mobile_closed,
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name, fmt_ha(area_ha(LOT_OK)))
