"""Pantallas finales de la tanda 8a: «Lote · historial y progreso» (D4) y «Registrar cosecha y siembra» (E).

Historial (HU-165, HU-167, HU-204): una red, no cadenas. Cada siembra dice de cuáles viene (`follows_season_ids`): un
terreno se divide en varios y varios se juntan en uno. Por cada relación se dice si la rotación cumple las reglas de
filtro y cuál regla; una que no cumple se muestra como hecho, sin puntaje. Lo borrado hace menos de 30 días se ve
aparte con «Restaurar». El progreso solo cuenta hechos registrados y reglas con fuente (R5, R8): temporadas,
rotaciones que cumplen e hitos, cada uno con lo que lo produce. Datos: GET /lots/{id}/seasons y /progress.

Registrar: primero la cosecha (PATCH /seasons/{id} con `harvest_date`) y luego la siembra (POST /lots/{id}/seasons
con cultivo, fecha, área, «¿qué había antes en este terreno?», con una o varias, y el diagnóstico que se vio). La suma de áreas no puede
pasar del área del lote. Los nombres y las cifras son de muestra.

    python design/pantallas/historial.py     # escribe svg/finca-06-historial-*.svg y svg/finca-07-registrar-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "finca"))

import ui  # noqa: E402,F401
import muestra  # noqa: E402
import cultivos as cv  # noqa: E402
import escena  # noqa: E402
from calendario import level_mark, tag, wrap_lines  # noqa: E402
from finca import CROPS, lot_header, lot_tabs  # noqa: E402
from ui import (BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, checkbox, field, frame, group, link, paragraph, poly, text,  # noqa: E402
                topbar, width_of)

OK, BAD = "cumple", "no-cumple"
# El historial de El Alto como red: cada siembra dice de cuáles viene (`follows_season_ids`). Un terreno se divide en
# varios (la cebolla de 2025 dio paso a zanahoria y abono verde) y varios se juntan en uno (papa y maíz → arveja).
# Las columnas solo ordenan por fecha de siembra; no son semestres. `slot` es la fila en escritorio.
# follows: (id de la anterior, cumple o no, regla).
SEASONS = (
    dict(id="A", crop="papa", stage=4, area=1.26, dates="feb – jul 2025", light="amarillo", col=0, slot=0, follows=()),
    dict(id="B", crop="maiz", stage=4, area=0.42, dates="feb – jul 2025", light="verde", col=0, slot=1, follows=()),
    dict(id="C", crop="cebolla", stage=4, area=0.83, dates="mar – ago 2025", light="amarillo", col=0, slot=2.5, follows=()),
    dict(id="D", crop="arveja", stage=4, area=1.68, dates="ago – dic 2025", light="verde", col=1, slot=0.5,
         follows=(("A", OK, "No repite la familia"), ("B", OK, "No repite la familia"))),
    dict(id="E", crop="zanahoria", stage=4, area=0.41, dates="sep 2025 – ene 2026", light="verde", col=1, slot=2,
         follows=(("C", OK, "No repite la familia"),)),
    dict(id="F", crop="abono", stage=3, area=0.42, dates="sep 2025 – feb 2026", light=None, col=1, slot=3,
         follows=(("C", OK, "Abono verde tras un cultivo exigente"),)),
    dict(id="G", crop="maiz", stage=4, area=1.26, dates="ene – jul 2026", light="verde", col=2, slot=0,
         follows=(("D", OK, "Leguminosa antes de un cereal"),)),
    dict(id="H", crop="arveja", stage=4, area=0.42, dates="ene – jun 2026", light="amarillo", col=2, slot=1,
         follows=(("D", BAD, "Repite la familia (leguminosas)"),)),
    dict(id="I", crop="papa_criolla", stage=4, area=0.41, dates="feb – jun 2026", light="verde", col=2, slot=2,
         follows=(("E", OK, "No repite la familia"),)),
    dict(id="J", crop="papa", stage=3, area=1.26, dates="desde el 2 ago 2026", light=muestra.LIGHT_AT_SOWING[("papa", "2026 B")], col=3, slot=0, current=True,
         follows=(("G", OK, "No repite la familia"),)),
    dict(id="L", crop="cebolla", stage=2, area=0.42, dates="desde el 16 ago 2026", light="amarillo", col=3, slot=1, current=True,
         follows=(("H", OK, "No repite la familia"),)),
    dict(id="K", crop="haba", stage=2, area=0.42, dates="desde el 1 sep 2026", light=muestra.LIGHT_AT_SOWING[("haba", "2026 B")], col=3, slot=3, current=True,
         follows=(("F", OK, "Abono verde antes de sembrar"),)),
)
BY_ID = {s["id"]: s for s in SEASONS}
FREE = dict(area=0.41, since="15 jun 2026", after="I", col=3, slot=2)  # lo que dejó la papa criolla
COLUMNS = ("Sembradas feb – mar 2025", "Sembradas ago – sep 2025", "Sembradas ene – feb 2026", "Ahora · sembradas ago – sep 2026")
LIGHT = {"verde": ("favorable", "Vio luz verde"), "amarillo": ("moderado", "Vio luz amarilla"), "rojo": ("desfavorable", "Vio luz roja"),
         "no-evaluable": (None, "No se pudo evaluar")}  # sin datos no es riesgo: forma neutra (R1)
MILESTONES = (("Primera rotación con leguminosa", "ago 2025", "Regla: bonificar leguminosas · papa y maíz → arveja"),
              ("Primer abono verde", "sep 2025", "Hecho registrado: avena con vicia después de la cebolla"),
              ("Tres siembras seguidas sin repetir familia", "ago 2026", "Regla: no repetir la familia · papa → arveja → maíz → papa"))
N_SEASONS = len(SEASONS)
N_LINKS = sum(len(s["follows"]) for s in SEASONS)
N_VALID = sum(1 for s in SEASONS for f in s["follows"] if f[1] == OK)


def ha(v):
    return f"{v:.2f}".replace(".", ",") + " ha"


def mini(crop_key, stage, x, y, size):
    """Miniatura de una temporada: su cama con el cultivo."""
    k = size / 215
    with escena.low_beds():
        body = [poly(chamfer(0, 0, size, size, size * 0.14), "#EAF0DA"),
                f'<g transform="translate({size / 2:g} {size * 0.56:g}) scale({k:g})">{"".join(cv.stage_cell(CROPS[crop_key], stage, 0, 0))}</g>']
    return [group("miniatura", body, x, y)]


def crop_label(key):
    return "Avena con vicia" if key == "abono" else CROPS[key][1]


def short(key):
    return crop_label(key).split(" ")[0].lower()


def check(x, y, ok, s=1.0):
    """Cumple (visto) o no cumple (equis): forma y color, no solo color."""
    ink = D["oliva"] if ok else D["rojo"]
    r = 9 * s
    out = [poly(chamfer(x - r, y - r, 2 * r, 2 * r, 3 if ok else 0), "#E9F2D8" if ok else "#FBE6E2", ink, 1.5)]
    out.append(f'<polyline points="{x - 5 * s:g},{y:g} {x - 1.5 * s:g},{y + 4 * s:g} {x + 5 * s:g},{y - 4 * s:g}" fill="none" stroke="{ink}" stroke-width="2.2" stroke-linecap="round"/>' if ok else
               f'<path d="M{x - 4 * s:g} {y - 4 * s:g} l{8 * s:g} {8 * s:g} M{x + 4 * s:g} {y - 4 * s:g} l{-8 * s:g} {8 * s:g}" stroke="{ink}" stroke-width="2.2" stroke-linecap="round"/>')
    return out


CARD_H = 172  # alto fijo en escritorio, para que la red quede en filas


def season_card(x, y, w, s, mobile=False):
    """Una siembra: cultivo, área y fechas; de qué siembras viene y si cada rotación cumple; la luz vista al sembrar."""
    cur = s.get("current", False)
    rows = [(state, wrap_lines([f"De {short(BY_ID[pid]['crop'])}: {rule[0].lower() + rule[1:]}"], 34 if not mobile else 44)) for pid, state, rule in s["follows"]]
    n = max(1, sum(len(r) for _, r in rows))
    h = CARD_H if not mobile else 104 + 22 * n + 30
    body = [poly(chamfer(0, 0, w, h, 12), "#FFF6EA" if cur else WHITE, P["calabaza"] if cur else BORDE, 2.5 if cur else 1.5)]
    size = 54 if not mobile else 64
    body += mini(s["crop"], s["stage"], 12, 12, size)
    tx = size + 24
    body += [text(tx, 34, crop_label(s["crop"]), 16 if not mobile else 17, 700), text(tx, 54, ha(s["area"]), 13, 700),
             text(tx, 72, s["dates"], 12 if not mobile else 13, fill=SEC)]
    ly = 98 if not mobile else 104
    if not rows:
        body.append(text(16, ly, "Primera siembra registrada aquí", 12, fill=SEC))
        ly += 22
    for state, lines in rows:
        body += check(24, ly - 4, state == OK, 0.9)
        for ln in lines:
            body.append(text(40, ly, ln, 12, 700 if state == BAD else 400, D["rojo"] if state == BAD else P["noche"]))
            ly += 18 if not mobile else 22
    ly = max(ly, 142) if not mobile else ly + 6
    if s["light"]:
        lv, label = LIGHT[s["light"]]
        if lv:
            body += level_mark(24, ly - 4, lv, 9)
        else:
            body += [poly(chamfer(14, ly - 14, 20, 20, 4), WHITE, D["cielo"], 1.5, "3 3"), text(24, ly + 1, "?", 13, 700, D["cielo"], anchor="middle")]
        body.append(text(42, ly, label + " al sembrar", 12))
    else:
        body.append(text(16, ly, "Sin diagnóstico al sembrar", 12, fill=SEC))
    # Acción: cosechar lo que está en curso; corregir o borrar lo pasado.
    body += link(w - 14, 34 if mobile else h - 12, "Registrar cosecha" if cur else "Editar", 13, anchor="end")
    return [group(f"siembra-{s['id'].lower()}-{s['crop']}", body, x, y)], h


def free_card(x, y, w, h, mobile=False):
    body = [poly(chamfer(0, 0, w, h, 12), WHITE, D["cielo"], 2, "5 5"), text(16, 32, f"Libre · {ha(FREE['area'])}", 16, 700),
            text(16, 52, f"Desde el {FREE['since']}", 12, fill=SEC)]
    body.append(text(16, 82, f"Antes: {short(BY_ID[FREE['after']]['crop'])}", 12, fill=SEC))
    body += button(16, h - 60, w - 32, "Registrar siembra", "primary", h=42)
    return [group("terreno-libre", body, x, y)]


def network(x, y, w):
    """Escritorio: la red por columnas de fecha, con una línea de cada siembra a las que vinieron después."""
    cols = len(COLUMNS)
    cw = 254
    gap = (w - cols * cw) / (cols - 1)
    step = CARD_H + 26
    pos = lambda col, slot: (col * (cw + gap), 44 + slot * step)  # noqa: E731
    out = []
    for i, label in enumerate(COLUMNS):
        out.append(text(i * (cw + gap), 20, label.upper(), 13, 700, P["calabaza"] if i == cols - 1 else SEC))
    lines = []
    def edge(a, b, ok):
        (ax, ay), (bx, by) = a, b
        ink = D["oliva"] if ok else D["rojo"]
        mx = (ax + bx) / 2
        lines.append(f'<path d="M{ax:g} {ay:g} C{mx:g} {ay:g}, {mx:g} {by:g}, {bx - 8:g} {by:g}" fill="none" stroke="{ink}" stroke-width="3"'
                     + ('' if ok else ' stroke-dasharray="7 5"') + '/>')
        lines.append(poly([(bx - 10, by - 6), (bx, by), (bx - 10, by + 6)], ink))
    for s in SEASONS:
        bx, by = pos(s["col"], s["slot"])
        for pid, state, _ in s["follows"]:
            p = BY_ID[pid]
            px, py = pos(p["col"], p["slot"])
            edge((px + cw, py + CARD_H / 2), (bx, by + CARD_H / 2), state == OK)
    fx, fy = pos(FREE["col"], FREE["slot"])
    p = BY_ID[FREE["after"]]
    px, py = pos(p["col"], p["slot"])
    lines.append(f'<path d="M{px + cw:g} {py + CARD_H / 2:g} L{fx - 8:g} {fy + CARD_H / 2:g}" fill="none" stroke="{D["cielo"]}" stroke-width="3" stroke-dasharray="3 5"/>')
    out += lines
    for s in SEASONS:
        c, _ = season_card(*pos(s["col"], s["slot"]), cw, s)
        out += c
    out += free_card(fx, fy, cw, CARD_H)
    rows = max(s["slot"] for s in SEASONS) + 1
    return [group("red-de-siembras", out, x, y)], 44 + rows * step


def legend(x, y, w):
    out = [poly(chamfer(0, 0, w, 52, 10), WHITE, BORDE, 1.5)]
    lx = 20
    for ok, label in ((True, "Cumple las reglas de rotación"), (False, "No cumple: se muestra, no resta puntos")):
        ink = D["oliva"] if ok else D["rojo"]
        out.append(f'<path d="M{lx} 26 h34" stroke="{ink}" stroke-width="3"' + ('' if ok else ' stroke-dasharray="7 5"') + '/>')
        out += check(lx + 52, 26, ok, 0.9)
        out.append(text(lx + 68, 31, label, 13))
        lx += 68 + width_of(label, 13) + 40
    out.append(text(lx, 31, "Una línea por cada terreno que pasó de una siembra a otra: se dividen y se juntan como usted trabaje.", 13, fill=SEC))
    return [group("leyenda", out, x, y)]


def progress_cards(x, y, w, mobile=False):
    """Progreso: solo hechos registrados y reglas con fuente; cada hito dice qué lo produce."""
    out = []
    if mobile:
        cw = (w - 12) / 2
        nums = ((str(N_SEASONS), "siembras registradas"), (f"{N_VALID} de {N_LINKS}", "rotaciones cumplen las reglas"))
        for i, (n, label) in enumerate(nums):
            cx = x + i * (cw + 12)
            body = [text(18, 46, n, 30, 600, font=FONT_TITLE)] + paragraph(18, 70, wrap_lines([label], 20), 13, 18, fill=SEC)
            out += card(cx, y, cw, 116, f"progreso-{i + 1}") + [group(f"progreso-{i + 1}-texto", body, cx, y)]
        my = y + 136
        body = [text(18, 36, "HITOS", 13, 700, SEC)]
        ry = 52
        for title, when, basis in MILESTONES:
            tl, bl = wrap_lines([title], 34), wrap_lines([basis], 42)
            body += [poly([(30, ry), (42, ry + 12), (30, ry + 24), (18, ry + 12)], P["trigo"], D["trigo"], 2)]
            body += paragraph(54, ry + 10, tl, 15, 18, weight=700)
            body += [text(54, ry + 12 + len(tl) * 18, when, 12, fill=SEC)]
            body += paragraph(54, ry + 28 + len(tl) * 18, bl, 12, 15, fill=SEC)
            ry += 28 + len(tl) * 18 + len(bl) * 15 + 12
        mh = ry + 6
        out += card(x, my, w, mh, "hitos") + [group("hitos-texto", body, x, my)]
        return out, 136 + mh
    nw = 250
    for i, (n, label) in enumerate(((str(N_SEASONS), "siembras registradas"), (f"{N_VALID} de {N_LINKS}", "rotaciones cumplen las reglas"))):
        cx = x + i * (nw + 20)
        body = [text(24, 62, n, 40, 600, font=FONT_TITLE)] + paragraph(24, 92, wrap_lines([label], 26), 15, 20, fill=SEC)
        out += card(cx, y, nw, 150, f"progreso-{i + 1}") + [group(f"progreso-{i + 1}-texto", body, cx, y)]
    mx = x + 2 * (nw + 20)
    mw = w - 2 * (nw + 20)
    body = [text(24, 36, "HITOS", 13, 700, SEC)]
    col = (mw - 48) / 3
    for i, (title, when, basis) in enumerate(MILESTONES):
        cx = 24 + i * col
        body += [poly([(cx + 12, 54), (cx + 24, 66), (cx + 12, 78), (cx, 66)], P["trigo"], D["trigo"], 2)]
        body += paragraph(cx + 34, 64, wrap_lines([title], 26), 15, 19, weight=700)
        body += [text(cx + 34, 108, when, 12, fill=SEC)] + paragraph(cx + 34, 124, wrap_lines([basis], 36), 12, 15, fill=SEC)
    out += card(mx, y, mw, 150, "hitos") + [group("hitos-texto", body, mx, y)]
    return out, 150


DELETED = dict(crop="Fríjol", area=0.20, dates="sembrado en mar 2026", until="2 de noviembre", until_short="2 nov")


def restore_box(x, y, w, mobile=False):
    """Lo borrado hace menos de 30 días se ve aparte y se puede restaurar (POST /seasons/{id}/restore)."""
    d = DELETED
    h = 60 if not mobile else 104
    body = [poly(chamfer(0, 0, w, h, 12), P["niebla"], BORDE, 1.5, "6 5")]
    if mobile:
        body += [text(18, 30, f"Borrada: {d['crop'].lower()}, {ha(d['area'])}", 15, 700, SEC), text(18, 52, d['dates'][0].upper() + d['dates'][1:], 13, fill=SEC),
                 text(18, 72, f"Se puede restaurar hasta el {d['until']}", 13, fill=SEC)]
        body += link(18, 94, "Restaurar", 14)
    else:
        body += [text(24, 36, f"Borrada: {d['crop'].lower()}, {ha(d['area'])}, {d['dates']}. Se puede restaurar hasta el {d['until']}.", 15, fill=SEC)]
        body += link(w - 24, 36, "Restaurar", 15, anchor="end")
    return [group("borradas", body, x, y)], h


def historial_desktop():
    w = 1440
    b = [f'<rect width="{w}" height="2600" fill="{P["niebla"]}"/>']
    b += topbar(w, active="Mi finca", user="Rosa")
    b += lot_header(48, 140)
    b += lot_tabs(48, 212, "Historial")
    b.append(text(48, 312, "Historial y progreso", 34, 600, font=FONT_TITLE))
    b.append(text(48, 340, "Cada siembra dice qué había antes en su terreno. Solo se cuentan hechos registrados y reglas con fuente.", 16, fill=SEC))
    p, ph = progress_cards(48, 366, w - 96)
    b += p
    y = 366 + ph + 40
    net, nh = network(0, 0, w - 96 - 56)
    ch = nh + 30 + 76
    b += card(48, y, w - 96, ch, "tarjeta-red")
    b.append(f'<g transform="translate({48 + 28} {y + 24})">{"".join(net)}</g>')
    b += legend(48 + 28, y + 24 + nh + 10, w - 96 - 56)
    y += ch + 32
    b.append(text(48, y + 4, "BORRADAS HACE POCO", 13, 700, SEC))
    r, rh = restore_box(48, y + 16, w - 96)
    b += r
    y += rh + 16 + 40
    b.append(text(48, y, "Una rotación que no cumple se muestra como hecho: no resta puntos ni hay puntaje de «salud del suelo».", 14, fill=SEC))
    b += link(w - 48, y, "¿Cuáles son las reglas de rotación?", 15, anchor="end")
    return ui.long_page((w, y + 60), b, P["niebla"])


def historial_mobile():
    """Móvil: la red se lee de lo más reciente a lo más viejo; cada siembra dice de cuáles viene."""
    w = MOBILE[0]
    pad, fw = 16, w - 32
    b = topbar(w) + lot_header(pad, 118, mobile=True)
    tabs = lot_tabs(-410, 0, "Historial")
    b.append(f'<defs><clipPath id="recorte-pestanas-hist"><rect x="0" y="200" width="{w}" height="60"/></clipPath></defs>'
             f'<g clip-path="url(#recorte-pestanas-hist)"><g transform="translate({pad} 210)">{"".join(tabs)}</g></g>')
    b.append(text(pad, 302, "Historial y progreso", 25, 600, font=FONT_TITLE))
    p, ph = progress_cards(pad, 322, fw, True)
    b += p
    y = 322 + ph + 30
    b += paragraph(pad, y, ["Cada siembra dice qué había antes en su", "terreno: se dividen y se juntan como usted", "trabaje."], 14, 20, fill=SEC)
    y += 76
    for col in range(len(COLUMNS) - 1, -1, -1):
        b.append(text(pad, y + 14, COLUMNS[col].upper(), 13, 700, P["calabaza"] if col == len(COLUMNS) - 1 else SEC))
        y += 28
        items = sorted((s for s in SEASONS if s["col"] == col), key=lambda s: s["slot"])
        if col == FREE["col"]:
            items = items[:2] + [None] + items[2:]
        for s in items:
            if s is None:
                b += free_card(pad, y, fw, 150, True)
                y += 150 + 12
                continue
            c, h = season_card(pad, y, fw, s, mobile=True)
            b += c
            y += h + 12
        y += 18
    b.append(text(pad, y + 4, "BORRADAS HACE POCO", 13, 700, SEC))
    r, rh = restore_box(pad, y + 16, fw, True)
    b += r
    y += rh + 16 + 30
    b += paragraph(pad, y, ["Una rotación que no cumple se muestra como", "hecho: no resta puntos."], 13, 19, fill=SEC)
    b += link(pad, y + 56, "¿Cuáles son las reglas de rotación?", 15)
    return ui.long_page((w, y + 100), b, P["niebla"])


# ---------- Registrar cosecha y siembra ----------

def step_bar(x, y, w, step):
    labels = ("1 · Cosecha", "2 · Siembra")
    half = (w - 10) / 2
    out = []
    for i, lab in enumerate(labels):
        on, done = i + 1 == step, i + 1 < step
        out.append(poly(chamfer(i * (half + 10), 0, half, 40, 8), P["noche"] if on else ("#E9F2D8" if done else WHITE), None if on else (D["oliva"] if done else BORDE), 0 if on else 1.5))
        out.append(text(i * (half + 10) + half / 2, 26, lab + (" · hecha" if done else ""), 15, 700, WHITE if on else P["noche"], anchor="middle"))
    return [group("pasos", out, x, y)]


def area_bar(x, y, w, parts):
    """Cómo queda repartido el lote: una barra con sus partes por área."""
    total = sum(a for _, a, _ in parts)
    out, cx = [], 0
    for name, a, kind in parts:
        pw = w * a / total
        fill = {"crop": "#DCEBC2", "new": P["calabaza"], "free": WHITE}[kind]
        out.append(f'<rect x="{cx:.1f}" y="0" width="{pw - 3:.1f}" height="40" fill="{fill}" stroke="{P["noche"] if kind == "new" else BORDE}" stroke-width="{2 if kind == "new" else 1.5}"'
                   + (' stroke-dasharray="4 4"' if kind == "free" else "") + "/>")
        out.append(text(cx + (pw - 3) / 2, 25, name, 13, 700, anchor="middle"))
        out.append(text(cx + (pw - 3) / 2, 58, f"{a:.2f}".replace(".", ",") + " ha", 12, fill=SEC, anchor="middle"))
        cx += pw
    return [group("reparto-del-lote", out, x, y)]


def side_summary(x, y, w, parts, title, lines):
    body = [text(24, 40, "CÓMO QUEDA EL LOTE", 14, 700, SEC), text(24, 72, title, 20, 600, font=FONT_TITLE)]
    body += area_bar(24, 96, w - 48, parts)
    body += paragraph(24, 190, [ln for line in lines for ln in wrap_lines([line], int((w - 48) / 7.3))], 14, 21, fill=SEC)
    h = 190 + sum(len(wrap_lines([line], int((w - 48) / 7.3))) for line in lines) * 21 + 20
    return card(x, y, w, h, "tarjeta-reparto") + [group("reparto", body, x, y)], h


def diagnosis_box(x, y, w, seen=True):
    """El diagnóstico que se guarda con la siembra: el que el usuario vio, con sus versiones (R4)."""
    n = int((w - 70) / 7.2)
    if seen:
        lines = wrap_lines([f"Se guarda el diagnóstico que usted vio para sembrar arveja el 15 de enero de 2027, sin riego: verde con sus prioridades y verde con el criterio de AgroSense ({muestra.VERSIONS.lower()})."], n)
        body = [poly(chamfer(0, 0, w, 28 + len(lines) * 20, 10), "#E9F2D8", D["oliva"], 1.5)] + level_mark(26, 14 + len(lines) * 10, "favorable", 12)
    else:
        lines = wrap_lines(["Todavía no ha visto el diagnóstico de este cultivo. Puede guardar la siembra sin él."], n)
        body = [poly(chamfer(0, 0, w, 28 + len(lines) * 20, 10), WHITE, D["cielo"], 1.5, "4 4"), text(26, 20 + len(lines) * 10, "?", 16, 700, D["cielo"], anchor="middle")]
    body += paragraph(50, 26, lines, 14, 20)
    return [group("diagnostico-visto", body, x, y)], 28 + len(lines) * 20


def form_page(w, mobile=False):
    b = [f'<rect width="{w}" height="2400" fill="{P["niebla"]}"/>']
    b += topbar(w, active="Mi finca", user=None if mobile else "Rosa") if not mobile else topbar(w)
    pad = 16 if mobile else 48
    b += link(pad, 118 if mobile else 140, "‹ El Alto", 16)
    return b, pad


def cosecha(mobile=False):
    w = MOBILE[0] if mobile else 1440
    b, pad = form_page(w, mobile)
    fx, fy, fw = (pad, 150, w - 2 * pad) if mobile else (48, 172, 640)
    ip = 20 if mobile else 36
    c = step_bar(ip, 28, fw - 2 * ip, 1)
    c += [text(ip, 110, "Registrar la cosecha", 26 if mobile else 32, 600, font=FONT_TITLE), text(ip, 138, "Papa · 1,26 ha · sembrada el 2 de agosto de 2026", 15, fill=SEC)]
    c += field(ip, 180, fw - 2 * ip, "¿Cuándo cosechó?", "22 de diciembre de 2026", trailing="▾", name="campo-fecha-cosecha",
               hint="La cosecha estimada era el 28 de diciembre")
    c += paragraph(ip, 300, wrap_lines(["Con la cosecha, esta parte del lote queda libre y la papa pasa al historial. Puede corregir la fecha después."], int((fw - 2 * ip) / 7.6)), 15, 22, fill=SEC)
    yy = 300 + (88 if mobile else 60)
    c += button(ip, yy, fw - 2 * ip, "Guardar cosecha y registrar la siembra")
    c += link(ip, yy + 90, "Guardar solo la cosecha", 16)
    c += link(fw - ip, yy + 90, "Cancelar", 16, anchor="end")
    ch = yy + 124
    b += card(fx, fy, fw, ch) + [group("formulario", c, fx, fy)]
    parts = (("Libre", 1.26, "new"), ("Haba", 0.42, "crop"), ("Cebolla", 0.42, "crop"), ("Libre", 0.41, "free"))
    sx, sy, sw = (pad, fy + ch + 24, w - 2 * pad) if mobile else (48 + fw + 24, fy, w - 96 - fw - 24)
    s, sh = side_summary(sx, sy, sw, parts, "Después de cosechar la papa", ["Quedan libres 1,67 ha de 2,51 ha.", "El haba y la cebolla siguen en curso."])
    b += s
    return frame((w, max(fy + ch, sy + sh) + 60), b, P["niebla"])


BEFORE = (("Papa", "1,26 ha · cosechada el 22 dic 2026", True), ("Papa criolla", "0,41 ha · cosechada el 15 jun 2026 · libre", False),
          ("Nada: es la primera siembra aquí", "Tierra del lote que no había sembrado", False))


def before_list(x, y, w, mobile=False):
    """«¿Qué había antes en este terreno?»: una o varias siembras cosechadas (`follows_season_ids`). Marcar varias junta
    terrenos; para dividir uno, se registra una siembra y luego otra desde el mismo. «Nada» deja la lista vacía."""
    out = [text(0, 0, "¿Qué había antes en este terreno?", 18, 700)]
    hint = (["Marque una o varias. Si junta terrenos,", "márquelos todos."] if mobile else ["Marque una o varias. Si junta terrenos, márquelos todos."])
    out += paragraph(0, 24, hint, 14, 20, fill=SEC)
    ry = 24 + len(hint) * 20 + 4
    for name, sub, on in BEFORE:
        out.append(poly(chamfer(0, ry, w, 58, 10), "#FFF6EA" if on else WHITE, P["calabaza"] if on else BORDE, 2 if on else 1.5))
        out += checkbox(14, ry + 13, on, name=f"casilla-{name.lower().replace(' ', '-')}")
        out += [text(58, ry + 25, name, 16, 700), text(58, ry + 45, sub, 13, fill=SEC)]
        ry += 68
    split = (["Para dividirlo en dos cultivos, registre uno y luego", "el otro marcando el mismo terreno."] if mobile else
             ["Para dividirlo en dos cultivos, registre uno y luego el otro marcando el mismo terreno."])
    out += paragraph(0, ry + 12, split, 14, 20, fill=SEC)
    return [group("antes-en-este-terreno", out, x, y)], ry + 12 + len(split) * 20 + 14


def siembra(mobile=False, error=False):
    w = MOBILE[0] if mobile else 1440
    b, pad = form_page(w, mobile)
    fx, fy, fw = (pad, 150, w - 2 * pad) if mobile else (48, 172, 640)
    ip = 20 if mobile else 36
    iw = fw - 2 * ip
    c = step_bar(ip, 28, iw, 2)
    c += [text(ip, 110, "Registrar la siembra", 26 if mobile else 32, 600, font=FONT_TITLE)]
    pv, pvh = before_list(ip, 160, iw, mobile)
    c += pv
    o = pvh - 100  # lo que crece el formulario frente al campo de antes
    c += field(ip, 272 + o, iw, "Cultivo", "Arveja", trailing="▾", name="campo-cultivo")
    c += link(ip, 364 + o, "Ver qué conviene sembrar aquí" if mobile else "Ver qué conviene sembrar después de la papa", 14)
    half = iw if mobile else (iw - 16) / 2
    ay = 408 + o
    if error:
        c += field(ip, ay, half, "Área que siembra (ha)", "1,80", state="error", hint="Solo hay 1,67 ha libres en el lote", name="campo-area")
    else:
        c += field(ip, ay, half, "Área que siembra (ha)", "1,26", hint="Hay 1,67 ha libres en el lote", name="campo-area")
    dy = ay + 120 if mobile else ay
    c += field(ip if mobile else ip + half + 16, dy, half, "Fecha de siembra", "15 de enero de 2027", trailing="▾", name="campo-fecha-siembra")
    yy = dy + 122
    dbox, dh = diagnosis_box(ip, yy, iw)
    c += dbox
    yy += dh + 24
    c += button(ip, yy, iw, "Guardar siembra", "disabled" if error else "primary")
    c += link(fw - ip, yy + 90, "Cancelar", 16, anchor="end")
    ch = yy + 124
    b += card(fx, fy, fw, ch) + [group("formulario", c, fx, fy)]
    if error:
        parts = (("Arveja", 1.80, "new"), ("Haba", 0.42, "crop"), ("Cebolla", 0.42, "crop"))
        title, lines = "No cabe en el lote", ["1,80 + 0,42 + 0,42 = 2,64 ha, y el lote tiene 2,51 ha.", "Baje el área a 1,67 ha o menos."]
    else:
        parts = (("Arveja", 1.26, "new"), ("Haba", 0.42, "crop"), ("Cebolla", 0.42, "crop"), ("Libre", 0.41, "free"))
        title, lines = "Con la arveja sembrada", ["La arveja ocupa la parte donde estuvo la papa.", "Queda libre 0,41 ha.", "Papa → arveja cumple la regla: no repite la familia."]
    sx, sy, sw = (pad, fy + ch + 24, w - 2 * pad) if mobile else (48 + fw + 24, fy, w - 96 - fw - 24)
    s, sh = side_summary(sx, sy, sw, parts, title, lines)
    b += s
    return frame((w, max(fy + ch, sy + sh) + 60), b, P["niebla"])


SCREENS = {
    "finca-06-historial-escritorio": historial_desktop,
    "finca-06-historial-movil": historial_mobile,
    "finca-07-registrar-cosecha-escritorio": cosecha,
    "finca-07-registrar-siembra-escritorio": siembra,
    "finca-07-registrar-siembra-movil": lambda: siembra(mobile=True),
    "finca-07-registrar-siembra-error-movil": lambda: siembra(mobile=True, error=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
    print("siembras", N_SEASONS, "rotaciones", N_VALID, "de", N_LINKS)
