"""Pantalla final «Lote · agua» (D3, tanda 7c, HU-145). Escritorio y móvil.

El plan de agua del lote: por cada cultivo en curso y cada mes, el déficit estimado (ET0 × Kc menos lluvia efectiva)
y el volumen en m³ según su parte del área, para un año normal o un año seco. Total del lote y total de la zona
(todos los lotes del usuario en el municipio). POST /water-plans con las temporadas en curso y su `area_ha`.
Todo es una estimación con el clima de la zona, se muestra en rangos y se pide verificar la humedad en campo (R10).
Rediseño, tanda 7: el balance usa la textura del suelo de la zona (cuánta agua guarda entre lluvias; POST /water-plans no
recibe `lot_id`) y el lote dice si tiene riego. Sin riego, el déficit no se llama «riego probable»: «pasaría sed».
Los nombres y las cifras son de muestra.

    python design/pantallas/agua.py     # escribe svg/finca-05-agua-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from calendario import tag, wrap_lines  # noqa: E402
from finca import drop, lot_header, lot_tabs  # noqa: E402
from ui import BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, card, chamfer, frame, group, link, paragraph, poly, text, topbar  # noqa: E402

MONTHS = ("Ago", "Sep", "Oct", "Nov", "Dic", "Ene")
TODAY = 2  # octubre
IRRIGATED = False  # El Alto no tiene riego (finca.py)
TEXTURE = "franco arcillosa"  # suelo de la zona (SoilGrids), estimación
NEED = "pasaría sed" if not IRRIGATED else "riego probable"
# cultivo, área (ha), meses en que está en el lote, déficit en mm por mes (mín, máx) en un año normal
CROPS = (
    ("Papa", 1.26, (0, 4), {2: (10, 22), 4: (18, 30)}),
    ("Haba", 0.42, (1, 5), {4: (12, 24), 5: (20, 34)}),
    ("Cebolla", 0.42, (0, 5), {2: (8, 18), 4: (15, 26), 5: (22, 36)}),
)


def m3(mm, ha):
    """Milímetros sobre un área a metros cúbicos: 1 mm en 1 ha son 10 m³."""
    return round(mm * 10 * ha)


def fmt(n):
    return f"{n:,}".replace(",", ".")


def totals():
    out = []
    for m in range(len(MONTHS)):
        lo = sum(m3(d[m][0], ha) for _, ha, _, d in CROPS if m in d)
        hi = sum(m3(d[m][1], ha) for _, ha, _, d in CROPS if m in d)
        out.append((lo, hi))
    return out


TOTALS = totals()
SEASON = (sum(t[0] for t in TOTALS), sum(t[1] for t in TOTALS))
ZONE = (SEASON[0] + 870, SEASON[1] + 1570)  # con La Vega y El Bajo (muestra)


def estimate_banner(x, y, w, mobile=False):
    lines = (["Estimación con el clima de la zona, no una", "medición de su lote. En los meses marcados", "la lluvia no alcanza: el cultivo pasaría sed.", "Verifique la humedad del suelo en campo."] if mobile else
             ["Estimación con el clima de la zona, no una medición de su lote. En los meses marcados la lluvia no alcanza: el cultivo", "pasaría sed. Verifique la humedad del suelo en campo."])
    h = 28 + len(lines) * 22 + 10
    body = [poly(chamfer(0, 0, w, h, 12), "#E6F0F5", D["cielo"], 2)] + drop(30, h / 2, 1.6)
    body += paragraph(60, 30, lines, 16, 22, weight=700)
    return [group("rotulo-de-estimacion", body, x, y)], h


def lot_strip(x, y, w, mobile=False):
    """Lo del lote que cambia la cuenta: si tiene riego y la textura del suelo de la zona."""
    h = 132 if mobile else 76
    body = [poly(chamfer(0, 0, w, h, 12), WHITE, BORDE, 1.5)]
    body += [text(20, 30, "Riego del lote", 13, fill=SEC), text(20, 54, "Sin riego" if not IRRIGATED else "Con riego", 17, 700)]
    body += link(150 if not mobile else w - 20, 30, "Cambiar", 14, anchor="start" if not mobile else "end")
    tx, ty = (w / 2 - 80, 0) if not mobile else (0, 62)
    body += [f'<rect x="{tx + 20}" y="{ty + 12}" width="1.5" height="{52}" fill="{BORDE}"/>'] if not mobile else [f'<rect x="20" y="{ty}" width="{w - 40}" height="1.5" fill="{BORDE}"/>']
    sx = tx + (40 if not mobile else 20)
    body += [text(sx, ty + 30, "Textura del suelo de la zona · estimación", 13, fill=SEC), text(sx, ty + 54, f"{TEXTURE[0].upper() + TEXTURE[1:]}: guarda agua entre lluvias" if not mobile else TEXTURE[0].upper() + TEXTURE[1:], 17, 700)]
    body += link(w - 20, ty + 30, "Ver suelo", 14, anchor="end")
    return [group("riego-y-suelo", body, x, y)], h


def year_toggle(x, y, w=320):
    """Año normal o año seco: los dos vienen en la respuesta del plan de agua."""
    half = w / 2
    out = [poly(chamfer(0, 0, w, 44, 10), WHITE, BORDE, 1.5), poly(chamfer(3, 3, half - 3, 38, 8), P["noche"]),
           text(half / 2, 28, "Año normal", 16, 700, WHITE, anchor="middle"), text(half * 1.5, 28, "Año seco", 16, 700, anchor="middle")]
    return [group("tipo-de-ano", out, x, y)]


def plan_table(x, y, w):
    """Una fila por cultivo y una columna por mes. Cada celda con déficit: milímetros y metros cúbicos, en rango."""
    lab = 210
    cw = (w - lab - 16) / len(MONTHS)
    col = lambda m: lab + m * cw  # noqa: E731
    rh, top = 96, 62
    h = top + len(CROPS) * rh + 110
    out = [poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE)]
    out.append(f'<rect x="{col(TODAY):.1f}" y="8" width="{cw:.1f}" height="{h - 16}" fill="{P["niebla"]}" fill-opacity="0.7"/>')
    for m, name in enumerate(MONTHS):
        cx = col(m) + cw / 2
        out.append(text(cx, 36, name + (" 2027" if name == "Ene" else ""), 17, 700 if m == TODAY else 400, anchor="middle"))
        if m == TODAY:
            out += tag(cx, 40, "Hoy", P["noche"])
        if m:
            out.append(f'<rect x="{col(m):.1f}" y="52" width="1" height="{h - 68}" fill="{BORDE}" fill-opacity="0.6"/>')
    for i, (name, ha, (s0, s1), deficit) in enumerate(CROPS):
        ry = top + i * rh
        out.append(f'<rect x="16" y="{ry - 4}" width="{w - 32}" height="1" fill="{BORDE}"/>')
        out += [text(20, ry + 38, name, 18, 700), text(20, ry + 60, f"{ha:.2f}".replace(".", ",") + " ha", 14, fill=SEC)]
        for m in range(len(MONTHS)):
            cx = col(m) + cw / 2
            if not s0 <= m <= s1:
                out.append(f'<rect x="{cx - 7:.1f}" y="{ry + 42}" width="14" height="3" fill="{BORDE}"/>')
            elif m in deficit:
                lo, hi = deficit[m]
                out.append(poly(chamfer(col(m) + 8, ry + 6, cw - 16, rh - 18, 8), "#E6F0F5", D["cielo"], 1.5))
                out += drop(col(m) + 30, ry + 32, 1.3)
                out += [text(col(m) + 50, ry + 34, f"{lo} a {hi} mm", 15, 700), text(col(m) + 50, ry + 56, f"{fmt(m3(lo, ha))} a {fmt(m3(hi, ha))} m³", 14),
                        text(col(m) + 50, ry + 72, NEED, 11, 700 if not IRRIGATED else 400, D["cielo"] if not IRRIGATED else SEC)]
            else:
                out += [f'<circle cx="{cx - 34:.1f}" cy="{ry + 40}" r="8" fill="none" stroke="{BORDE}" stroke-width="2.5"/>', text(cx - 18, ry + 45, "La lluvia alcanza", 13, fill=SEC)]
    # total del lote: barras con rango
    ty = top + len(CROPS) * rh
    out.append(f'<rect x="16" y="{ty - 4}" width="{w - 32}" height="2" fill="{P["noche"]}"/>')
    out += [text(20, ty + 38, "Agua que faltaría" if not IRRIGATED else "Total del lote", 18, 700), text(20, ty + 60, "en el lote · m³ en el mes", 13, fill=SEC)]
    vmax = max(t[1] for t in TOTALS) or 1
    pid = "rayado-agua"
    out.append(f'<defs><pattern id="{pid}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="{P["cielo"]}" fill-opacity="0.35"/>'
               f'<rect width="3" height="8" fill="{D["cielo"]}" fill-opacity="0.6"/></pattern></defs>')
    for m, (lo, hi) in enumerate(TOTALS):
        cx = col(m) + cw / 2
        if hi == 0:
            out.append(text(cx, ty + 50, "0", 15, fill=SEC, anchor="middle"))
            continue
        bw = cw - 40
        out.append(poly(chamfer(col(m) + 20, ty + 14, bw * hi / vmax, 22, 3), f"url(#{pid})", D["cielo"], 1.5))
        out.append(poly(chamfer(col(m) + 20, ty + 14, bw * lo / vmax, 22, 3), P["cielo"], D["cielo"], 1.5))
        out.append(text(cx, ty + 62, f"{fmt(lo)} a {fmt(hi)} m³", 15, 700, anchor="middle"))
    out += [poly(chamfer(lab, ty + 78, 22, 14, 2), P["cielo"], D["cielo"], 1.5), text(lab + 30, ty + 90, "mínimo estimado", 12, fill=SEC),
            poly(chamfer(lab + 150, ty + 78, 22, 14, 2), f"url(#{pid})", D["cielo"], 1.5), text(lab + 180, ty + 90, "hasta el máximo estimado", 12, fill=SEC)]
    return [group("plan-de-agua", out, x, y)], h


def summary_cards(x, y, w, mobile=False):
    n = 3 if not mobile else 1
    cw = (w - 24 * (n - 1)) / n
    data = (("AGUA QUE FALTARÍA EN LA TEMPORADA", f"{fmt(SEASON[0])} a {fmt(SEASON[1])} m³", ["De agosto a enero, para papa, haba y cebolla.", "Un tanque de 1.000 litros es 1 m³."], None),
            ("TOTAL DE SUS LOTES EN SAMACÁ", f"{fmt(ZONE[0])} a {fmt(ZONE[1])} m³", ["El Alto, La Vega y El Bajo, en la misma temporada."], "Ver mis lotes"),
            ("MES MÁS SECO PARA SUS CULTIVOS", "Diciembre", ["Los tres cultivos piden agua a la vez.", "La papa está en llenado."], "Ver diciembre en el calendario"))
    out, h = [], 190
    for i, (title, big, lines, lk) in enumerate(data):
        cx, cy = (x + i * (cw + 24), y) if not mobile else (x, y + i * (h + 16))
        body = [text(24, 40, title, 13, 700, SEC), text(24, 78, big, 26, 600, font=FONT_TITLE)]
        body += paragraph(24, 106, [ln for line in lines for ln in wrap_lines([line], int((cw - 48) / 7.2))], 14, 20, fill=SEC)
        if lk:
            body += link(24, h - 22, lk, 14)
        out += card(cx, cy, cw, h, f"resumen-{i + 1}") + [group(f"resumen-{i + 1}-texto", body, cx, cy)]
    return out, h if not mobile else 3 * h + 32


def how_card(x, y, w):
    n = int((w - 48) / 7.2)
    lines = wrap_lines(["Para cada mes: lo que el cultivo necesita según su etapa (ET0 × Kc) menos la lluvia que suele caer. Si falta agua, hay déficit: sin riego, el cultivo pasaría sed.",
                        "El suelo guarda agua entre una lluvia y otra según su textura: uno arenoso se seca antes que uno arcilloso. Se usa la textura estimada del suelo de la zona; sin ella, se calcula sin esa reserva y se dice.",
                        "El rango va de un mes más lluvioso a uno más seco dentro de lo normal. «Año seco» repite la cuenta con los años más secos del histórico.",
                        "No usa el clima de hoy ni un pronóstico."], n)
    body = [text(24, 40, "CÓMO SE CALCULA", 14, 700, SEC)] + paragraph(24, 68, lines, 14, 21)
    h = 68 + len(lines) * 21 + 44
    body += link(24, h - 22, "¿De dónde salen estos datos?", 15)
    return card(x, y, w, h, "tarjeta-como") + [group("como-se-calcula", body, x, y)], h


def desktop():
    w = 1440
    b = [f'<rect width="{w}" height="2600" fill="{P["niebla"]}"/>']
    b += topbar(w, active="Mi finca", user="Rosa")
    b += lot_header(48, 140)
    b += lot_tabs(48, 212, "Agua")
    b += [text(48, 312, "Plan de agua del lote", 34, 600, font=FONT_TITLE)]
    b += year_toggle(w - 48 - 320, 282)
    ban, bh = estimate_banner(48, 336, w - 96)
    b += ban
    y = 336 + bh + 16
    st, sth = lot_strip(48, y, w - 96)
    b += st
    y += sth + 24
    t, th = plan_table(48, y, w - 96)
    b += t
    y += th + 32
    s, sh = summary_cards(48, y, w - 96)
    b += s
    y += sh + 32
    hc, hh = how_card(48, y, w - 96)
    b += hc
    return frame((w, y + hh + 60), b, P["niebla"])


def month_card(x, y, w, m):
    lo, hi = TOTALS[m]
    rows = [(name, ha, deficit.get(m)) for name, ha, (s0, s1), deficit in CROPS if s0 <= m <= s1]
    h = 62 + len(rows) * 40 + (44 if hi else 8)
    out = [poly(chamfer(0, 0, w, h, 12), WHITE, D["cielo"] if hi else BORDE, 2 if hi else 1.2)]
    out.append(text(16, 34, MONTHS[m] + (" 2027" if MONTHS[m] == "Ene" else ""), 19, 700))
    if m == TODAY:
        out += tag(80, 19, "Hoy", P["noche"])
    if not hi:
        out.append(text(w - 16, 34, "La lluvia alcanza", 14, fill=SEC, anchor="end"))
    for i, (name, ha, d) in enumerate(rows):
        ry = 52 + i * 40
        out.append(text(16, ry + 20, name, 15, 700 if d else 400))
        if d:
            out += drop(100, ry + 14, 1.0) + [text(116, ry + 20, f"{d[0]} a {d[1]} mm", 14, 700), text(w - 16, ry + 20, f"{fmt(m3(d[0], ha))} a {fmt(m3(d[1], ha))} m³", 14, anchor="end")]
            out.append(text(116, ry + 36, NEED, 11, 700, D["cielo"]))
        else:
            out.append(text(116, ry + 20, "la lluvia alcanza", 13, fill=SEC))
    if hi:
        ty = 52 + len(rows) * 40 + 6
        out += [f'<rect x="16" y="{ty}" width="{w - 32}" height="1.5" fill="{P["noche"]}"/>', text(16, ty + 26, "Faltaría en el lote", 15, 700),
                text(w - 16, ty + 26, f"{fmt(lo)} a {fmt(hi)} m³", 16, 700, anchor="end")]
    return [group(f"mes-{MONTHS[m].lower()}", out, x, y)], h


def mobile():
    w = MOBILE[0]
    pad, fw = 16, w - 32
    b = topbar(w) + lot_header(pad, 118, mobile=True)
    tabs = lot_tabs(-330, 0, "Agua")
    b.append(f'<defs><clipPath id="recorte-pestanas-agua"><rect x="0" y="200" width="{w}" height="60"/></clipPath></defs>'
             f'<g clip-path="url(#recorte-pestanas-agua)"><g transform="translate({pad} 210)">{"".join(tabs)}</g></g>')
    b.append(text(pad, 302, "Plan de agua del lote", 25, 600, font=FONT_TITLE))
    b += year_toggle(pad, 320, fw)
    ban, bh = estimate_banner(pad, 380, fw, True)
    b += ban
    y = 380 + bh + 14
    st, sth = lot_strip(pad, y, fw, True)
    b += st
    y += sth + 20
    for m in range(len(MONTHS)):
        mc, mh = month_card(pad, y, fw, m)
        b += mc
        y += mh + 10
    y += 14
    s, sh = summary_cards(pad, y, fw, True)
    b += s
    y += sh + 20
    hc, hh = how_card(pad, y, fw)
    b += hc
    return frame((w, y + hh + 50), b, P["niebla"])


SCREENS = {"finca-05-agua-escritorio": desktop, "finca-05-agua-movil": mobile}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
    print("temporada", SEASON, "zona", ZONE)
