"""Pantallas finales de Mi finca, tanda 7a: «Mis lotes en el mapa» (D0) y «Lote vivo y paso del tiempo» (D1).

Mis lotes: el mapa real (MapLibre + OpenStreetMap) con los polígonos de los lotes, sus cultivos, sus etapas y sus avisos.
Lote vivo (HU-187): el diorama del lote como cubos de tierra juntos, uno o más por cultivo según su parte del área,
con una casita y un perro acostado detrás y el clima de ahora. Se recorre arrastrando y acercando; tocar un cultivo lo
elige. La línea de tiempo (HU-186) es la del cultivo elegido: real hasta el último dato de temperatura y estimada con
un año normal después; los demás cultivos avanzan a la misma fecha.
Datos: GET /lots, GET /lots/{id} (current_seasons), GET /seasons/{id}/growth, POST /water-plans (falta de agua
estimada: sin riego, «la lluvia no alcanza»; con riego, «riego probable») y POST /calendar (meses con riesgo de
helada). El clima de ahora es ambiente (Open-Meteo): se rotula como condición aproximada, con su fuente y su hora.
Los nombres y las cifras son de muestra.

    python design/pantallas/finca.py     # escribe svg/finca-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "finca"))

import ui  # noqa: E402,F401
import muestra  # noqa: E402
import cultivos as cv  # noqa: E402
import escena  # noqa: E402
from lote import G, LOT, LOT_INK, FIELDS, attribution, fmt_ha, area_ha, map_view, scale_bar, tool_button, zoom_controls  # noqa: E402
from ui import (BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, field, frame, group, link,  # noqa: E402
                paragraph, poly, pts, text, topbar, width_of)

CROPS = {c[0]: c for c in cv.CROPS}


def ha(v):
    return f"{v:.2f}".replace(".", ",") + " ha"


# Lotes de muestra en Samacá (coordenadas del mundo del mapa de lote.py). Cada parte: cultivo (None si está libre),
# etapa de hoy y del 20 de diciembre, día desde la siembra, área y los cubos que ocupa en el diorama.
LOTS = (
    dict(key="el-alto", name="El Alto", irrigated=False, area_pts=[(842, 498), (968, 482), (1004, 590), (936, 652), (850, 628)], alerts=("agua",), parts=(
        dict(crop="papa", stage=3, sim=5, day=70, area=1.26, cells=((0, 0), (1, 0), (2, 0))),
        dict(crop="haba", stage=2, sim=4, day=40, area=0.42, cells=((0, 1),)),
        dict(crop="cebolla", stage=2, sim=4, day=56, area=0.42, cells=((1, 1),)),
        dict(crop=None, area=0.41, cells=((2, 1),)))),
    dict(key="la-vega", name="La Vega", irrigated=True, area_pts=[(1022, 628), (1142, 610), (1166, 716), (1040, 738)], alerts=(), parts=(
        dict(crop="maiz", stage=2, sim=4, day=41, area=1.66, cells=((0, 0),)),)),
    dict(key="el-bajo", name="El Bajo", irrigated=False, area_pts=[(690, 540), (796, 528), (812, 626), (700, 640)], alerts=("helada",), parts=(
        dict(crop="arveja", stage=1, sim=4, day=12, area=1.33, cells=((0, 0),)),)),
    dict(key="potrero", name="Potrero", irrigated=None, area_pts=[(870, 700), (972, 690), (986, 784), (884, 796)], alerts=(), parts=(
        dict(crop=None, area=1.19, cells=((0, 0),)),)),
)
ALTO = LOTS[0]
# Lote borrado hace poco: GET /lots lo trae con `deleted_at` y `restorable_until` (30 días).
DELETED = dict(name="La Loma", area=0.86, deleted="3 oct", until="2 nov")


def irrigation_label(lot):
    return {True: "Con riego", False: "Sin riego", None: "Riego sin definir"}[lot["irrigated"]]


def water_alert(lot, form="short"):
    """Aviso de falta de agua de un lote. El texto sale de `irrigated`, como en agua.py: sin riego la lluvia no alcanza
    (el cultivo pasaría sed) y no se habla de riego; con riego, es riego probable. Siempre es una estimación (R10)."""
    base = "Riego probable" if lot["irrigated"] else "La lluvia no alcanza"
    return {"short": base, "chip": f"{base} · estimación", "long": f"{base} este mes · estimación"}[form]


# El clima de ahora es ambiente (decisión 7): condición aproximada, con su fuente y la hora de la lectura.
LIVE = "Condición aproximada en Samacá: nublado · 13 °C · Open-Meteo · 10:40"
LIVE_SHORT = "Ahora: nublado · 13 °C · Open-Meteo 10:40"


def stage_name(part, sim=False):
    crop = CROPS[part["crop"]]
    return cv.STAGES[crop[3]][part["sim"] if sim else part["stage"]]


def crop_name(part):
    return CROPS[part["crop"]][1].split(" ")[0] if part["crop"] else "Libre"


def layout_of(lot, sim=False):
    return [(i, j, p["crop"] or "libre", CROPS.get(p["crop"]), (p["sim"] if sim else p["stage"]) if p["crop"] else 0)
            for p in lot["parts"] for i, j in p["cells"]]


def planted(lot):
    return [p for p in lot["parts"] if p["crop"]]


def crops_label(lot):
    names = [crop_name(p).lower() for p in planted(lot)]
    if not names:
        return "Sin siembra"
    s = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " y " + names[-1]
    return s[0].upper() + s[1:]


# ---------- Piezas ----------

def thumb(lot, x, y, size):
    """Miniatura del lote: sus cubos juntos, cada cultivo en su etapa."""
    lay = layout_of(lot)
    n = max(i + j for i, j, *_ in lay) + 1
    k = size / (230 + 105 * (n - 1))
    body = [poly(chamfer(0, 0, size, size, size * 0.14), "#EAF0DA" if planted(lot) else P["niebla"])]
    with escena.low_beds():
        body.append(f'<g transform="translate({size / 2:g} {size * 0.52:g})">{"".join(escena.cubes(0, 0, k * 1.08, lay))}</g>')
    return [group("miniatura", body, x, y)]


def drop(x, y, s=1.0, fill=None):
    return [f'<g transform="translate({x:g} {y:g}) scale({s:g})">' + poly([(0, -9), (7, 2), (4, 8), (-4, 8), (-7, 2)], fill or P["cielo"], D["cielo"], 1.5) + "</g>"]


def flake(x, y, s=1.0, ink=None):
    ink = ink or D["cielo"]
    arms = "".join(f'<line x1="0" y1="0" x2="0" y2="-9" stroke="{ink}" stroke-width="2" stroke-linecap="round" transform="rotate({a})"/>' for a in range(0, 360, 60))
    return [f'<g transform="translate({x:g} {y:g}) scale({s:g})">{arms}<circle r="2" fill="{ink}"/></g>']


def stage_bar(x, y, w, stage, h=8):
    """Seis tramos, uno por etapa: los pasados llenos, el actual en calabaza."""
    gap = 4
    seg = (w - 5 * gap) / 6
    return [poly(chamfer(x + i * (seg + gap), y, seg, h, 2), D["oliva"] if i < stage else (P["calabaza"] if i == stage else P["niebla"])) for i in range(6)]


def pill(x, y, label, on=False):
    w = width_of(label, 13) + 18
    return [poly(chamfer(x, y, w, 24, 6), P["noche"] if on else "#EEF2E4"), text(x + 9, y + 17, label, 13, 700 if on else 400, WHITE if on else P["noche"])], w


def lot_row(x, y, w, lot, selected=False):
    parts = planted(lot)
    multi = len(lot["parts"]) > 1
    tx = 112
    inner = []
    if not parts:
        inner.append(text(tx, 58, "Sin siembra en curso", 15, fill=SEC))
        inner += link(tx, 90, "Registrar siembra", 15)
        h = 112
    elif multi:  # varios cultivos: una ficha por cultivo con su etapa; el alto crece con las filas de fichas
        px, py = tx, 46
        for p in parts:
            pl, pw = pill(px, py, f"{crop_name(p)} · {stage_name(p).lower()}")
            if px + pw > w - 12:
                px, py = tx, py + 30
                pl, pw = pill(px, py, f"{crop_name(p)} · {stage_name(p).lower()}")
            inner += pl
            px += pw + 6
        h = max(112, py + 24 + (36 if lot["alerts"] else 14))
    else:
        h = 112
    body = [poly(chamfer(0, 0, w, h, 12), "#FFF6EA" if selected else WHITE, LOT if selected else BORDE, 2.5 if selected else 1.5)]
    body += thumb(lot, 12, 14, 84)
    body.append(text(tx, 34, lot["name"], 19, 700))
    body.append(text(w - 16, 34, fmt_ha(area_ha(lot["area_pts"])), 14, fill=SEC, anchor="end"))
    body += inner
    if parts and not multi:
        p = parts[0]
        body.append(text(tx, 58, f"{CROPS[p['crop']][1]} · {stage_name(p)} · día {p['day']}", 15))
        body += stage_bar(tx, 70, w - tx - 16, p["stage"])
    ax = tx
    for a in lot["alerts"]:
        body += drop(ax + 8, h - 14, 0.8) if a == "agua" else flake(ax + 8, h - 15, 0.8)
        short = water_alert(lot) if a == "agua" else "Riesgo de helada"
        body.append(text(ax + 20, h - 9, short, 13, 700, D["cielo"]))
        ax += width_of(short, 13, True) + 34
    return [group(f"lote-{lot['key']}", body, x, y)], h


def lot_on_map(lot, s, selected=False, compact=False):
    """El polígono del lote y su rótulo con nombre, cultivos y avisos. Tocarlo abre el lote vivo."""
    p = lot["area_pts"]
    sown = bool(planted(lot))
    out = [f'<polygon points="{pts(p)}" fill="{FIELDS[0]}"/>',
           f'<polygon points="{pts(p)}" fill="{LOT if sown else P["cielo"]}" fill-opacity="{0.42 if selected else 0.28}" '
           f'stroke="{LOT_INK if sown else D["cielo"]}" stroke-width="{(5 if selected else 3) / s:g}" stroke-linejoin="round"/>']
    cx, cy = sum(x for x, _ in p) / len(p), sum(y for _, y in p) / len(p)
    name = lot["name"]
    parts = planted(lot)
    sub = (f"{CROPS[parts[0]['crop']][1]} · {stage_name(parts[0]).lower()}" if len(parts) == 1 else crops_label(lot)) if parts else "Sin siembra"
    if compact:  # móvil: solo el nombre y los avisos; el detalle está en la lista
        w = width_of(name, 15, True) + 26 + 22 * len(lot["alerts"])
        tag = [poly(chamfer(-w / 2, -36, w, 30, 7), P["noche"] if selected else WHITE, None if selected else P["noche"], 0 if selected else 2),
               poly([(-7, -6), (7, -6), (0, 2)], P["noche"]), text(-w / 2 + 11, -16, name, 15, 700, WHITE if selected else P["noche"])]
        ay = -21
    else:
        w = max(width_of(name, 15, True), width_of(sub, 13)) + 30 + 22 * len(lot["alerts"])
        tag = [poly(chamfer(-w / 2, -52, w, 46, 8), P["noche"] if selected else WHITE, None if selected else P["noche"], 0 if selected else 2),
               poly([(-7, -6), (7, -6), (0, 2)], P["noche"]),
               text(-w / 2 + 12, -33, name, 15, 700, WHITE if selected else P["noche"]),
               text(-w / 2 + 12, -15, sub, 13, fill=P["niebla"] if selected else SEC)]
        ay = -30
    ax = w / 2 - 16
    for a in lot["alerts"]:
        tag += drop(ax, ay, 0.9, P["cielo"]) if a == "agua" else flake(ax, ay, 0.9, P["cielo"] if selected else D["cielo"])
        ax -= 22
    out.append(f'<g transform="translate({cx:g} {cy:g}) scale({1 / s:g})">{"".join(tag)}</g>')
    return out


def zone_select(x, y, w):
    return field(x, y, w, "Zona", "Samacá, Boyacá · 4 lotes", trailing="▾", name="selector-zona")


def map_legend(x, y):
    """La gota sirve para lotes con y sin riego: «falta de agua»; cada lote dice después si es riego probable o no alcanza."""
    rows = (("agua", "Falta de agua: estimación con el clima de la zona"), ("helada", "Riesgo de helada: meses con heladas en el histórico"))
    body = [poly(chamfer(0, 0, 404, 76, 10), WHITE, BORDE, 1.5)]
    for i, (k, label) in enumerate(rows):
        body += drop(18, 25 + i * 28, 0.8) if k == "agua" else flake(18, 24 + i * 28, 0.8)
        body.append(text(34, 29 + i * 28, label, 13))
    return [group("leyenda", body, x, y)]


# ---------- D0 · Mis lotes en el mapa ----------

def deleted_row(x, y, w):
    """Un lote borrado hace menos de 30 días: se ve aparte y se puede restaurar (POST /lots/{id}/restore)."""
    d = DELETED
    body = [poly(chamfer(0, 0, w, 76, 12), P["niebla"], BORDE, 1.5, "6 5"),
            text(16, 30, d["name"], 17, 700, SEC), text(16 + width_of(d["name"], 17, True) + 10, 30, ha(d["area"]), 14, fill=SEC),
            text(16, 56, f"Borrado el {d['deleted']} · se puede restaurar hasta el {d['until']}", 13, fill=SEC)]
    body += link(w - 16, 30, "Restaurar", 15, anchor="end")
    return [group("lote-borrado", body, x, y)], 76


def lot_list(x, y, w, selected=None):
    out, yy = [], y
    for lot in LOTS:
        row, rh = lot_row(x, yy, w, lot, lot["key"] == selected)
        out += row
        yy += rh + 10
    out.append(text(x, yy + 22, "BORRADOS HACE POCO", 13, 700, SEC))
    row, rh = deleted_row(x, yy + 34, w)
    out += row
    return out, yy + 34 + rh + 14


def mis_lotes_desktop():
    w, h = DESKTOP[0], DESKTOP[1] + 130
    zoom = 1.15
    center = (880 - 230 / zoom, 640)
    drawn = []
    for lot in LOTS:
        drawn += lot_on_map(lot, zoom, lot["key"] == "el-alto")
    b = map_view(w, h, center, zoom, drawn, "recorte-mis-lotes")
    b += topbar(w, active="Mi finca", user="Rosa")
    b += zoom_controls(w - 88, 116)
    b += map_legend(500, h - 100)
    b += scale_bar(w - 270, h - 66, zoom)
    b += attribution(w - 12, h - 30)
    x, y, cw, pad = 32, 104, 440, 24
    fw = cw - 2 * pad
    c = [text(pad, 44, "MI FINCA", 15, 700, SEC), text(pad, 82, "Sus lotes", 34, 600, font=FONT_TITLE)]
    c += zone_select(pad, 122, fw)
    rows, yy = lot_list(pad, 206, fw, "el-alto")
    c += rows
    c += button(pad, yy + 4, fw, "Agregar lote")
    b += card(x, y, cw, yy + 76) + [group("panel", c, x, y)]
    return frame((w, h), b)


def mis_lotes_mobile():
    w = MOBILE[0]
    zoom = 0.72
    center = (905, 655)
    drawn = []
    for lot in LOTS:
        drawn += lot_on_map(lot, zoom * 1.35, compact=True)
    mh = 380
    b = map_view(w, mh + 30, center, zoom, drawn, "recorte-mis-lotes-m")
    b += topbar(w)  # sin «mi ubicación»: ninguna spec pide geolocalización
    b += attribution(w - 8, mh - 2)
    pad, fw = 16, w - 32
    s = [poly(chamfer(0, 0, w, 1400, 20), WHITE), poly(chamfer(w / 2 - 28, 10, 56, 6, 3), BORDE)]
    s += [text(pad, 50, "MI FINCA", 14, 700, SEC), text(pad, 84, "Sus lotes", 26, 600, font=FONT_TITLE)]
    s += zone_select(pad, 122, fw)
    rows, yy = lot_list(pad, 210, fw)
    s += rows
    s += button(pad, yy + 6, fw, "Agregar lote")
    yy += 84
    s += paragraph(pad, yy, ["Falta de agua: estimación con el clima de la", "zona. Riesgo de helada: meses con heladas", "en el histórico del municipio."], 13, 19, fill=SEC)
    b += [group("hoja", s, 0, mh)]
    return frame((w, mh + yy + 80), b)


# ---------- D1 · Lote vivo y paso del tiempo ----------

PAPA_PART = ALTO["parts"][0]
DATA_UNTIL, TODAY, SIM, HARVEST = 64, 70, 140, 148  # días desde la siembra de la papa (2 de agosto de 2026)
BOUNDS = (0, 0.05, 0.2, 0.42, 0.62, 0.92, 1.0)  # fin de cada etapa como fracción del ciclo
MONTHS = ((0, "2 ago"), (30, "1 sep"), (60, "1 oct"), (91, "1 nov"), (121, "1 dic"), (148, "28 dic"))
STAGE_TONES = ("#D9C79A", "#C7DDA0", "#9CC152", "#F2C46B", "#E0A15A", "#B98A5E")


def lot_tabs(x, y, active):
    """Navegación del lote: cada pestaña abre su vista (D1 a D4)."""
    out, tx = [], 0
    for t in ("Ahora", "Calendario", "Próxima siembra", "Agua", "Historial"):
        tw = width_of(t, 17, True) + 36
        on = t == active
        out.append(poly(chamfer(tx, 0, tw, 44, 10), P["noche"] if on else WHITE, None if on else BORDE, 0 if on else 1.5))
        out.append(text(tx + tw / 2, 28, t, 17, 700, WHITE if on else P["noche"], anchor="middle"))
        tx += tw + 8
    return [group("pestanas-del-lote", out, x, y)]


def timeline(x, y, w, cursor, mobile=False):
    """Línea de tiempo del cultivo elegido (GET /seasons/{id}/growth). Se arrastra o se reproduce."""
    fx = lambda d: x + 70 + (w - 70) * d / HARVEST  # noqa: E731
    out = [poly(chamfer(x, y - 4, 52, 52, 10), D["oliva"]), poly([(x + 20, y + 9), (x + 36, y + 22), (x + 20, y + 35)], WHITE)]  # reproducir
    labels = cv.STAGES[CROPS["papa"][3]]
    for i in range(6):
        a, bnd = BOUNDS[i] * HARVEST, BOUNDS[i + 1] * HARVEST
        out.append(f'<rect x="{fx(a):.1f}" y="{y + 6}" width="{fx(bnd) - fx(a) - 2:.1f}" height="32" fill="{STAGE_TONES[i]}"/>')
    pid = "rayado-ano-normal" + ("-m" if mobile else "")
    out.append(f'<defs><pattern id="{pid}" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
               f'<rect width="4" height="10" fill="{WHITE}" fill-opacity="0.6"/></pattern></defs>')
    out.append(f'<rect x="{fx(DATA_UNTIL):.1f}" y="{y + 6}" width="{fx(HARVEST) - fx(DATA_UNTIL):.1f}" height="32" fill="url(#{pid})"/>')
    for i in range(6):
        a, bnd = BOUNDS[i] * HARVEST, BOUNDS[i + 1] * HARVEST
        if (not mobile or i in (1, 3, 5)) and fx(bnd) - fx(a) > (50 if not mobile else 30):
            lab = labels[i] if not mobile else labels[i][:5] + ("." if len(labels[i]) > 5 else "")
            out.append(text((fx(a) + fx(bnd)) / 2, y + 27, lab, 13 if not mobile else 11, 700, anchor="middle"))
    out.append(f'<rect x="{x + 70}" y="{y + 6}" width="{w - 70}" height="32" fill="none" stroke="{P["noche"]}" stroke-width="2"/>')
    for d, label in MONTHS if not mobile else MONTHS[::2] + (MONTHS[-1],):
        out.append(f'<rect x="{fx(d) - 1:.1f}" y="{y + 38}" width="2" height="8" fill="{P["noche"]}"/>')
        out.append(text(fx(d), y + 62, label, 13 if not mobile else 12, fill=SEC, anchor="middle"))
    out.append(f'<rect x="{fx(TODAY) - 1.5:.1f}" y="{y - 6}" width="3" height="52" fill="{P["noche"]}"/>')
    out.append(text(fx(TODAY), y - 12, "Hoy", 13, 700, anchor="middle"))
    cx = fx(cursor)
    out.append(poly([(cx, y - 2), (cx + 13, y + 22), (cx, y + 46), (cx - 13, y + 22)], P["calabaza"], P["noche"], 2.5))
    ly = y + 92 if not mobile else y + 88
    out += [f'<rect x="{x}" y="{ly - 12}" width="22" height="14" fill="{STAGE_TONES[2]}" stroke="{P["noche"]}" stroke-width="1.5"/>',
            text(x + 30, ly, "Real: temperatura de la zona hasta el 5 oct", 13)]
    lx, ly2 = (x + 380, ly) if not mobile else (x, ly + 24)
    out += [f'<rect x="{lx}" y="{ly2 - 12}" width="22" height="14" fill="{STAGE_TONES[2]}" stroke="{P["noche"]}" stroke-width="1.5"/>',
            f'<rect x="{lx}" y="{ly2 - 12}" width="22" height="14" fill="url(#{pid})"/>',
            text(lx + 30, ly2, "Estimación con un año normal, no es pronóstico", 13, 700)]
    if not mobile:
        out.append(text(x + w, ly, "Los demás cultivos del lote avanzan a la misma fecha", 13, fill=SEC, anchor="end"))
    return [group("linea-de-tiempo", out)]


def parts_card(x, y, w, sim=False):
    """Los cultivos del lote, cada uno con su parte del área. Tocar uno lo elige; la parte libre invita a sembrar."""
    rows = ALTO["parts"]
    step, rh, fs = 42, 36, 14
    h = 56 + len(rows) * step + 6
    body = [text(18, 34, "CULTIVOS DE ESTE LOTE", 13, 700, SEC), text(w - 18, 34, fmt_ha(area_ha(ALTO["area_pts"])), 13, 700, anchor="end")]
    for i, p in enumerate(rows):
        ry = 48 + i * step
        on = p is PAPA_PART
        body.append(poly(chamfer(10, ry, w - 20, rh, 7), "#FFF1DF" if on else WHITE, LOT if on else BORDE, 2 if on else 1))
        body.append(text(22, ry + 23, crop_name(p) if p["crop"] else "Libre", fs + 1, 700))
        body.append(text(100, ry + 23, ha(p["area"]), fs, fill=SEC))
        if p["crop"]:
            body.append(text(w - 22, ry + 23, stage_name(p, sim), fs, 700 if on else 400, anchor="end"))
        elif sim:  # al adelantar el tiempo no se registra nada
            body.append(text(w - 22, ry + 23, "Sin siembra", fs, fill=SEC, anchor="end"))
        else:
            body += link(w - 22, ry + 23, "Registrar siembra", fs, anchor="end")
    return card(x, y, w, h, "tarjeta-cultivos") + [group("cultivos", body, x, y)], h


def crop_card(x, y, w, sim=False):
    st = PAPA_PART["sim"] if sim else PAPA_PART["stage"]
    h = 172
    body = [text(18, 34, "CULTIVO ELEGIDO" if not sim else "ADELANTANDO EL TIEMPO", 13, 700, SEC),
            text(18, 64, f"Papa · {cv.STAGES['anual'][st].lower()}", 21, 600, font=FONT_TITLE)]
    body += stage_bar(18, 76, w - 36, st, 8)
    if sim:
        body += paragraph(18, 110, ["20 de diciembre · día 140", "Cosecha estimada: 28 dic 2026"], 14, 21)
        body += paragraph(18, 156, ["Con un año normal; no es pronóstico."], 12, fill=SEC)
    else:
        body += paragraph(18, 110, ["Día 70 desde la siembra (2 ago)", "Cosecha estimada: 28 dic · año normal"], 14, 21)
        body += paragraph(18, 156, ["Etapa estimada con la temperatura de la zona."], 12, fill=SEC)
    return card(x, y, w, h, "tarjeta-cultivo") + [group("cultivo", body, x, y)], h


def soil_card(x, y, w):
    """El suelo estimado del lote. «Ver suelo» (agua.py, proxima.py) trae aquí, a la pestaña «Ahora»."""
    narrow = w < 400
    h = 300 if narrow else 172
    soil = muestra.SOIL_ALTO
    rows = (("pH", soil["ph"], "rango probable " + soil["ph_range"]), ("Carbono orgánico", soil["soc"], "nivel " + soil["soc_class"]), ("Textura", soil["texture"], ""))
    body = [text(24, 40, "SUELO DE SU LOTE · ESTIMACIÓN", 14, 700, SEC)]
    if narrow:
        for i, (k, v, r) in enumerate(rows):
            ry = 76 + i * 50
            body += [text(24, ry, k, 16), text(w - 24, ry, v, 16, 700, anchor="end")]
            if r:
                body.append(text(w - 24, ry + 20, r, 13, fill=SEC, anchor="end"))
        body += paragraph(24, 236, ["Mapa global de 250 m (SoilGrids), mediana de su", "polígono. Para decidir, haga un análisis de suelo."], 13, 19, fill=SEC)
    else:  # ancho: tres columnas
        for i, (k, v, r) in enumerate(rows):
            cx = 24 + i * (w - 48) / 3
            body += [text(cx, 76, k, 15, fill=SEC), text(cx, 104, v, 20, 700)]
            if r:
                body.append(text(cx, 126, r, 13, fill=SEC))
        body.append(text(24, 154, "Mapa global de 250 m (SoilGrids), mediana del polígono del lote; el mismo para todas sus partes. Para decidir, haga un análisis de suelo.", 13, fill=SEC))
    return card(x, y, w, h, "tarjeta-suelo") + [group("suelo", body, x, y)], h


def diorama_controls(x, y):
    """Recorrer el diorama: acercar, alejar y volver a encuadrar todo el lote."""
    frame_glyph = ['<path d="M13 19v-6h6M29 13h6v6M35 29v6h-6M19 35h-6v-6" fill="none" stroke="INK" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>']
    return [group("recorrer-diorama", tool_button(0, 0, G["mas"], name="acercar") + tool_button(0, 58, G["menos"], name="alejar")
                  + tool_button(0, 116, frame_glyph, name="encuadrar-lote"), x, y)]


def hint(x, y, label):
    w = width_of(label, 14, True) + 52
    hand = '<path d="M16 22 v-11 a2.5 2.5 0 0 1 5 0 v8 M21 18 v-2 a2.5 2.5 0 0 1 5 0 v4 M26 19 a2.5 2.5 0 0 1 5 0 v5 c0 5-3 8-8 8 h-2 c-3 0-5-2-6-4 l-4-6 a2.4 2.4 0 0 1 4-2.5 l1.5 2" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    return [group("ayuda-recorrer", [poly(chamfer(0, 0, w, 36, 10), P["noche"], None, 0), f'<g transform="translate(4 -1) scale(0.95)">{hand}</g>',
                                     text(40, 23, label, 14, 700, WHITE)], x, y)]


def alto_tags(sim=False):
    """Rótulos de cada cultivo sobre sus cubos (posición en unidades del catálogo, con el lote centrado)."""
    lay = layout_of(ALTO, sim)
    out = []
    for p in ALTO["parts"]:
        cells = p["cells"]
        xs, ys = zip(*(escena.cube_pos(lay, i, j) for i, j in cells))
        tx, ty = sum(xs) / len(xs), min(ys) - (70 if p["crop"] else 35)
        label = crop_name(p)
        sub = (f"{stage_name(p, sim).lower()} · {ha(p['area'])}" if p["crop"] else ha(p["area"]))
        out.append(((tx, ty), label, sub, p is PAPA_PART))
    return tuple(out)


def lot_header(x, y, mobile=False, right=None):
    """Nombre, cultivos, área, zona y riego del lote. «Editar lote» abre su edición (PATCH /lots/{id})."""
    sub = f"{crops_label(ALTO)} · {fmt_ha(area_ha(ALTO['area_pts']))} · Samacá, Boyacá"
    out = link(x, y, "‹ Mi finca", 16)
    # `right`: la pestaña «Ahora» suma el riego y «Editar lote»; las demás pestañas dejan la cabecera corta.
    if mobile:
        out += [text(x, y + 44, "El Alto", 30, 600, font=FONT_TITLE), text(x, y + 72, sub, 15, fill=SEC)]
        if right:
            out.append(text(x, y + 94, irrigation_label(ALTO), 15, 700))
            out += link(right, y + 44, "Editar lote", 16, anchor="end")
    else:
        out += [text(x, y + 50, "El Alto", 40, 600, font=FONT_TITLE), text(x + 170, y + 48, f"{sub} · {irrigation_label(ALTO).lower()}" if right else sub, 17, fill=SEC)]
        if right:
            out += link(right, y + 48, "Editar lote", 17, anchor="end")
    return out


def lote_vivo_desktop(sim=False):
    w, h = 1440, 1370
    b = [f'<rect width="{w}" height="{h}" fill="{P["niebla"]}"/>']
    b += topbar(w, active="Mi finca", user="Rosa")
    b += lot_header(48, 140, right=w - 48)
    b += lot_tabs(48, 212, "Ahora")
    sx, sy, sw, sh = 48, 282, 1010, 670
    common = dict(crop=None, layout=layout_of(ALTO, sim), selected="papa", tags=alto_tags(sim), farm=True, lot_k=1.05, lot_y=0.6, lot_x=0.6, seed=4)
    if sim:
        body = escena.scene(sw, sh, "dia", (), "normal", (), **common)
    else:
        body = escena.scene(sw, sh, "dia", ("nublado",), "seco", ((water_alert(ALTO, "long"), "riego"), (LIVE, "vivo")), **common)
    b.append(f'<g id="lote-vivo" transform="translate({sx} {sy})">{escena.framed(body, sw, sh, "recorte-lote-vivo" + ("-sim" if sim else ""))}</g>')
    b += diorama_controls(sx + sw - 68, sy + 20)
    if sim:
        # «Adelantó el tiempo», no «simulación»: ese nombre es del modo de desarrollo con respuestas simuladas.
        banner = [poly(chamfer(0, 0, 600, 64, 12), P["noche"]), text(20, 28, "Adelantó el tiempo · 20 de diciembre de 2026", 17, 700, WHITE),
                  text(20, 50, "Estimación con un año normal, no es pronóstico. Sin clima en vivo.", 14, fill=P["niebla"])]
        b.append(group("aviso-simulacion", banner, sx + 20, sy + 20))
        b += button(sx + sw - 200, sy + sh - 76, 180, "Volver a hoy", "secondary")
    else:
        b += hint(sx + sw - 290, sy + sh - 56, "Arrastre para recorrer el lote")
    cx_, cw = sx + sw + 20, w - sx - sw - 20 - 48
    pc, ph = parts_card(cx_, sy, cw, sim)
    b += pc
    cc, ch = crop_card(cx_, sy + ph + 20, cw, sim)
    b += cc
    if not sim:
        b += button(cx_, sy + ph + ch + 42, cw, "Registrar cosecha de papa", "secondary")
    ty = sy + sh + 40
    tl = [poly(chamfer(0, 8, w - 96, 176, 16), BORDE), poly(chamfer(0, 0, w - 96, 176, 16), WHITE),
          text(24, 40, "Papa · del 2 de agosto a la cosecha", 20, 700), text(w - 96 - 24, 40, "Arrastre el rombo o toque reproducir", 14, fill=SEC, anchor="end")]
    tl += timeline(24, 70, w - 96 - 48, SIM if sim else TODAY)
    b.append(group("tiempo", tl, 48, ty))
    sc_, sh_ = soil_card(48, ty + 210, w - 96)
    b += sc_
    return ui.long_page((w, ty + 210 + sh_ + 60), b, P["niebla"])


def plan_2d(w, h):
    """Modo ligero (HU-158): el lote visto desde arriba, quieto y en 2D, con la misma información que el diorama."""
    out = [f'<rect width="{w}" height="{h}" fill="#DDE8C6"/>']
    gw, gh = w - 48, h - 170
    cw, ch = gw / 3, gh / 2
    x0, y0 = 24, 70
    tones = {"papa": STAGE_TONES[3], "haba": STAGE_TONES[2], "cebolla": STAGE_TONES[2]}
    for p in ALTO["parts"]:
        cells = p["cells"]
        i0, i1 = min(i for i, _ in cells), max(i for i, _ in cells)
        j0 = min(j for _, j in cells)
        rx, ry, rw = x0 + i0 * cw, y0 + j0 * ch, (i1 - i0 + 1) * cw
        on = p is PAPA_PART
        if p["crop"]:
            out.append(poly(chamfer(rx + 3, ry + 3, rw - 6, ch - 6, 8), tones[p["crop"]], P["calabaza"] if on else P["noche"], 3 if on else 1.5))
            for k in range(int(rw // 26)):  # surcos
                out.append(f'<rect x="{rx + 14 + k * 26:.1f}" y="{ry + 12}" width="3" height="{ch - 24:.1f}" fill="{P["noche"]}" fill-opacity="0.12"/>')
            out += [text(rx + 14, ry + 30, crop_name(p), 16, 700), text(rx + 14, ry + 50, f"{stage_name(p).lower()} · {ha(p['area'])}", 12)]
        else:
            out.append(poly(chamfer(rx + 3, ry + 3, rw - 6, ch - 6, 8), "#C9B48A", P["noche"], 1.5, "5 5"))
            out += [text(rx + 14, ry + 30, "Libre", 16, 700), text(rx + 14, ry + 50, ha(p["area"]), 12)]
    chip = lambda x, y, label, icon: [group("aviso", [poly(chamfer(0, 0, len(label) * 7.2 + 44, 30, 8), WHITE, BORDE, 1.5), *icon, text(34, 20, label, 13, 700)], x, y)]  # noqa: E731
    out += chip(16, 16, "Modo ligero · imagen fija", [poly(chamfer(10, 8, 14, 14, 3), P["niebla"], P["noche"], 1.5)])
    cloud = [f'<path d="M10 20 a5 5 0 0 1 3 -9 a6 6 0 0 1 11 2 a4 4 0 0 1 0 7 z" fill="{P["niebla"]}" stroke="{P["noche"]}" stroke-width="1.5"/>']
    out += chip(16, h - 84, LIVE_SHORT, cloud)
    out += chip(16, h - 46, water_alert(ALTO, "long"), drop(17, 15, 0.8))
    return out


def lote_vivo_mobile(view=(-30, 30, 1.45), name="m", light=False):
    """`view` es el recorrido del diorama: desplazamiento y acercamiento tras arrastrar y pellizcar."""
    w = MOBILE[0]
    pad = 16
    b = topbar(w) + lot_header(pad, 118, mobile=True, right=w - pad)
    tabs = lot_tabs(0, 0, "Ahora")
    b.append(f'<defs><clipPath id="recorte-pestanas"><rect x="0" y="222" width="{w}" height="60"/></clipPath></defs>'
             f'<g clip-path="url(#recorte-pestanas)"><g transform="translate({pad} 232)">{"".join(tabs)}</g></g>')
    sw, sh = w, 520
    if light:
        body = plan_2d(sw, sh)
    else:
        body = escena.scene(sw, sh, "dia", ("nublado",), "seco", ((water_alert(ALTO, "chip"), "riego"), (LIVE_SHORT, "vivo")),
                            crop=None, layout=layout_of(ALTO), selected="papa", tags=alto_tags(), farm=True, lot_k=0.62, lot_y=0.56, seed=6,
                            view=view)
    b.append(f'<g id="lote-vivo" transform="translate(0 292)"><defs><clipPath id="recorte-lote-vivo-{name}"><rect width="{sw}" height="{sh}"/></clipPath></defs>'
             f'<g clip-path="url(#recorte-lote-vivo-{name})">{"".join(body)}</g></g>')
    if not light:  # la imagen fija no se recorre
        b += [f'<g transform="translate({w - 60} 308) scale(0.85)">{"".join(diorama_controls(0, 0))}</g>']
        b += hint(pad, 292 + 16, "Arrastre con un dedo")
    y = 292 + sh + 20
    pc, ph = parts_card(pad, y, w - 2 * pad)
    b += pc
    y += ph + 24
    tl = [text(0, 24, "Papa · del 2 de agosto a la cosecha", 17, 700)]
    tl += timeline(0, 60, w - 2 * pad, TODAY, mobile=True)
    b.append(group("tiempo", tl, pad, y))
    y += 196
    cc, ch = crop_card(pad, y, w - 2 * pad)
    b += cc
    y += ch + 20
    s_, sh_ = soil_card(pad, y, w - 2 * pad)
    b += s_
    y += sh_ + 28
    b += button(pad, y, w - 2 * pad, "Registrar cosecha de papa", "secondary")
    return ui.long_page((w, y + 90), b, P["niebla"])


SCREENS = {
    "finca-01-mis-lotes-escritorio": mis_lotes_desktop,
    "finca-01-mis-lotes-movil": mis_lotes_mobile,
    "finca-02-lote-vivo-escritorio": lote_vivo_desktop,
    "finca-02-lote-vivo-simulacion-escritorio": lambda: lote_vivo_desktop(sim=True),
    "finca-02-lote-vivo-movil": lote_vivo_mobile,
    "finca-02-lote-vivo-recorrido-movil": lambda: lote_vivo_mobile(view=(215, 70, 1.5), name="m2"),
    "finca-02-lote-vivo-ligero-movil": lambda: lote_vivo_mobile(name="m3", light=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
