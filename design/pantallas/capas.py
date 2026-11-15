"""Tanda 11 · «Mapa del lote con capa de la NASA» (HU-211). Escritorio, móvil y el estado «la NASA no responde».

El mapa de Mi finca (finca.py) y el de dibujar el lote (lote.py) suman un control de capas con dos capas WMTS de
NASA GIBS que el agricultor prende y apaga: una imagen satelital de color real y el verdor (NDVI).

- Cada capa dice su producto, su fecha y su resolución, y la atribución que pide GIBS (R8).
- La imagen es de la fecha indicada, no de hoy; un día con nubes se ve con nubes y se dice.
- El verdor es de la zona, a la resolución del producto: cada cuadro de 250 m cubre unas 6 hectáreas, más que
  muchos lotes. No es una medición del lote (R10).
- La capa es solo para ver: no entra al motor ni cambia un resultado.
- Si GIBS no responde, el mapa sigue con OpenStreetMap y lo dice; ver, dibujar y editar el lote no dependen de ella.

Qué hace cada control: los interruptores prenden y apagan cada capa; «Ver de dónde sale» abre «¿Cómo funciona?» en
las fuentes; «Reintentar» vuelve a pedir la capa; «Cerrar» esconde el panel; el botón de capas lo abre.

Por confirmar antes de programar (docs/fuentes.md): el nombre exacto de cada capa de GIBS, su resolución, cada
cuánto se actualiza y sus condiciones de uso. Los productos y las fechas de aquí son de muestra.

    python design/pantallas/capas.py     # escribe svg/finca-10-capas-*.svg
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from finca import LOTS, lot_on_map  # noqa: E402
from lote import M_PER_PX, map_view, scale_bar, tool_button, zoom_controls  # noqa: E402
from ui import BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, frame, group, link, paragraph, poly, text, toggle, topbar  # noqa: E402

CELL = 250 / M_PER_PX  # un cuadro de 250 m, en píxeles del mundo
NDVI_TONES = ("#F3E9B8", "#D9E6A0", "#B5D77A", "#8CC45A", "#5FA542", "#3F8A34")  # de menos a más verde
TRUE_TONES = ("#5E7B3F", "#6F8B48", "#8A9A55", "#A8A06A", "#7C6A4C", "#4F6E3A", "#93A964")
SATELLITE = dict(name="Imagen satelital", product="MODIS Terra · color real", res="250 m", date="8 de octubre de 2026", note="Ese día había nubes sobre la zona.")
GREENNESS = dict(name="Verdor (NDVI)", product="MODIS · índice de vegetación", res="250 m", date="16 días hasta el 30 de septiembre de 2026", note="De la zona: cada cuadro cubre unas 6 hectáreas.")
GLYPH_LAYERS = ['<path d="M24 12 L38 20 L24 28 L10 20 Z" fill="none" stroke="INK" stroke-width="2.8" stroke-linejoin="round"/>'
                '<path d="M10 26 L24 34 L38 26 M10 32 L24 40 L38 32" fill="none" stroke="INK" stroke-width="2.8" stroke-linejoin="round" stroke-linecap="round"/>']


def cells(kind_):
    """La capa, como una cuadrícula de 250 m sobre el mundo. Los cuadros grandes son la resolución real del producto."""
    rnd = random.Random(11 if kind_ == "ndvi" else 23)
    tones = NDVI_TONES if kind_ == "ndvi" else TRUE_TONES
    out = []
    for r in range(-1, 7):
        for c in range(-1, 9):
            tone = tones[min(len(tones) - 1, max(0, int(rnd.gauss(3.4 if kind_ == "ndvi" else 2.5, 1.4))))]
            out.append(f'<rect x="{c * CELL:.1f}" y="{r * CELL:.1f}" width="{CELL + 0.6:.1f}" height="{CELL + 0.6:.1f}" fill="{tone}" fill-opacity="{0.78 if kind_ == "ndvi" else 0.92}"/>')
    if kind_ == "color":  # nubes del día de la imagen: se ven como son
        for cx, cy, k in ((560, 430, 1.0), (1260, 760, 1.3), (980, 300, 0.7)):
            cloud = [(cx - 150 * k, cy + 30 * k), (cx - 110 * k, cy - 30 * k), (cx - 30 * k, cy - 60 * k), (cx + 60 * k, cy - 50 * k), (cx + 150 * k, cy - 6 * k), (cx + 120 * k, cy + 44 * k), (cx - 40 * k, cy + 60 * k)]
            out.append(f'<polygon points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in cloud)}" fill="#FFFFFF" fill-opacity="0.82"/>')
    return out


def lots(zoom, compact=False):
    out = []
    for lot in LOTS:
        out += lot_on_map(lot, zoom, lot["key"] == "el-alto", compact)
    return out


def layer_row(y, w, layer, on, disabled=False):
    """Una capa con su interruptor y, debajo, su producto, su resolución y su fecha."""
    ink = SEC if disabled else P["noche"]
    out = [text(0, y + 18, layer["name"], 17, 700, ink)] + toggle(w - 64, y - 6, on and not disabled)
    out += [text(0, y + 40, f"{layer['product']} · {layer['res']}", 13, fill=SEC), text(0, y + 58, f"Imagen del {layer['date']}" if "días" not in layer["date"] else f"Compuesto de {layer['date']}", 13, fill=SEC)]
    if on and not disabled:
        out.append(text(0, y + 76, layer["note"], 13, 700, D["cielo"]))
    return out, 96 if on and not disabled else 78


def ndvi_legend(x, y, w):
    sw = (w - 24) / len(NDVI_TONES)
    body = [poly(chamfer(0, 0, w, 66, 10), WHITE, BORDE, 1.5), text(12, 22, "Verdor de la zona (NDVI)", 13, 700)]
    for i, tone in enumerate(NDVI_TONES):
        body.append(f'<rect x="{12 + i * sw:.1f}" y="30" width="{sw + 0.5:.1f}" height="12" fill="{tone}" stroke="{BORDE}" stroke-width="0.5"/>')
    body += [text(12, 58, "menos verde", 12, fill=SEC), text(w - 12, 58, "más verde", 12, fill=SEC, anchor="end")]
    return [group("leyenda-verdor", body, x, y)]


def nasa_attribution(x, y, active, anchor="end"):
    label = "© OpenStreetMap · OpenFreeMap · MapLibre" + (" · Imágenes: NASA GIBS / EOSDIS" if active else "")
    w = len(label) * 6.4 + 16
    x0 = x - w if anchor == "end" else x
    return [group("atribucion", [f'<rect x="0" y="0" width="{w:g}" height="22" fill="{WHITE}" fill-opacity="0.88"/>', text(8, 15, label, 12, fill="#4A4A48")], x0, y)]


def panel(cw, pad, state, mobile=False):
    """El control de capas. `state`: «ndvi», «color» o «caida» (la NASA no responde)."""
    fw = cw - 2 * pad
    down = state == "caida"
    c = [text(pad, 44, "MI FINCA · SAMACÁ", 14, 700, SEC), text(pad, 82, "Capas del mapa", 26 if mobile else 30, 600, font=FONT_TITLE)]
    c += link(cw - pad, 44, "Cerrar", 15, anchor="end")
    yy = 112
    base = [poly(chamfer(0, 0, fw, 58, 10), P["niebla"]), text(16, 24, "Mapa base", 13, fill=SEC), text(16, 46, "OpenStreetMap · siempre visible", 16, 700)]
    c.append(group("capa-base", base, pad, yy))
    yy += 84
    if down:
        rows = ["La NASA no respondió.", "El mapa sigue con OpenStreetMap: puede ver,", "dibujar y editar sus lotes igual."] if not mobile else \
            ["La NASA no respondió.", "El mapa sigue con OpenStreetMap:", "puede ver, dibujar y editar igual."]
        ah = 30 + len(rows) * 21
        al = [poly(chamfer(0, 0, fw, ah, 10), WHITE, D["cielo"], 2, "5 4"), poly([(26, 18), (38, 40), (14, 40)], WHITE, D["cielo"], 2), text(26, 37, "!", 13, 700, D["cielo"], anchor="middle")]
        al += [text(52, 30 + i * 21, row, 15, 700 if i == 0 else 400) for i, row in enumerate(rows)]
        c.append(group("aviso-sin-capa", al, pad, yy))
        yy += ah + 14
        c += button(pad, yy, fw, "Reintentar", "secondary", h=44)
        yy += 74
    for layer, key in ((SATELLITE, "color"), (GREENNESS, "ndvi")):
        row, rh = layer_row(yy, fw, layer, state == key, down)
        c.append(group(f"capa-{key}", row, pad, 0))
        yy += rh
        c.append(f'<rect x="{pad}" y="{yy}" width="{fw}" height="1" fill="{BORDE}"/>')
        yy += 22
    notes = ["La imagen es de la fecha indicada, no de hoy.", "El verdor es de la zona, no una medición de su lote.", "Solo para ver: no cambian ningún resultado."]
    for note in notes:
        c += [poly([(pad + 6, yy - 12), (pad + 12, yy - 6), (pad + 6, yy), (pad, yy - 6)], D["brote"]), text(pad + 22, yy, note, 13 if mobile else 14)]
        yy += 24
    c += link(pad, yy + 14, "Ver de dónde sale", 15)
    return c, yy + 40


def desktop(state="ndvi"):
    w, h = DESKTOP[0], DESKTOP[1] + 130
    zoom = 1.15
    center = (880 - 230 / zoom, 640)
    layer = [] if state == "caida" else cells(state)
    b = map_view(w, h, center, zoom, layer + lots(zoom), "recorte-capas-" + state)
    b += topbar(w, active="Mi finca", user="Rosa")
    b += zoom_controls(w - 88, 116)
    b += [group("boton-capas", tool_button(0, 0, GLYPH_LAYERS, True, name="capas"), w - 88, 240)]
    if state == "ndvi":
        b += ndvi_legend(500, h - 96, 300)
    if state == "color":
        tag = [poly(chamfer(0, 0, 392, 34, 8), WHITE, BORDE, 1.5), text(14, 22, "Imagen del 8 de octubre de 2026 · no es de hoy", 14, 700)]
        b.append(group("fecha-de-la-imagen", tag, 500, h - 64))
    b += scale_bar(w - 270, h - 66, zoom)
    b += nasa_attribution(w - 12, h - 30, state != "caida")
    x, y, cw, pad = 32, 104, 420, 26
    c, ch = panel(cw, pad, state)
    b += card(x, y, cw, ch) + [group("panel-capas", c, x, y)]
    return frame((w, h), b)


def mobile(state="ndvi"):
    w = MOBILE[0]
    zoom = 0.72
    mh = 380
    layer = [] if state == "caida" else cells(state)
    b = map_view(w, mh + 30, (905, 655), zoom, layer + lots(zoom * 1.35, compact=True), "recorte-capas-m-" + state)
    b += topbar(w)
    b += [group("boton-capas", tool_button(0, 0, GLYPH_LAYERS, True, name="capas"), w - 60, 86)]
    b += nasa_attribution(8, mh - 2, False, anchor="start")
    if state != "caida":
        b.append(group("atribucion-nasa", [f'<rect x="0" y="0" width="186" height="20" fill="{WHITE}" fill-opacity="0.88"/>', text(8, 14, "Imágenes: NASA GIBS / EOSDIS", 12, fill="#4A4A48")], 8, mh - 26))
    c, ch = panel(w, 20, state, True)
    s = [poly(chamfer(0, 0, w, ch + 60, 20), WHITE), poly(chamfer(w / 2 - 28, 10, 56, 6, 3), BORDE)] + [f'<g transform="translate(0 10)">{"".join(c)}</g>']
    if state == "ndvi":
        s += ndvi_legend(20, ch + 6, w - 40)
        ch += 80
    b += [group("hoja-capas", s, 0, mh)]
    return frame((w, mh + ch + 30), b)


SCREENS = {
    "finca-10-capas-verdor-escritorio": lambda: desktop("ndvi"),
    "finca-10-capas-satelital-escritorio": lambda: desktop("color"),
    "finca-10-capas-sin-respuesta-escritorio": lambda: desktop("caida"),
    "finca-10-capas-verdor-movil": lambda: mobile("ndvi"),
    "finca-10-capas-sin-respuesta-movil": lambda: mobile("caida"),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
