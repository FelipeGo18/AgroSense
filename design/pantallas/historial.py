"""Pantallas finales de la tanda 8a: «Lote · historial y progreso» (D4) y «Registrar cosecha y siembra» (E).

Historial (HU-165, HU-167): cada terreno del lote tiene su historial: una temporada puede venir de varias y tener varias sucesoras (`follows_season_ids`). Entre dos
siembras seguidas se dice si la rotación cumple las reglas de filtro y cuál regla; una que no cumple se muestra
como hecho, sin puntaje. El progreso solo cuenta hechos registrados y reglas con fuente (R5, R8): temporadas,
rotaciones que cumplen e hitos, cada uno con lo que lo produce. Datos: GET /lots/{id}/seasons y /progress.

Registrar: primero la cosecha (PATCH /seasons/{id} con `harvest_date`) y luego la siembra (POST /lots/{id}/seasons
con cultivo, fecha, área, «¿qué había antes en esta parte?» y el diagnóstico que se vio). La suma de áreas no puede
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
from ui import (BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, field, frame, group, link, paragraph, poly, text,  # noqa: E402
                topbar, width_of)

OK, BAD = "cumple", "no-cumple"
# Cadenas por parte del lote. Temporada: semestre, cultivo, etapa para la miniatura, fechas, luz vista al sembrar.
# Enlace con la anterior: (cumple o no, regla).
CHAINS = (
    dict(name="Parte de la papa", area="1,26 ha", seasons=(
        ("2025 A", "papa", 4, "feb – jul 2025", "amarillo", None),
        ("2025 B", "arveja", 4, "ago – dic 2025", "verde", (OK, "No repite la familia")),
        ("2026 A", "maiz", 4, "ene – jul 2026", None, (OK, "Leguminosa antes de un cereal")),
        ("2026 B", "papa", 3, "desde ago 2026", muestra.LIGHT_AT_SOWING[("papa", "2026 B")], (OK, "No repite la familia"))), free=False),
    dict(name="Parte del haba", area="0,42 ha", seasons=(
        ("2025 B", "cebolla", 4, "sep 2025 – ene 2026", "amarillo", None),
        ("2026 A", "abono", 3, "feb – may 2026", None, (OK, "Abono verde tras un cultivo exigente")),
        ("2026 B", "haba", 2, "desde sep 2026", muestra.LIGHT_AT_SOWING[("haba", "2026 B")], (OK, "No repite la familia"))), free=False),
    dict(name="Parte de la cebolla", area="0,42 ha", seasons=(
        ("2026 A", "arveja", 4, "feb – jun 2026", "verde", None),
        ("2026 B", "cebolla", 2, "desde ago 2026", "amarillo", (OK, "No repite la familia"))), free=False),
    dict(name="Parte libre", area="0,41 ha", seasons=(
        ("2025 B", "papa", 4, "ago – dic 2025", "verde", None),
        ("2026 A", "papa_criolla", 4, "ene – jun 2026", "rojo", (BAD, "Repite la familia (solanáceas)"))), free=True),
)
LIGHT = {"verde": ("favorable", "Vio luz verde"), "amarillo": ("moderado", "Vio luz amarilla"), "rojo": ("desfavorable", "Vio luz roja"),
         "no-evaluable": (None, "No se pudo evaluar")}  # sin datos no es riesgo: forma neutra (R1)
MILESTONES = (("Primera rotación con leguminosa", "dic 2025", "Regla: bonificar leguminosas · papa → arveja"),
              ("Primer abono verde", "feb 2026", "Hecho registrado: avena con vicia en la parte del haba"),
              ("Tres siembras seguidas sin repetir familia", "ago 2026", "Regla: no repetir la familia · parte de la papa"))
N_SEASONS = sum(len(c["seasons"]) for c in CHAINS)
N_LINKS = sum(1 for c in CHAINS for s in c["seasons"] if s[5])
N_VALID = sum(1 for c in CHAINS for s in c["seasons"] if s[5] and s[5][0] == OK)


def mini(crop_key, stage, x, y, size):
    """Miniatura de una temporada: su cama con el cultivo."""
    k = size / 215
    with escena.low_beds():
        body = [poly(chamfer(0, 0, size, size, size * 0.14), "#EAF0DA"),
                f'<g transform="translate({size / 2:g} {size * 0.56:g}) scale({k:g})">{"".join(cv.stage_cell(CROPS[crop_key], stage, 0, 0))}</g>']
    return [group("miniatura", body, x, y)]


def crop_label(key):
    return "Avena con vicia" if key == "abono" else CROPS[key][1]


def season_card(x, y, w, season, current, mobile=False):
    sem, crop, stage, dates, light, _ = season
    h = 140 if not mobile else 104
    body = [poly(chamfer(0, 0, w, h, 12), "#FFF6EA" if current else WHITE, P["calabaza"] if current else BORDE, 2.5 if current else 1.5)]
    if mobile:
        body += mini(crop, stage, 12, 14, 76)
        tx = 100
        body += [text(tx, 28, sem, 12, 700, SEC), text(tx, 50, crop_label(crop), 17, 700), text(tx, 70, dates, 13, fill=SEC)]
        ly = 90
    else:
        body += mini(crop, stage, 12, 12, 54)
        tx = 76
        body += [text(tx, 30, sem, 12, 700, SEC), text(tx, 51, crop_label(crop), 15, 700), text(tx, 70, dates, 12, fill=SEC)]
        ly = 96
        tx = 16
    if light:
        lv, label = LIGHT[light]
        if lv:
            body += level_mark(tx + 8, ly, lv, 10)
        else:
            body += [poly(chamfer(tx - 2, ly - 10, 20, 20, 4), WHITE, D["cielo"], 1.5, "3 3"), text(tx + 8, ly + 5, "?", 13, 700, D["cielo"], anchor="middle")]
        body.append(text(tx + 24, ly + 5, label + " al sembrar", 12))
    else:
        body.append(text(tx, ly + 5, "Sin diagnóstico al sembrar", 12, fill=SEC))
    if current:
        body += tag(w - 44, 10, "En curso", P["calabaza"], P["noche"])
        if not mobile:
            body += link(w - 14, h - 12, "Registrar cosecha", 13, anchor="end")
    else:
        body += link(w - 14, (h - 12) if not mobile else 28, "Editar", 13, anchor="end")
    return [group(f"temporada-{sem.replace(' ', '-').lower()}-{crop}", body, x, y)], h


def rotation_link(x, y, w, link_, vertical=False):
    """Entre dos siembras: si la rotación cumple las reglas de filtro y cuál regla."""
    state, rule = link_
    ok = state == OK
    ink = D["oliva"] if ok else D["rojo"]
    out = []
    if vertical:
        out += [f'<rect x="{x + 22}" y="{y}" width="3" height="{w}" fill="{ink}"/>',
                poly(chamfer(x + 12, y + w / 2 - 11, 22, 22, 4 if ok else 0), "#E9F2D8" if ok else "#FBE6E2", ink, 2)]
        cx, cy = x + 23, y + w / 2
        out.append(f'<polyline points="{cx - 6},{cy} {cx - 2},{cy + 5} {cx + 6},{cy - 5}" fill="none" stroke="{ink}" stroke-width="2.5" stroke-linecap="round"/>' if ok else
                   f'<path d="M{cx - 5} {cy - 5} l10 10 M{cx + 5} {cy - 5} l-10 10" stroke="{ink}" stroke-width="2.5" stroke-linecap="round"/>')
        out += [text(x + 46, y + w / 2 - 2, "Cumple" if ok else "No cumple", 13, 700, ink), text(x + 46, y + w / 2 + 15, rule, 12, fill=SEC)]
        return out
    out += [f'<rect x="{x}" y="{y + 40}" width="{w}" height="3" fill="{ink}"/>', poly([(x + w - 2, y + 34), (x + w + 8, y + 41.5), (x + w - 2, y + 49)], ink),
            poly(chamfer(x + w / 2 - 12, y + 29, 24, 24, 4 if ok else 0), "#E9F2D8" if ok else "#FBE6E2", ink, 2)]
    cx, cy = x + w / 2, y + 41
    out.append(f'<polyline points="{cx - 6},{cy} {cx - 2},{cy + 5} {cx + 6},{cy - 5}" fill="none" stroke="{ink}" stroke-width="2.5" stroke-linecap="round"/>' if ok else
               f'<path d="M{cx - 5} {cy - 5} l10 10 M{cx + 5} {cy - 5} l-10 10" stroke="{ink}" stroke-width="2.5" stroke-linecap="round"/>')
    out.append(text(cx, y + 70, "Cumple" if ok else "No cumple", 12, 700, ink, anchor="middle"))
    for i, ln in enumerate(wrap_lines([rule], 13)):
        out.append(text(cx, y + 86 + i * 14, ln, 11, fill=SEC, anchor="middle"))
    return out


def free_slot(x, y, w, h, mobile=False):
    body = [poly(chamfer(0, 0, w, h, 12), WHITE, D["cielo"], 2, "5 5"), text(16, 34, "Ahora", 12, 700, SEC), text(16, 58, "Libre desde el 15 jun", 16, 700)]
    body += button(16, h - 62, w - 32, "Registrar siembra", "primary", h=44)
    return [group("parte-libre", body, x, y)]


def chain_row(x, y, w, chain):
    """Escritorio: la cadena de una parte, de izquierda a derecha."""
    cw, lw = 212, 84
    out = [text(0, 22, chain["name"], 18, 700), text(0, 44, chain["area"], 14, fill=SEC)]
    cx = 170
    for i, s in enumerate(chain["seasons"]):
        if s[5]:
            out += rotation_link(cx, 0, lw - 12, s[5])
            cx += lw
        current = i == len(chain["seasons"]) - 1 and not chain["free"]
        c, h = season_card(cx, 0, cw, s, current)
        out += c
        cx += cw
    if chain["free"]:
        out += [f'<rect x="{cx + 8}" y="40" width="{lw - 28}" height="3" fill="{BORDE}"/>'] + free_slot(cx + lw, 0, 220, 140)
    return [group("cadena-" + chain["name"].split(" ")[-1], out, x, y)], 140


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


def restore_box(x, y, w, mobile=False):
    """Una temporada borrada se puede restaurar durante 30 días."""
    body = [poly(chamfer(0, 0, w, 60 if not mobile else 84, 12), WHITE, D["cielo"], 2, "4 4")]
    if mobile:
        body += [text(18, 30, "1 siembra borrada: maíz, 2025 B", 15, 700), text(18, 52, "Se puede restaurar hasta el 2 nov", 13, fill=SEC)] + link(18, 74, "Restaurar", 14)
    else:
        body += [text(24, 36, "1 siembra borrada: maíz, 2025 B, en la parte del haba. Se puede restaurar hasta el 2 de noviembre.", 15)] + link(w - 24, 36, "Restaurar", 15, anchor="end")
    return [group("borradas", body, x, y)], 60 if not mobile else 84


def historial_desktop():
    w = 1440
    b = [f'<rect width="{w}" height="2600" fill="{P["niebla"]}"/>']
    b += topbar(w, active="Mi finca", user="Rosa")
    b += lot_header(48, 140)
    b += lot_tabs(48, 212, "Historial")
    b.append(text(48, 312, "Historial y progreso", 34, 600, font=FONT_TITLE))
    b.append(text(48, 340, "Cada parte del lote lleva su propia cadena de siembras. Solo se cuentan hechos registrados y reglas con fuente.", 16, fill=SEC))
    p, ph = progress_cards(48, 366, w - 96)
    b += p
    y = 366 + ph + 40
    ch = len(CHAINS) * 168 + 30
    b += card(48, y, w - 96, ch, "tarjeta-cadenas")
    for i, chain in enumerate(CHAINS):
        row, _ = chain_row(48 + 28, y + 30 + i * 168, w - 96 - 56, chain)
        b += row
        if i:
            b.append(f'<rect x="{48 + 28}" y="{y + 30 + i * 168 - 18}" width="{w - 96 - 56}" height="1" fill="{BORDE}"/>')
    y += ch + 32
    r, rh = restore_box(48, y, w - 96)
    b += r
    y += rh + 30
    b.append(text(48, y, "Una rotación que no cumple se muestra como hecho: no resta puntos ni hay puntaje de «salud del suelo».", 14, fill=SEC))
    b += link(w - 48, y, "¿Cuáles son las reglas de rotación?", 15, anchor="end")
    return frame((w, y + 60), b, P["niebla"])


def historial_mobile():
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
    for chain in CHAINS:
        b += [text(pad, y + 20, chain["name"], 18, 700), text(w - pad, y + 20, chain["area"], 14, fill=SEC, anchor="end")]
        y += 34
        seasons = chain["seasons"][::-1]  # lo más reciente arriba
        if chain["free"]:
            b += free_slot(pad, y, fw, 132, True)
            y += 132
            b += [f'<rect x="{pad + 22}" y="{y}" width="3" height="22" fill="{BORDE}"/>']
            y += 22
        for i, s in enumerate(seasons):
            current = i == 0 and not chain["free"]
            c, h = season_card(pad, y, fw, s, current, True)
            b += c
            y += h
            if current:
                b += button(pad, y + 10, fw, "Registrar cosecha", "secondary", h=44)
                y += 64
            if s[5]:
                b += rotation_link(pad, y, 52, s[5], vertical=True)
                y += 52
        y += 30
    r, rh = restore_box(pad, y, fw, True)
    b += r
    y += rh + 24
    b += paragraph(pad, y, ["Una rotación que no cumple se muestra como", "hecho: no resta puntos."], 13, 19, fill=SEC)
    b += link(pad, y + 56, "¿Cuáles son las reglas de rotación?", 15)
    return frame((w, y + 100), b, P["niebla"])


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
        lines = wrap_lines(["Se guarda el diagnóstico que usted vio: arveja, semestre A de 2027, luz verde (datos 2026.11.0 · reglas 1.0.0)."], n)
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


def siembra(mobile=False, error=False):
    w = MOBILE[0] if mobile else 1440
    b, pad = form_page(w, mobile)
    fx, fy, fw = (pad, 150, w - 2 * pad) if mobile else (48, 172, 640)
    ip = 20 if mobile else 36
    iw = fw - 2 * ip
    c = step_bar(ip, 28, iw, 2)
    c += [text(ip, 110, "Registrar la siembra", 26 if mobile else 32, 600, font=FONT_TITLE)]
    c += field(ip, 152, iw, "¿Qué había antes en esta parte?", "Papa · cosechada el 22 dic · 1,26 ha", trailing="▾", name="campo-parte",
               hint="Así se arma el historial de esta parte")
    c += field(ip, 272, iw, "Cultivo", "Arveja", trailing="▾", name="campo-cultivo")
    c += link(ip, 364, "Ver qué conviene sembrar aquí" if mobile else "Ver qué conviene sembrar después de la papa", 14)
    half = iw if mobile else (iw - 16) / 2
    ay = 408
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
