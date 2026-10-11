"""Pantalla final «Lote · calendario» (D1b, tanda 7b, HU-180). Escritorio y móvil, con sus dos lecturas.

«Mi cultivo»: para lo que ya está sembrado. Los meses de la siembra a la cosecha estimada con las decisiones del ciclo:
la etapa del cultivo, las heladas con «Vigile» cuando la etapa es sensible, y el riego probable (plan de agua).
En P1 se suman abonar, labores y cosecha, gota y vender; aquí van rotuladas «P1» para el equipo y en la app solo
aparecen cuando su dato existe. Datos: POST /calendar con `sowing_date` y POST /water-plans.

«Planear una siembra»: para la parte libre, otro cultivo o sin cuenta. Doce meses con qué tan bueno es sembrar y el
riesgo de helada (POST /calendar sin `sowing_date`).

Cada nivel va con forma y texto, no solo color (R1). Es el histórico de la zona, no un pronóstico; lo de después de
hoy y el riego son estimaciones y se dice (R10). Tocar un mes abre su detalle con las razones (R5).
Los nombres y las cifras son de muestra.

    python design/pantallas/calendario.py     # escribe svg/finca-03-calendario-*.svg y svg/consulta-04-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from build_kit_svg import STATUS, icon  # noqa: E402
from finca import STAGE_TONES, drop, lot_header, lot_tabs  # noqa: E402
from ui import (BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, card, chamfer, field, frame, group, link, paragraph, poly, text,  # noqa: E402
                topbar, width_of)

MONTHS = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
LABEL = {"favorable": "Favorable", "moderado": "Moderado", "desfavorable": "Desfavorable"}
SHORT = {"favorable": "Favorable", "moderado": "Moderado", "desfavorable": "Desfav."}
FAV, MOD, UNF = "favorable", "moderado", "desfavorable"

# ----- Planear una siembra: papa en Samacá (muestra), de /calendar sin sowing_date -----
SOWING = (UNF, MOD, FAV, FAV, MOD, UNF, MOD, MOD, FAV, MOD, UNF, UNF)
BEST = (2, 3, 8)  # best_sowing_months: marzo, abril y septiembre
FROST = (22, 16, 5, 1, 0, 1, 3, 4, 2, 1, 2, 12)  # frost_freq_pct
TODAY, SELECTED = 9, 11  # octubre es hoy; el mes abierto es diciembre

# ----- Mi cultivo: la papa de El Alto, sembrada el 2 de agosto (muestra), de /calendar con sowing_date -----
# mes, etapa, tono, ¿estimada?, helada %, etapa sensible, riego probable, y en P1: abonar, labores, gota, vender
CYCLE = (
    dict(m=7, stage="Siembra y emergencia", tone=1, est=False, frost=4, sens=True, water=False,
         fert=(FAV, "Pocos aguaceros"), work=(FAV, "Suele haber días secos"), blight=(FAV, "Poco favorable"), sell=(FAV, "Suele estar 6 % arriba")),
    dict(m=8, stage="Desarrollo", tone=2, est=False, frost=2, sens=True, water=False,
         fert=(MOD, "Algunos aguaceros"), work=(MOD, "Pocos días secos"), blight=(MOD, "Algo favorable"), sell=(FAV, "Suele estar 2 % arriba")),
    dict(m=9, stage="Floración", tone=3, est=True, frost=1, sens=True, water=True,
         fert=(FAV, "Pocos aguaceros"), work=(FAV, "Suele haber días secos"), blight=(FAV, "Poco favorable"), sell=(MOD, "Suele estar 3 % abajo")),
    dict(m=10, stage="Llenado", tone=4, est=True, frost=2, sens=True, water=False,
         fert=(UNF, "Aguaceros frecuentes"), work=(UNF, "Casi sin días secos"), blight=(UNF, "Muy favorable: vigile"), sell=(MOD, "Suele estar 7 % abajo")),
    dict(m=11, stage="Llenado y cosecha", tone=5, est=True, frost=12, sens=True, water=True,
         fert=(FAV, "Pocos aguaceros"), work=(FAV, "Días secos para cosechar"), blight=(MOD, "Algo favorable"), sell=(UNF, "Suele estar 9 % abajo")),
)
P1_ROWS = (("fert", "Abonar", "Aguaceros que lavan", "el abono; no la dosis"), ("work", "Labores y cosecha", "Días secos seguidos", "para trabajar"),
           ("blight", "Gota", "Clima que favorece", "la gota de la papa"), ("sell", "Vender", "Precio del mes frente", "al promedio del año"))


def frost_level(v):
    return UNF if v >= 15 else (MOD if v >= 5 else FAV)


def level_mark(x, y, level, size=22):
    """El nivel como forma y color: octágono, triángulo o cuadrado."""
    st = STATUS[level]
    return [poly(chamfer(x - size / 2 - 5, y - size / 2 - 5, size + 10, size + 10, 6), st["fill"], st["stroke"], 2)] + icon(st["icon"], x - size / 2, y - size / 2, st["ink"], size)


def tag(x, y, label, fill, ink=WHITE, stroke=None, size=11):
    w = width_of(label, size, True) + 14
    return [poly(chamfer(x - w / 2, y, w, 18, 4), fill, stroke, 1.5 if stroke else 0), text(x, y + 13, label, size, 700, ink, anchor="middle")]


def mode_toggle(x, y, mine=True, w=420):
    """Las dos lecturas del calendario."""
    half = w / 2
    out = [poly(chamfer(0, 0, w, 44, 10), WHITE, BORDE, 1.5), poly(chamfer(3 if mine else half, 3, half - 3, 38, 8), P["noche"])]
    out.append(text(half / 2, 28, "Mi cultivo", 16, 700, WHITE if mine else P["noche"], anchor="middle"))
    out.append(text(half * 1.5, 28, "Planear una siembra", 16, 700, P["noche"] if mine else WHITE, anchor="middle"))
    return [group("lectura", out, x, y)]


def crop_chips(x, y, items):
    """Los cultivos del lote y «Otro cultivo» para planear cualquiera del catálogo."""
    out, cx = [], x
    for name, on in items:
        w = width_of(name, 16, True) + 32
        out.append(poly(chamfer(cx, y, w, 40, 9), D["oliva"] if on else WHITE, None if on else BORDE, 0 if on else 1.5))
        out.append(text(cx + w / 2, y + 26, name, 16, 700, WHITE if on else P["noche"], anchor="middle"))
        cx += w + 8
    w = 170
    out += [poly(chamfer(cx, y, w, 40, 9), WHITE, BORDE, 1.5), text(cx + 16, y + 26, "Otro cultivo", 16), text(cx + w - 16, y + 26, "▾", 15, 700, D["oliva"], anchor="end")]
    return [group("elegir-cultivo", out)], cx + w


def banner(x, y, w, title, big, note=None, lines=None):
    h = 64 if not lines else 84
    body = [poly(chamfer(0, 0, w, h, 12), "#E9F2D8", D["oliva"], 2)] + icon("octagon", 18, 20, D["oliva"], 24)
    body += [text(54, 28 if not lines else 30, title, 15, 700), text(54, 52 if not lines else 54, big, 20 if not lines else 18, 600, font=FONT_TITLE)]
    if lines:
        body.append(text(54, 74, lines, 13, fill=SEC))
    if note:
        body.append(text(w - 20, 40, note, 14, fill=SEC, anchor="end"))
    return [group("resumen", body, x, y)]


# ---------- Mi cultivo: de la siembra a la cosecha ----------

def cycle_grid(x, y, w):
    """Los meses del ciclo en columnas y una fila por decisión. Cada columna se toca para abrir su detalle."""
    lab, after = 200, 150
    cw = (w - lab - after - 16) / len(CYCLE)
    col = lambda i: lab + i * cw  # noqa: E731
    r = dict(stage=62, frost=150, water=252, p1=346, fert=382, work=452, blight=522, sell=592)
    h = 672
    out = [poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE)]
    ti = next(i for i, c in enumerate(CYCLE) if c["m"] == TODAY)
    si = next(i for i, c in enumerate(CYCLE) if c["m"] == SELECTED)
    out.append(f'<rect x="{col(ti):.1f}" y="8" width="{cw:.1f}" height="{h - 16}" fill="{P["niebla"]}" fill-opacity="0.7"/>')
    out.append(poly(chamfer(col(si) + 2, 6, cw - 4, h - 12, 10), "#FFF6EA", P["calabaza"], 2.5))
    for i in range(1, len(CYCLE) + 1):
        out.append(f'<rect x="{col(i):.1f}" y="52" width="1" height="{h - 68}" fill="{BORDE}" fill-opacity="0.6"/>')
    for key in ("stage", "frost", "water", "fert", "work", "blight", "sell"):
        out.append(f'<rect x="16" y="{r[key] - 6}" width="{w - 32 - after}" height="1" fill="{BORDE}"/>')
    # encabezado
    for i, c in enumerate(CYCLE):
        cx = col(i) + cw / 2
        out.append(text(cx, 36, MONTHS[c["m"]], 18, 700 if i in (ti, si) else 400, anchor="middle"))
        if i == ti:
            out += tag(cx, 40, "Hoy", P["noche"])
    # etapa del cultivo
    out += [text(20, r["stage"] + 30, "Etapa de la papa", 16, 700), text(20, r["stage"] + 50, "Cómo va y qué viene", 13, fill=SEC)]
    pid = "rayado-calendario"
    out.append(f'<defs><pattern id="{pid}" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="4" height="10" fill="{WHITE}" fill-opacity="0.6"/></pattern></defs>')
    for i, c in enumerate(CYCLE):
        bx = col(i) + 6
        out.append(f'<rect x="{bx:.1f}" y="{r["stage"] + 8}" width="{cw - 12:.1f}" height="34" fill="{STAGE_TONES[c["tone"]]}"/>')
        if c["est"]:
            out.append(f'<rect x="{bx:.1f}" y="{r["stage"] + 8}" width="{cw - 12:.1f}" height="34" fill="url(#{pid})"/>')
        out.append(text(col(i) + cw / 2, r["stage"] + 30, c["stage"], 14, 700, anchor="middle"))
        if i < len(CYCLE) - 1:
            out.append(text(col(i) + cw / 2, r["stage"] + 60, "Estimada con un año normal" if c["est"] else "Con la temperatura real de la zona", 12, fill=SEC, anchor="middle"))
    hx = col(len(CYCLE) - 1) + cw * 0.9
    out += [f'<rect x="{hx - 1.5:.1f}" y="{r["stage"] + 2}" width="3" height="46" fill="{P["noche"]}"/>']
    out += tag(col(len(CYCLE) - 1) + cw / 2, r["stage"] + 48, "Cosecha estimada: 28 dic", P["noche"])
    # heladas
    out += [text(20, r["frost"] + 30, "Heladas", 16, 700), text(20, r["frost"] + 50, "% de años con helada", 13, fill=SEC), text(20, r["frost"] + 66, "y si toca vigilar", 13, fill=SEC)]
    for i, c in enumerate(CYCLE):
        cx = col(i) + cw / 2
        lv = frost_level(c["frost"])
        watch = c["sens"] and lv != FAV
        out += level_mark(cx - 44, r["frost"] + 26, lv, 18)
        out += [text(cx - 22, r["frost"] + 24, f"{c['frost']} %", 16, 700), text(cx - 22, r["frost"] + 42, LABEL[lv], 13, fill=SEC)]
        if watch:
            out += tag(cx, r["frost"] + 58, "Vigile: etapa sensible", P["calabaza"], P["noche"])
        elif c["sens"]:
            out.append(text(cx, r["frost"] + 71, "Etapa sensible, riesgo bajo", 12, fill=SEC, anchor="middle"))
    # riego probable
    out += [text(20, r["water"] + 30, "Riego probable", 16, 700), text(20, r["water"] + 50, "Estimación del plan", 13, fill=SEC), text(20, r["water"] + 66, "de agua", 13, fill=SEC)]
    for i, c in enumerate(CYCLE):
        cx = col(i) + cw / 2
        if c["water"]:
            out += drop(cx - 40, r["water"] + 30, 1.5) + [text(cx - 20, r["water"] + 28, "Probable", 15, 700), text(cx - 20, r["water"] + 46, "estimación", 12, fill=SEC)]
        else:
            out += [f'<circle cx="{cx - 40:.1f}" cy="{r["water"] + 32}" r="9" fill="none" stroke="{BORDE}" stroke-width="2.5"/>', text(cx - 20, r["water"] + 37, "No", 15, fill=SEC)]
    # filas de P1
    out += tag(94, r["p1"] - 2, "P1 · próximas filas", WHITE, D["cielo"], D["cielo"], 12)
    out.append(text(176, r["p1"] + 12, "Solo aparecen cuando su dato existe (HU-046 y señal de mercado)", 12, fill=SEC))
    for key, title, s1, s2 in P1_ROWS:
        ry = r[key]
        out += [text(20, ry + 24, title, 15, 700), text(20, ry + 42, s1, 12, fill=SEC), text(20, ry + 56, s2, 12, fill=SEC)]
        for i, c in enumerate(CYCLE):
            lv, label = c[key]
            cx = col(i) + 16
            out += level_mark(cx + 12, ry + 28, lv, 14) + [text(cx + 34, ry + 33, label, 13)]
    # después de la cosecha
    ax = col(len(CYCLE)) + 14
    out += [text(ax, 36, "Después", 16, fill=SEC), text(ax, r["stage"] + 22, "Con la cosecha", 13, fill=SEC), text(ax, r["stage"] + 40, "queda la parte libre", 13, fill=SEC)]
    out += link(ax, r["stage"] + 70, "Próxima siembra", 15)
    return [group("calendario-mi-cultivo", out, x, y)], h


def reason(x, y, title, level, lines, glyph=None, level_text=None):
    out = drop(x + 16, y + 16, 1.5) if glyph == "riego" else (level_mark(x + 16, y + 16, level, 18) if level else
                                                               [poly(chamfer(x + 2, y + 2, 28, 28, 6), STAGE_TONES[5], P["noche"], 1.5)])
    out.append(text(x + 46, y + 12, title, 16, 700))
    out.append(text(x + 46, y + 32, level_text or LABEL[level], 14, 700, SEC))
    out += paragraph(x + 46, y + 56, lines, 15, 22)
    return out, 56 + len(lines) * 22 + 14


def wrap_lines(lines, n):
    out = []
    for ln in lines:
        cur = ""
        for word in ln.split(" "):
            if len(cur) + len(word) + 1 > n and cur:
                out.append(cur)
                cur = word
            else:
                cur = (cur + " " + word).strip()
        out.append(cur)
    return out


def month_detail(x, y, w, mode="mine", foot=True):
    """Detalle del mes elegido, con las razones que evaluó el motor (R5)."""
    n = int((w - 90) / 7.4)
    if mode == "mine":
        blocks = (("Etapa de la papa", None, ["Llenado del tubérculo y cosecha; se estima para el 28 de diciembre."], None, "Estimada con un año normal"),
                  ("Heladas", MOD, ["Heló en 12 de cada 100 diciembres del histórico (mínima menor que 2 °C).", "El follaje de la papa todavía es sensible en el llenado."], None, "Moderado · vigile"),
                  ("Riego de la papa", None, ["Déficit estimado de 18 a 30 mm en el mes, con el clima de la zona.", "Verifique la humedad del suelo en campo antes de regar."], "riego", "Probable · estimación"))
    else:
        blocks = (("Sembrar papa", UNF, ["La lluvia normal de diciembre a febrero no cubre la emergencia y el desarrollo.", "La floración caería en enero, el mes con más heladas."], None, None),
                  ("Heladas", MOD, ["Heló en 12 de cada 100 diciembres del histórico (mínima menor que 2 °C).", "Si siembra en diciembre, la floración de la papa caería en enero y febrero."], None, None))
    body = [text(24, 40, "MES ELEGIDO", 14, 700, SEC), text(24, 76, "Diciembre", 28, 600, font=FONT_TITLE)]
    yy = 104
    for title, level, lines, glyph, lt in blocks:
        rr, rh = reason(24, yy, title, level, wrap_lines(lines, n), glyph, lt)
        body += rr
        yy += rh + 8
    if mode == "mine":
        body += link(24, yy + 12, "Ver el plan de agua", 15)
    elif mode == "guest":
        body += paragraph(24, yy + 10, wrap_lines(["Con una cuenta y su lote, aquí también sigue el cultivo que ya sembró: su etapa, las heladas a vigilar y el riego probable."], n + 6), 14, 20, fill=SEC)
        yy += 44 if w > 500 else 64
        body += link(24, yy + 12, "Crear cuenta y guardar mi lote", 15)
    else:
        body += link(24, yy + 12, "Ver qué sembrar después en este lote", 15)
    h = yy + 40
    return card(x, y, w, h, "tarjeta-mes") + [group("detalle-del-mes", body, x, y)], h


def legend(x, y, w, h=None, mode="mine"):
    body = [text(24, 40, "CÓMO LEERLO", 14, 700, SEC)]
    yy = 66
    for lv, label in ((FAV, "Favorable: conviene"), (MOD, "Moderado: con cuidado"), (UNF, "Desfavorable: mejor no")):
        body += level_mark(40, yy + 10, lv, 16) + [text(68, yy + 16, label, 15)]
        yy += 38
    if mode == "mine":
        body += drop(40, yy + 10, 1.2) + [text(68, yy + 16, "Riego probable: estimación, no medición", 15)]
        yy += 38
    yy += 10
    n = int((w - 48) / 7.0)
    notes = wrap_lines(["Es el histórico de Samacá, no un pronóstico: dice qué ha pasado en cada mes, no qué va a pasar este año."], n) + [""] + \
        wrap_lines(["Helada: mínima menor que 2 °C, con la temperatura corregida por la altitud del municipio."], n)
    if mode == "mine":
        notes += [""] + wrap_lines(["Las etapas después de hoy se estiman con un año normal."], n)
    body += paragraph(24, yy, notes, 14, 21, fill=SEC)
    yy += len(notes) * 21 + 10
    body += link(24, yy, "¿De dónde salen estos datos?", 15)
    h = max(h or 0, yy + 28)
    return card(x, y, w, h, "tarjeta-leyenda") + [group("leyenda", body, x, y)], h


def lot_top(w, mine):
    b = [f'<rect width="{w}" height="2600" fill="{P["niebla"]}"/>']
    b += topbar(w, active="Mi finca", user="Rosa")
    b += lot_header(48, 140)
    b += lot_tabs(48, 212, "Calendario")
    b += mode_toggle(48, 280, mine)
    return b


def mine_desktop():
    w = 1440
    b = lot_top(w, True)
    chips, cx = crop_chips(500, 282, (("Papa", True), ("Haba", False), ("Cebolla", False)))
    b += chips
    b += banner(48, 344, w - 96, "Papa en El Alto · 1,26 ha · sembrada el 2 de agosto", "Va en floración; cosecha estimada el 28 de diciembre",
                "Este mes: riego probable · En diciembre: vigile las heladas")
    g, gh = cycle_grid(48, 432, w - 96)
    b += g
    y = 432 + gh + 32
    lw = 820
    d, dh = month_detail(48, y, lw, "mine")
    lg, lh = legend(48 + lw + 24, y, w - 96 - lw - 24, dh, "mine")
    b += d + lg
    return frame((w, y + max(dh, lh) + 60), b, P["niebla"])


# ---------- Planear una siembra: doce meses ----------

def plan_grid(x, y, w):
    lab = 176
    cw = (w - lab - 16) / 12
    col = lambda m: lab + m * cw  # noqa: E731
    r = dict(sow=58, frost=160)
    h = 284
    out = [poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE)]
    out.append(f'<rect x="{col(TODAY):.1f}" y="8" width="{cw:.1f}" height="{h - 16}" fill="{P["niebla"]}" fill-opacity="0.7"/>')
    out.append(poly(chamfer(col(SELECTED) + 2, 6, cw - 4, h - 12, 10), "#FFF6EA", P["calabaza"], 2.5))
    for m in range(1, 12):
        out.append(f'<rect x="{col(m):.1f}" y="52" width="1" height="{h - 68}" fill="{BORDE}" fill-opacity="0.6"/>')
    for key in ("sow", "frost"):
        out.append(f'<rect x="16" y="{r[key] - 6}" width="{w - 32}" height="1" fill="{BORDE}"/>')
    for m, name in enumerate(MONTHS):
        cx = col(m) + cw / 2
        out.append(text(cx, 36, name, 17, 700 if m in (TODAY, SELECTED) else 400, anchor="middle"))
        if m == TODAY:
            out += tag(cx, 40, "Hoy", P["noche"])
    out += [text(20, r["sow"] + 34, "Sembrar", 16, 700), text(20, r["sow"] + 54, "¿Conviene sembrar", 13, fill=SEC), text(20, r["sow"] + 70, "este mes?", 13, fill=SEC)]
    for m, lv in enumerate(SOWING):
        cx = col(m) + cw / 2
        out += level_mark(cx, r["sow"] + 30, lv)
        out.append(text(cx, r["sow"] + 64, SHORT[lv], 13, 700 if m in BEST else 400, anchor="middle"))
        if m in BEST:
            out += tag(cx, r["sow"] + 72, "Mejor mes", D["oliva"])
    out += [text(20, r["frost"] + 34, "Heladas", 16, 700), text(20, r["frost"] + 54, "% de años con", 13, fill=SEC), text(20, r["frost"] + 70, "helada en el mes", 13, fill=SEC)]
    for m, v in enumerate(FROST):
        cx = col(m) + cw / 2
        lv = frost_level(v)
        bh = max(3, 46 * v / 25)
        out.append(poly(chamfer(cx - 15, r["frost"] + 52 - bh, 30, bh, 2), STATUS[lv]["fill"], STATUS[lv]["stroke"], 1.5))
        out.append(text(cx, r["frost"] + 72, f"{v} %", 14, 700, anchor="middle"))
        out += [f'<g transform="translate({cx - 34:.1f} {r["frost"] + 80})">{"".join(icon(STATUS[lv]["icon"], 0, 0, STATUS[lv]["stroke"], 12))}</g>',
                text(cx + 6, r["frost"] + 91, SHORT[lv], 12, fill=SEC, anchor="middle")]
    return [group("calendario-planear", out, x, y)], h


def plan_desktop():
    """Con cuenta: planear la parte libre del lote (u otro cultivo)."""
    w = 1440
    b = lot_top(w, False)
    chips, cx = crop_chips(500, 282, (("Papa", True), ("Haba", False), ("Cebolla", False)))
    b += chips
    b += banner(48, 344, w - 96, "Mejores meses para sembrar papa en Samacá · parte libre de El Alto, 0,41 ha", "Marzo, abril y septiembre",
                "Según el histórico de la zona; no es pronóstico")
    g, gh = plan_grid(48, 432, w - 96)
    b += g
    y = 432 + gh + 32
    lw = 820
    d, dh = month_detail(48, y, lw, "plan")
    lg, lh = legend(48 + lw + 24, y, w - 96 - lw - 24, dh, "plan")
    b += d + lg
    return frame((w, y + max(dh, lh) + 60), b, P["niebla"])


def guest_desktop():
    """Sin cuenta, desde la consulta: solo «Planear una siembra». Se elige municipio y cultivo."""
    w = 1440
    b = [f'<rect width="{w}" height="2000" fill="{P["niebla"]}"/>']
    b += topbar(w, active="Consultar")
    b += link(48, 140, "‹ Volver al resultado", 16)
    b += [text(48, 190, "Calendario de la papa", 40, 600, font=FONT_TITLE), text(48, 222, "Samacá, Boyacá · histórico de la zona, no es pronóstico", 17, fill=SEC)]
    b += field(48, 262, 300, "Municipio", "Samacá, Boyacá", trailing="▾", name="elegir-municipio")
    b += field(372, 262, 240, "Cultivo", "Papa", trailing="▾", name="elegir-cultivo")
    b += banner(644, 270, w - 48 - 644, "Mejores meses para sembrar papa en Samacá", "Marzo, abril y septiembre", "Según el histórico de la zona")
    g, gh = plan_grid(48, 372, w - 96)
    b += g
    y = 372 + gh + 32
    lw = 820
    d, dh = month_detail(48, y, lw, "guest")
    lg, lh = legend(48 + lw + 24, y, w - 96 - lw - 24, dh, "guest")
    b += d + lg
    return frame((w, y + max(dh, lh) + 60), b, P["niebla"])


# ---------- Móvil ----------

def mobile_top(w, pad, mine, cid):
    b = topbar(w) + lot_header(pad, 118, mobile=True)
    tabs = lot_tabs(-98, 0, "Calendario")  # la pestaña activa queda a la vista al deslizar la fila
    b.append(f'<defs><clipPath id="{cid}"><rect x="0" y="200" width="{w}" height="60"/></clipPath></defs>'
             f'<g clip-path="url(#{cid})"><g transform="translate({pad} 210)">{"".join(tabs)}</g></g>')
    b += mode_toggle(pad, 276, mine, w - 2 * pad)
    b += field(pad, 350, w - 2 * pad, "Cultivo", "Papa · en el lote" if mine else "Papa · parte libre", trailing="▾", name="elegir-cultivo")
    return b


def cycle_month_card(x, y, w, c):
    """Un mes del ciclo en móvil: etapa, heladas y riego; en P1, las otras cuatro decisiones."""
    on, today = c["m"] == SELECTED, c["m"] == TODAY
    lv = frost_level(c["frost"])
    watch = c["sens"] and lv != FAV
    h = 236
    out = [poly(chamfer(0, 0, w, h, 12), "#FFF6EA" if on else WHITE, P["calabaza"] if on else BORDE, 2.5 if on else 1.2)]
    out.append(text(16, 34, MONTHS[c["m"]], 20, 700))
    if today:
        out += tag(78, 19, "Hoy", P["noche"])
    out.append(f'<rect x="{w - 196}" y="14" width="180" height="28" fill="{STAGE_TONES[c["tone"]]}"/>')
    out.append(text(w - 106, 33, c["stage"], 13, 700, anchor="middle"))
    out.append(text(w - 16, 58, "Estimada con un año normal" if c["est"] else "Con la temperatura real", 11, fill=SEC, anchor="end"))
    out += level_mark(30, 86, lv, 16) + [text(54, 84, f"Heladas: {c['frost']} % · {LABEL[lv].lower()}", 14, 700)]
    if watch:
        out += tag(54 + 62, 91, "Vigile: etapa sensible", P["calabaza"], P["noche"])
    elif c["sens"]:
        out.append(text(54, 102, "Etapa sensible, riesgo bajo", 12, fill=SEC))
    if c["water"]:
        out += drop(30, 126, 1.3) + [text(54, 131, "Riego probable · estimación", 14, 700)]
    else:
        out += [f'<circle cx="30" cy="126" r="8" fill="none" stroke="{BORDE}" stroke-width="2.5"/>', text(54, 131, "Sin riego probable", 14, fill=SEC)]
    out.append(f'<rect x="16" y="150" width="{w - 32}" height="1" fill="{BORDE}"/>')
    out += tag(32, 158, "P1", WHITE, D["cielo"], D["cielo"])
    half = (w - 32) / 2
    for k, (key, title, *_rest) in enumerate(P1_ROWS):
        px, py = 16 + (k % 2) * half, 186 + (k // 2) * 24
        out += level_mark(px + 8, py + 6, c[key][0], 10) + [text(px + 24, py + 10, title, 12, 700 if c[key][0] == UNF else 400)]
    return [group(f"mes-{MONTHS[c['m']].lower()}", out, x, y)], h


def mine_mobile():
    w = MOBILE[0]
    pad, fw = 16, w - 32
    b = mobile_top(w, pad, True, "recorte-pestanas-cal-1")
    b += banner(pad, 444, fw, "Papa en El Alto · 1,26 ha", "En floración · cosecha: 28 dic", lines="Sembrada el 2 de agosto")
    y = 548
    for c in CYCLE:
        row, rh = cycle_month_card(pad, y, fw, c)
        b += row
        y += rh + 10
    b += link(pad, y + 18, "Después de la cosecha: próxima siembra", 15)
    y += 50
    d, dh = month_detail(pad, y, fw, "mine")
    b += d
    y += dh + 24
    lg, lh = legend(pad, y, fw, mode="mine")
    b += lg
    return frame((w, y + lh + 50), b, P["niebla"])


def plan_month_row(x, y, w, m):
    on, today = m == SELECTED, m == TODAY
    h = 56
    out = [poly(chamfer(0, 0, w, h, 10), "#FFF6EA" if on else WHITE, P["calabaza"] if on else BORDE, 2.5 if on else 1.2)]
    out.append(text(14, 34, MONTHS[m], 17, 700))
    if today:
        out += tag(72, 19, "Hoy", P["noche"])
    out += level_mark(130, 28, SOWING[m], 16)
    out.append(text(152, 26 if m in BEST else 33, LABEL[SOWING[m]], 13, 700 if m in BEST else 400))
    if m in BEST:
        out.append(text(152, 43, "Mejor mes", 11, 700, D["oliva"]))
    lv = frost_level(FROST[m])
    out += [f'<g transform="translate({w - 78} 21)">{"".join(icon(STATUS[lv]["icon"], 0, 0, STATUS[lv]["stroke"], 14))}</g>', text(w - 16, 33, f"{FROST[m]} %", 14, 700, anchor="end")]
    return [group(f"mes-{MONTHS[m].lower()}", out, x, y)], h


def plan_mobile():
    w = MOBILE[0]
    pad, fw = 16, w - 32
    b = mobile_top(w, pad, False, "recorte-pestanas-cal-2")
    b += banner(pad, 444, fw, "Mejores meses para sembrar papa", "Marzo, abril y septiembre", lines="Según el histórico de Samacá")
    y = 556
    b += [text(pad + 14, y, "Mes", 12, 700, SEC), text(pad + 118, y, "Sembrar", 12, 700, SEC), text(w - pad - 16, y, "Heladas", 12, 700, SEC, anchor="end")]
    y += 12
    for m in range(12):
        row, rh = plan_month_row(pad, y, fw, m)
        b += row
        y += rh + 6
    y += 14
    d, dh = month_detail(pad, y, fw, "plan")
    b += d
    y += dh + 24
    lg, lh = legend(pad, y, fw, mode="plan")
    b += lg
    return frame((w, y + lh + 50), b, P["niebla"])


SCREENS = {
    "finca-03-calendario-mi-cultivo-escritorio": mine_desktop,
    "finca-03-calendario-mi-cultivo-movil": mine_mobile,
    "finca-03-calendario-planear-escritorio": plan_desktop,
    "finca-03-calendario-planear-movil": plan_mobile,
    "consulta-04-calendario-sin-cuenta-escritorio": guest_desktop,
}

if __name__ == "__main__":
    out = DIR / "svg"
    for old in ("finca-03-calendario-escritorio.svg", "finca-03-calendario-movil.svg"):  # nombres de la primera versión
        (out / old).unlink(missing_ok=True)
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
