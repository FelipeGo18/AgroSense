"""Tanda 8: «Finca temporal» sin cuenta (HU-141, HU-145) y «Guardar la finca temporal» al crear la cuenta (HU-168).

Sin cuenta hay una sola finca temporal: área total, si tiene riego y, por cultivo, su porcentaje del terreno y su
fecha de siembra; lo que falta para 100 % es descanso. Se envía a POST /water-plans solo para calcular y no se guarda
en el servidor ni en este dispositivo (R9; guardarla en el navegador es HU-149, P1). Al crear la cuenta se ofrece
guardarla como un lote sin dibujar con una temporada por cultivo, cada una con su parte del área: la finca pasa de la
página al registro sin guardarse antes en ningún lado. El plan de agua es
una estimación con el clima de la zona (R10). Los nombres y las cifras son de muestra.

    python design/pantallas/temporal.py     # escribe svg/finca-08-temporal-*.svg y svg/cuenta-07-guardar-finca-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from agua import fmt, m3  # noqa: E402
from calendario import wrap_lines  # noqa: E402
from finca import drop  # noqa: E402
from lote import IRRIGATION, options  # noqa: E402
from ui import BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, field, frame, group, link, paragraph, poly, text, topbar  # noqa: E402

AREA = 3.0
# cultivo, porcentaje del terreno, sembrado el, déficit en mm por mes (mín, máx) en un año normal
ROWS = (("Papa", 50, "2 ago 2026", {2: (10, 22), 4: (18, 30)}), ("Arveja", 30, "1 sep 2026", {2: (6, 14), 3: (8, 16), 4: (14, 24)}))
ROWS_ERROR = (("Papa", 60, "2 ago 2026", {}), ("Arveja", 50, "1 sep 2026", {}))
MONTHS = ("Ago", "Sep", "Oct", "Nov", "Dic", "Ene")
TODAY = 2


def ha(v):
    return f"{v:.2f}".replace(".", ",") + " ha"


def area_of(pct):
    return AREA * pct / 100


def month_totals():
    out = []
    for m in range(len(MONTHS)):
        lo = sum(m3(d[m][0], area_of(p)) for _, p, _, d in ROWS if m in d)
        hi = sum(m3(d[m][1], area_of(p)) for _, p, _, d in ROWS if m in d)
        out.append((lo, hi))
    return out


TOTALS = month_totals()


def note_r9(x, y, w, mobile=False):
    rows = (["Sin cuenta, su finca se envía solo para", "calcular: no se guarda en el servidor ni", "en este dispositivo. Solo contamos la", "consulta, sin datos suyos."] if mobile else
            ["Sin cuenta, su finca se envía solo para calcular: no se guarda en el servidor ni en este dispositivo.", "Solo contamos la consulta por municipio y cultivo, sin datos suyos."])
    h = 26 + len(rows) * 21 + 8
    body = [poly(chamfer(0, 0, w, h, 10), "#EEF2E4"), poly([(16, 14), (30, 14), (30, 30), (23, 36), (16, 30)], D["oliva"])]
    body += paragraph(44, 28, rows, 14, 21)
    return [group("aviso-no-se-guarda", body, x, y)], h


def share_bar(x, y, w, rows):
    """El terreno repartido: cada cultivo con su porcentaje y su área; lo que sobra es descanso."""
    total = sum(p for _, p, _, _ in rows)
    parts = [(name, p, P["calabaza"] if i == 0 else P["brote"]) for i, (name, p, _, _) in enumerate(rows)]
    if total < 100:
        parts.append(("Descanso", 100 - total, None))
    out, cx = [], 0
    scale = w / max(100, total)
    for name, p, fill in parts:
        pw = p * scale
        over = total > 100 and cx + pw > w
        out.append(f'<rect x="{cx:.1f}" y="0" width="{pw - 3:.1f}" height="36" fill="{fill or WHITE}" stroke="{D["rojo"] if over else (BORDE if not fill else P["noche"])}" '
                   f'stroke-width="{2.5 if over else 1.5}"' + (' stroke-dasharray="4 4"' if not fill else "") + "/>")
        out.append(text(cx + (pw - 3) / 2, 23, f"{name} {p} %", 13, 700, anchor="middle"))
        out.append(text(cx + (pw - 3) / 2, 54, ha(area_of(p)), 12, fill=SEC, anchor="middle"))
        cx += pw
    if total > 100:
        out.append(f'<rect x="{w - 1:.1f}" y="-6" width="3" height="48" fill="{D["rojo"]}"/>')
    return [group("reparto", out, x, y)]


def crop_row(x, y, w, row, mobile=False, error=False):
    name, pct, date, _ = row
    if mobile:
        out = field(0, 0, w - 52, "Cultivo", name, trailing="▾", name="campo-cultivo")
        half = (w - 12) / 2
        out += field(0, 100, half, "% del terreno", str(pct), state="error" if error else "normal", name="campo-porcentaje")
        out += field(half + 12, 100, half, "Sembrado el", date, trailing="▾", name="campo-fecha")
        out += [group("quitar", [poly(chamfer(0, 0, 44, 44, 8), WHITE, BORDE, 2), '<path d="M14 14 l16 16 M30 14 l-16 16" stroke="#1D1D1B" stroke-width="2.5" stroke-linecap="round"/>'], w - 44, 14)]
        return [group(f"cultivo-{name.lower()}", out, x, y)], 196
    cw = (w - 52 - 24) / 3
    out = field(0, 0, cw, "Cultivo", name, trailing="▾", name="campo-cultivo")
    out += field(cw + 12, 0, cw, "% del terreno", str(pct), state="error" if error else "normal", name="campo-porcentaje")
    out += field(2 * (cw + 12), 0, cw, "Sembrado el", date, trailing="▾", name="campo-fecha")
    out += [group("quitar", [poly(chamfer(0, 0, 44, 44, 8), WHITE, BORDE, 2), '<path d="M14 14 l16 16 M30 14 l-16 16" stroke="#1D1D1B" stroke-width="2.5" stroke-linecap="round"/>'], w - 44, 18)]
    return [group(f"cultivo-{name.lower()}", out, x, y)], 96


def farm_form(w, mobile=False, error=False):
    """El formulario de la finca temporal. Devuelve las piezas y el alto."""
    rows = ROWS_ERROR if error else ROWS
    c = [text(0, 0, "MI FINCA · SIN CUENTA", 14, 700, SEC), text(0, 40, "Su finca en Samacá", 28 if mobile else 34, 600, font=FONT_TITLE)]
    nt, nh = note_r9(0, 62, w, mobile)
    c += nt
    y = 62 + nh + 28
    c += field(0, y, w if mobile else 260, "Área total (ha)", "3,00", name="campo-area")
    y += 104
    c += [text(0, y, "¿Tiene riego?", 18, 700)] + options(0, y + 16, w, IRRIGATION, 1, 16)
    y += 96
    c.append(text(0, y, "Cultivos", 20, 700))
    c.append(text(w, y, "La parte que no ocupe queda en descanso", 13, fill=SEC, anchor="end") if not mobile else text(0, y + 22, "La parte que no ocupe queda en descanso.", 13, fill=SEC))
    y += 46 if not mobile else 68
    for i, row in enumerate(rows):
        r, rh = crop_row(0, y, w, row, mobile, error and i == 1)
        c += r
        y += rh
    c += link(0, y + 10, "+ Agregar cultivo", 16)
    y += 46
    c += share_bar(0, y, w, rows)
    y += 72
    if error:
        total = sum(p for _, p, _, _ in rows)
        body = [poly(chamfer(0, 0, w, 64 if not mobile else 84, 10), "#FBE6E2", D["rojo"], 2), poly(chamfer(14, 14, 16, 16, 0), D["rojo"])]
        body += paragraph(42, 28, [f"Los cultivos suman {total} %: baje alguno", "para llegar a 100 % o menos."] if mobile else
                          [f"Los cultivos suman {total} % del terreno. Baje alguno para llegar a 100 % o menos."], 15, 22, weight=700, fill=D["rojo"])
        c.append(group("aviso-error", body, 0, y))
        y += (64 if not mobile else 84) + 20
    c += button(0, y, w, "Calcular el plan de agua", "disabled" if error else "primary")
    return c, y + 60


def water_card(w, mobile=False):
    """El plan de agua de la finca temporal: lo que faltaría cada mes, en rangos (R10)."""
    c = [text(0, 0, "PLAN DE AGUA · ESTIMACIÓN", 14, 700, SEC), text(0, 36, "Lo que faltaría cada mes", 22 if mobile else 26, 600, font=FONT_TITLE)]
    c += paragraph(0, 62, ["Con el clima de la zona, no una medición de", "su finca. Sin riego, en los meses marcados", "el cultivo pasaría sed."] if mobile else
                   ["Con el clima de la zona, no una medición de su finca. Sin riego, en los", "meses marcados el cultivo pasaría sed. Verifique la humedad en campo."], 14, 21, fill=SEC)
    y = 62 + (3 if mobile else 2) * 21 + 20
    vmax = max(hi for _, hi in TOTALS) or 1
    lab = 70
    bw = w - lab - (150 if not mobile else 120)
    for m, (lo, hi) in enumerate(TOTALS):
        ry = y + m * 44
        c.append(text(0, ry + 24, MONTHS[m] + (" 2027" if MONTHS[m] == "Ene" else ""), 15, 700 if m == TODAY else 400))
        if hi:
            c += [poly(chamfer(lab, ry + 8, bw * hi / vmax, 24, 3), "#E6F0F5", D["cielo"], 1.5), poly(chamfer(lab, ry + 8, bw * lo / vmax, 24, 3), P["cielo"], D["cielo"], 1.5)]
            c += drop(lab + bw * hi / vmax + 16, ry + 20, 0.8)
            c.append(text(w, ry + 25, f"{fmt(lo)} a {fmt(hi)} m³", 14, 700, anchor="end"))
        else:
            c.append(text(lab, ry + 25, "La lluvia alcanza", 14, fill=SEC))
    y += len(MONTHS) * 44 + 14
    lo, hi = sum(t[0] for t in TOTALS), sum(t[1] for t in TOTALS)
    c += [f'<rect x="0" y="{y}" width="{w}" height="2" fill="{P["noche"]}"/>', text(0, y + 30, "Faltaría en la temporada", 16, 700),
          text(w, y + 30, f"{fmt(lo)} a {fmt(hi)} m³", 18, 700, anchor="end")]
    return c, y + 46


def save_card(w, mobile=False):
    c = [text(0, 0, "¿Quiere guardarla?", 22 if mobile else 24, 600, font=FONT_TITLE)]
    c += paragraph(0, 30, ["Con una cuenta, su finca se guarda como", "un lote con una temporada por cultivo, y", "puede dibujarlo en el mapa."] if mobile else
                   ["Con una cuenta, su finca se guarda como un lote con una temporada", "por cultivo, y puede dibujarlo en el mapa."], 15, 22)
    y = 30 + (3 if mobile else 2) * 22 + 16
    if mobile:
        c += button(0, y, w, "Crear cuenta") + link(w / 2, y + 86, "Ya tengo cuenta: entrar", 16, anchor="middle")
        return c, y + 100
    c += button(0, y, 240, "Crear cuenta") + link(268, y + 32, "Ya tengo cuenta: entrar", 16)
    return c, y + 60


def temporal_desktop(error=False):
    w = 1440
    fw = 620
    form, fh = farm_form(fw, error=error)
    b = [f'<rect width="{w}" height="2400" fill="{P["niebla"]}"/>'] + topbar(w, active="Mi finca")
    b += card(48, 120, fw + 72, fh + 80) + [group("finca-temporal", form, 84, 170)]
    rx, rw = 48 + fw + 72 + 24, w - 96 - fw - 72 - 24
    wc, wh = water_card(rw - 72)
    b += card(rx, 120, rw, wh + 84) + [group("plan-de-agua", wc, rx + 36, 170)]
    sc, sh = save_card(rw - 72)
    sy = 120 + wh + 84 + 24
    b += card(rx, sy, rw, sh + 76) + [group("guardar", sc, rx + 36, sy + 48)]
    h = max(120 + fh + 80, sy + sh + 76) + 60
    return ui.long_page((w, h), b, P["niebla"])


def temporal_mobile(error=False):
    w = MOBILE[0]
    pad, fw = 16, w - 32
    form, fh = farm_form(fw - 40, True, error)
    b = topbar(w) + card(pad, 96, fw, fh + 70) + [group("finca-temporal", form, pad + 20, 142)]
    y = 96 + fh + 70 + 24
    if not error:
        wc, wh = water_card(fw - 40, True)
        b += card(pad, y, fw, wh + 76) + [group("plan-de-agua", wc, pad + 20, y + 44)]
        y += wh + 76 + 24
    sc, sh = save_card(fw - 40, True)
    b += card(pad, y, fw, sh + 70) + [group("guardar", sc, pad + 20, y + 46)]
    return ui.long_page((w, y + sh + 70 + 50), b, P["niebla"])


# ---------- Guardar la finca temporal al crear la cuenta ----------

def season_rows(x, y, w):
    out = []
    rows = [(name, area_of(p), date) for name, p, date, _ in ROWS] + [("Libre", area_of(100 - sum(p for _, p, _, _ in ROWS)), None)]
    for i, (name, a, date) in enumerate(rows):
        ry = i * 58
        out.append(poly(chamfer(0, ry, w, 50, 10), WHITE if date else P["niebla"], BORDE, 1.5, None if date else "5 5"))
        out += [text(16, ry + 22, name, 16, 700), text(16, ry + 40, f"{ha(a)} · desde el {date}" if date else f"{ha(a)} · en descanso", 13, fill=SEC)]
        if date:
            out.append(text(w - 16, ry + 31, "Sin diagnóstico al sembrar", 12, fill=SEC, anchor="end"))
    return [group("temporadas", out, x, y)], len(rows) * 58


def save_temporal(mobile=False):
    w = MOBILE[0] if mobile else 1440
    cw = w - 32 if mobile else 720
    x0 = 16 if mobile else (w - cw) / 2
    pad = 20 if mobile else 40
    iw = cw - 2 * pad
    c = [text(pad, 52, "CUENTA CREADA", 14, 700, SEC), text(pad, 92, "¿Guardamos su finca?", 26 if mobile else 34, 600, font=FONT_TITLE)]
    c += paragraph(pad, 124, ["Antes de crear la cuenta llenó una finca.", "Se guardaría como un lote sin dibujar."] if mobile else
                   ["Antes de crear la cuenta llenó una finca sin cuenta. Se guardaría como un lote sin dibujar, con una", "temporada por cultivo."], 15, 22)
    y = 124 + 44 + 26
    c += field(pad, y, iw, "Nombre del lote", "Mi finca", name="campo-nombre")
    y += 104
    c += [text(pad, y, "Samacá, Boyacá · 3,00 ha · sin riego", 16, 700)]
    y += 20
    s, sh = season_rows(pad, y, iw)
    c += s
    y += sh + 10
    c += paragraph(pad, y + 14, wrap_lines(["Puede dibujarlo en el mapa después; mientras tanto se usa el suelo del municipio. Lo puede editar o borrar cuando quiera."], 44 if mobile else 86), 14, 21, fill=SEC)
    y += 14 + (3 if mobile else 2) * 21 + 20
    if mobile:
        c += button(pad, y, iw, "Guardar como lote") + button(pad, y + 70, iw, "No guardarla", "secondary")
        y += 140
    else:
        bw = (iw - 16) / 2
        c += button(pad, y, bw, "Guardar como lote") + button(pad + bw + 16, y, bw, "No guardarla", "secondary")
        y += 70
    c += paragraph(pad, y + 14, ["«No guardarla» la descarta: no queda guardada en ningún lado."], 13, fill=SEC)
    ch = y + 40
    top = 120 if not mobile else 100
    b = [f'<rect width="{w}" height="2000" fill="{P["niebla"]}"/>'] + topbar(w, user=None if mobile else "Rosa")
    b += card(x0, top, cw, ch) + [group("guardar-finca", c, x0, top)]
    return frame((w, top + ch + 60 if mobile else max(900, top + ch + 60)), b, P["niebla"])


SCREENS = {
    "finca-08-temporal-escritorio": temporal_desktop,
    "finca-08-temporal-movil": temporal_mobile,
    "finca-08-temporal-error-movil": lambda: temporal_mobile(error=True),
    "cuenta-07-guardar-finca-escritorio": save_temporal,
    "cuenta-07-guardar-finca-movil": lambda: save_temporal(mobile=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
    print("por mes", TOTALS)
