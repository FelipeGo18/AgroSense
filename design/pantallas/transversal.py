"""Tanda 9 · Transversal: «¿Cómo funciona y de dónde sale esto?» (HU-122, HU-198), lámina de estados, menú en móvil
y «Reportar un problema» (P1, HU-170). Escritorio y móvil.

«Cómo funciona» lee GET /api/v1/version (versiones, región, pesos por defecto y fuentes con su cobertura). Los
estados son los de `specs/05-frontend.md`: cargando, vacío, sin cobertura, error con su código para soporte
(`request_id`), sin conexión y demasiados intentos (429). Reportar un problema usa POST/GET /api/v1/me/tickets (P1).
Los nombres y las cifras son de muestra.

    python design/pantallas/transversal.py     # escribe svg/transversal-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402
import muestra  # noqa: E402
from calendario import wrap_lines  # noqa: E402
from consulta import light  # noqa: E402
from senales import BAND, KEY_TO_KIND, kind  # noqa: E402
from ui import (BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, field, frame, group, link, logo, mascot,  # noqa: E402
                paragraph, poly, text, toggle, topbar, width_of)

# ---------- ¿Cómo funciona y de dónde sale esto? ----------

STEPS = (
    ("¿Se da en su zona?", "Primero miramos si el cultivo se da a la altitud de su municipio, según su ficha. Si no se da, se lo decimos y le sugerimos otros."),
    ("Seis señales de 0 a 100", "Para la fecha que eligió y lo que dura el cultivo: agua, heladas, calor, suelo, oferta y mercado. Cada una se compara con lo que ese cultivo necesita o aguanta."),
    ("Un semáforo por reglas", "Una señal mala y grave basta para el rojo: no se compensa con las buenas. Sin datos de agua u oferta no damos semáforo."),
    ("Sus prioridades", "Cada señal pesa de 0 a 5. Un riesgo grave de clima cuenta siempre. Si su luz y la de AgroSense difieren, le mostramos las dos."),
    ("Las mejores fechas", "Ordenamos las fechas del año por lo que más limita a cada una y, entre parecidas, por sus prioridades."),
)
SOURCES = (  # (señal o uso, fuente, institución, cobertura, licencia, se usa para)
    ("Clima", "NASA POWER", "NASA", "Mundial · celdas de unos 50 km", "Datos abiertos", "Agua, heladas y calor"),
    ("Suelo", "SoilGrids", "ISRIC", "Mundial · celdas de 250 m", "CC BY 4.0", "Suelo y agua que guarda"),
    ("Oferta", "Evaluaciones Agropecuarias (EVA)", "Ministerio de Agricultura", "Colombia", "Datos abiertos", "Oferta"),
    ("Oferta", "FAOSTAT", "FAO", "Mundial · por país", "CC BY 4.0", "Para contrastar"),
    ("Mercado", "SIPSA", "DANE", "Colombia", "Datos abiertos", "Mercado"),
    ("Límites", "Marco Geoestadístico", "DANE", "Colombia", "Datos abiertos", "Municipios"),
    ("Clima de ahora", "Open-Meteo", "Open-Meteo", "Mundial", "CC BY 4.0", "Solo la escena; nunca un resultado"),
)
NEVER = ("No pronostica el clima, el precio ni la cosecha: muestra lo que ha pasado en su zona.",
         "No usa el clima de hoy para calcular: solo para la escena.",
         "No rellena datos que faltan: si falta una fuente, lo dice.",
         "No decide por usted: la decisión es suya.")


def section_title(x, y, label, sub=None, mobile=False):
    out = [text(x, y, label, 26 if mobile else 32, 600, font=FONT_TITLE)]
    if sub:
        out += paragraph(x, y + 30, sub, 15, 22, fill=SEC)
    return out


def how(mobile=False):
    w = MOBILE[0] if mobile else 1440
    pad = 16 if mobile else 96
    cw = w - 2 * pad
    b = [f'<rect width="{w}" height="6000" fill="{P["niebla"]}"/>'] + topbar(w, active="Cómo funciona", user=None if mobile else "Rosa")
    b.append(text(pad, 150 if mobile else 180, "¿Cómo funciona?", 32 if mobile else 48, 600, font=FONT_TITLE))
    intro = (["AgroSense mira lo que ha pasado en su zona", "con datos abiertos y reglas que se pueden", "leer. No es un pronóstico: usted decide."] if mobile else
             ["AgroSense mira lo que ha pasado en su zona con datos abiertos y reglas que se pueden leer. No es un pronóstico: usted decide."])
    b += paragraph(pad, 190 if mobile else 224, intro, 16 if mobile else 18, 24)
    b += mascot(w - 120 if mobile else 1180, 70 if mobile else 100, 0.42 if mobile else 0.7, "guia")
    y = (190 if mobile else 224) + len(intro) * 24 + 40
    # 1. Cómo se decide
    b += section_title(pad, y + 20, "Cómo se decide", mobile=mobile)
    y += 50
    if mobile:
        for i, (title, body) in enumerate(STEPS):
            lines = wrap_lines([body], 40)
            h = 70 + len(lines) * 21
            c = [text(60, 38, title, 18, 700), poly(chamfer(16, 18, 30, 30, 6), P["calabaza"]), text(31, 39, str(i + 1), 16, 700, anchor="middle")]
            c += paragraph(20, 70, lines, 14, 21)
            b += card(pad, y, cw, h, f"paso-{i + 1}") + [group(f"paso-{i + 1}-texto", c, pad, y)]
            y += h + 14
    else:
        sw = (cw - 4 * 20) / 5
        for i, (title, body) in enumerate(STEPS):
            lines = wrap_lines([body], 30)
            c = [poly(chamfer(20, 20, 36, 36, 6), P["calabaza"]), text(38, 44, str(i + 1), 18, 700, anchor="middle"), text(20, 92, title, 18, 700)]
            c += paragraph(20, 120, lines, 14, 21)
            b += card(pad + i * (sw + 20), y, sw, 300, f"paso-{i + 1}") + [group(f"paso-{i + 1}-texto", c, pad + i * (sw + 20), y)]
        y += 320
    # bandas de la calificación y luces
    y += 20
    bw = cw if mobile else 560
    c = [text(20, 36, "De la nota al nivel", 18, 700)]
    for i, (lv, lo, hi, fill) in enumerate(BAND):
        bx = 20 + (bw - 40) * lo / 100
        ww = (bw - 40) * (hi - lo) / 100
        c += [f'<rect x="{bx:.1f}" y="56" width="{ww - 3:.1f}" height="34" fill="{fill}"/>', text(bx + ww / 2, 79, lv.capitalize(), 14, 700, anchor="middle"),
              text(bx, 112, str(lo), 12, fill=SEC)]
    c.append(text(bw - 20, 112, "100", 12, fill=SEC, anchor="end"))
    c += paragraph(20, 140, ["Una señal sin datos no tiene nota y no cuenta", "como riesgo."] if mobile else ["Una señal sin datos no tiene nota y no cuenta como riesgo."], 14, 21, fill=SEC)
    bh = 180 if mobile else 160
    b += card(pad, y, bw, bh, "bandas") + [group("bandas-texto", c, pad, y)]
    ly = y + bh + 20 if mobile else y
    lx = pad if mobile else pad + bw + 24
    lw = cw if mobile else cw - bw - 24
    lc = [text(20, 36, "Las luces", 18, 700)]
    for i, (key, label) in enumerate((("verde", "Sembrar"), ("amarillo", "Otra fecha o cultivo"), ("rojo", "Riesgo grave"), ("no-evaluable", "Faltan datos"))):
        cx = 20 + (i % 2 if mobile else i) * ((lw - 40) / (2 if mobile else 4))
        cy = 52 + (i // 2 if mobile else 0) * 84
        lc += light(key, cx, cy, 0.28) + [text(cx, cy + 66, label, 14, 700)]
    lh = 236 if mobile else 160
    b += card(lx, ly, lw, lh, "luces") + [group("luces-texto", lc, lx, ly)]
    y = ly + lh + 80
    # 2. Pesos por defecto
    b += section_title(pad, y, "Pesos por defecto", wrap_lines(["Cuánto pesa cada señal si usted no cambia sus prioridades. Son de muestra: los reales se fijan con su porqué y con evidencia."], 44 if mobile else 120), mobile)
    y += 30 + (3 if mobile else 1) * 22 + 24
    pc = []
    cols = 2 if mobile else 6
    pw = (cw - 40) / cols
    for i, k in enumerate(muestra.SIGNAL_ORDER):
        px, py = 20 + (i % cols) * pw, 20 + (i // cols) * 90
        pc += [f'<g transform="translate({px} {py}) scale(0.8)">{"".join(kind(KEY_TO_KIND[k], 0, 0))}</g>', text(px + 46, py + 20, muestra.SIGNAL_NAME[k], 16, 700),
               text(px + 46, py + 44, f"{muestra.DEFAULT_WEIGHTS[k]} de 5", 22, 600, font=FONT_TITLE)]
    rows = (len(muestra.SIGNAL_ORDER) + cols - 1) // cols
    ph = 20 + rows * 90
    pc += paragraph(20, ph + 6, ["Un riesgo grave de agua, heladas o calor", "cuenta siempre, aunque el peso sea 0."] if mobile else
                    ["Un riesgo grave de agua, heladas o calor cuenta siempre, aunque el peso sea 0."], 14, 21, fill=SEC)
    ph += (2 if mobile else 1) * 21 + 24
    b += card(pad, y, cw, ph, "pesos") + [group("pesos-texto", pc, pad, y)]
    y += ph + 80
    # 3. Fuentes y versión
    ver = f"Datos {muestra.DATASET} · Reglas {muestra.RULES} · Región: Colombia (supuesto hasta el enunciado del reto)"
    b += section_title(pad, y, "Fuentes y versión", wrap_lines([ver + ". Cada respuesta dice qué versión usó."], 44 if mobile else 120), mobile)
    y += 30 + (3 if mobile else 1) * 22 + 24
    if mobile:
        for kind_, name, inst, cov, lic, use in SOURCES:
            c = [text(16, 26, kind_.upper(), 12, 700, SEC), text(16, 50, name if len(name) < 28 else name[:26] + "…", 17, 700), text(16, 72, inst, 13, fill=SEC),
                 text(16, 94, cov, 13), text(16, 114, f"{lic} · {use}", 13, fill=SEC)]
            b += card(pad, y, cw, 132, "fuente") + [group("fuente-texto", c, pad, y)]
            y += 146
    else:
        cols_x = (24, 190, 520, 790, 1040)
        heads = ("Para", "Fuente", "Cobertura", "Licencia", "Se usa para")
        c = [text(x, 40, h_, 13, 700, SEC) for x, h_ in zip(cols_x, heads)]
        for i, (kind_, name, inst, cov, lic, use) in enumerate(SOURCES):
            ry = 64 + i * 56
            c.append(f'<rect x="24" y="{ry - 4}" width="{cw - 48}" height="1" fill="{BORDE}"/>')
            c += [text(cols_x[0], ry + 26, kind_, 15, 700), text(cols_x[1], ry + 20, name, 15, 700), text(cols_x[1], ry + 40, inst, 13, fill=SEC),
                  text(cols_x[2], ry + 26, cov, 14), text(cols_x[3], ry + 26, lic, 14), text(cols_x[4], ry + 26, use, 14, 700 if use == "Para contrastar" else 400)]
        th = 64 + len(SOURCES) * 56 + 20
        c += paragraph(24, th + 4, ["Las fuentes de un mismo indicador se muestran juntas y nunca se mezclan. Las cifras de muestra van rotuladas como ejemplo."], 14, fill=SEC)
        b += card(pad, y, cw, th + 40, "fuentes") + [group("fuentes-texto", c, pad, y)]
        y += th + 40
    y += 80
    # 4. Lo que no hace
    b += section_title(pad, y, "Lo que AgroSense no hace", mobile=mobile)
    y += 30
    nc = []
    ny = 30
    for row in NEVER:
        lines = wrap_lines([row], 40 if mobile else 100)
        nc += [poly(chamfer(20, ny - 14, 16, 16, 0), D["rojo"])] + paragraph(48, ny, lines, 15, 22)
        ny += len(lines) * 22 + 12
    b += card(pad, y, cw, ny + 8, "no-hace") + [group("no-hace-texto", nc, pad, y)]
    y += ny + 8 + 40
    b += link(pad, y, "Reportar un problema", 16)
    return ui.long_page((w, y + 60), b, P["niebla"])


# ---------- Lámina de estados ----------

def state_card(x, y, w, h, title, rows, mood, buttons=(), code=None, dashed=False, mobile=False):
    body = [poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE, D["cielo"] if dashed else None, 2 if dashed else 0, "6 5" if dashed else None)]
    body += [f'<g transform="translate({w - 92} 14) scale(0.26)">{"".join(mascot(0, 0, 1, mood))}</g>']
    body.append(text(24, 46, title, 21 if mobile else 22, 600, font=FONT_TITLE))
    rows = wrap_lines([" ".join(rows)], int((w - 140) / 7.4))  # sin pisar la mascota
    body += paragraph(24, 78, rows, 15, 22)
    by = 78 + len(rows) * 22 + 10
    if code:
        body += [poly(chamfer(24, by, w - 48, 36, 8), P["niebla"]), text(40, by + 24, f"Código para soporte: {code}", 14, 700)]
        by += 50
    bx = 24
    for i, (label, kind_) in enumerate(buttons):
        bw = (w - 48) if mobile else max(170, width_of(label, 18, True) + 56)
        if mobile:
            body += button(24, by + i * 64, bw, label, kind_, h=48)
        else:
            body += button(bx, by, bw, label, kind_, h=48)
            bx += bw + 16
    return [group("estado-" + title.split(" ")[0].lower(), body, x, y)]


def skeleton_card(x, y, w, h, mobile=False):
    """Cargando: la forma de lo que viene, sin datos inventados, y la mascota que gira."""
    body = [poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE)]
    body += [f'<g transform="translate({w - 110} 14) scale(0.32)">{"".join(mascot(0, 0, 1, "vuelo"))}</g>']
    body += [text(24, 46, "Cargando", 22, 600, font=FONT_TITLE), text(24, 76, "Calculando su ventana de siembra…", 15, fill=SEC)]
    for i, ww in enumerate((0.7, 0.5, 0.85, 0.6)):
        body.append(poly(chamfer(24, 100 + i * 30, (w - 48) * ww, 16, 4), P["niebla"]))
    body += [text(24, h - 22, "Si tarda más de 10 s: «Sigue calculando…»", 13, fill=SEC)]
    return [group("estado-cargando", body, x, y)]


STATES = (
    ("Todavía no tiene lotes", ["Dibuje su primer lote en el mapa para ver", "sus cultivos, su agua y su historial."], "guia", (("Agregar lote", "primary"),), None, True),
    ("Sin datos en su municipio", ["AgroSense cubre la región piloto. Puede", "consultar un municipio cercano que sí esté."], "reposo", (("Buscar otro municipio", "secondary"),), None, True),
    ("Algo falló de nuestro lado", ["No pudimos calcular. No es su culpa: vuelva", "a intentar en un momento."], "reposo", (("Reintentar", "primary"), ("Reportar", "secondary")), "9b1e-42c7", False),
    ("Sin conexión", ["Revise la señal. Lo que ya consultó sigue", "en pantalla; para calcular hace falta internet."], "reposo", (("Reintentar", "primary"),), None, False),
    ("Demasiados intentos", ["Por seguridad, espere 15 minutos para", "volver a entrar."], "reposo", (), None, False),
)


def states(mobile=False):
    w = MOBILE[0] if mobile else 1440
    pad = 16 if mobile else 96
    cw = w - 2 * pad
    b = [f'<rect width="{w}" height="6000" fill="{P["niebla"]}"/>'] + topbar(w, user=None if mobile else "Rosa")
    b.append(text(pad, 150 if mobile else 180, "Estados", 32 if mobile else 48, 600, font=FONT_TITLE))
    b += paragraph(pad, 186 if mobile else 220, ["Lo que se ve mientras carga, cuando no hay", "nada o cuando algo falla. Nunca se", "inventan datos para llenar el espacio."] if mobile else
                   ["Lo que se ve mientras carga, cuando no hay nada o cuando algo falla. Nunca se inventan datos para llenar el espacio."], 16, 23, fill=SEC)
    y = (186 + 3 * 23 + 30) if mobile else 260
    cols = 1 if mobile else 3
    gw = (cw - (cols - 1) * 24) / cols
    items = [None] + list(STATES)
    row_h = []
    for i, it in enumerate(items):
        if it is None:
            h = 250
        else:
            title, rows, mood, buttons, code, dashed = it
            rows = wrap_lines([" ".join(rows)], int((gw - 140) / 7.4))
            h = 78 + len(rows) * 22 + 10 + (50 if code else 0) + (len(buttons) * 64 if mobile else (64 if buttons else 0)) + 20
        row_h.append(h)
    hmax = max(row_h)
    for i, it in enumerate(items):
        cx = pad + (i % cols) * (gw + 24)
        cy = y + (i // cols) * ((row_h[i] if mobile else hmax) + 28) if not mobile else y
        h = row_h[i] if mobile else hmax
        if it is None:
            b += skeleton_card(cx, cy, gw, h, mobile)
        else:
            title, rows, mood, buttons, code, dashed = it
            b += state_card(cx, cy, gw, h, title, rows, mood, buttons, code, dashed, mobile)
        if mobile:
            y += h + 28
    if not mobile:
        y += ((len(items) + cols - 1) // cols) * (hmax + 28)
    b += paragraph(pad, y + 20, ["Borde punteado: no hay nada todavía, no es un", "error. El código para soporte es el request_id."] if mobile else
                   ["Borde punteado: no hay nada todavía, no es un error. El código para soporte es el request_id de la respuesta (cabecera X-Request-ID)."], 14, 21, fill=SEC)
    return frame((w, y + 100), b, P["niebla"])


# ---------- Menú en móvil ----------

def menu(guest=False):
    w, h = MOBILE
    b = [f'<rect width="{w}" height="{h}" fill="{P["noche"]}"/>']
    top = [poly(chamfer(12, 18, w - 24, 56, 12), BORDE), poly(chamfer(12, 12, w - 24, 56, 12), WHITE)] + logo(26, 18)
    top += [f'<path d="M{w - 58} 28 l22 22 M{w - 36} 28 l-22 22" stroke="{P["noche"]}" stroke-width="4" stroke-linecap="round"/>']
    b += [group("barra", top)]
    items = ["Consultar", "Mi finca", "Cómo funciona"] + (["Entrar", "Crear cuenta"] if guest else ["Mi cuenta", "Mi actividad"])
    y = 130
    for i, it in enumerate(items):
        on = it == "Mi finca" and not guest
        b += [text(28, y + i * 58, it, 26, 600, P["trigo"] if on else WHITE, FONT_TITLE)]
        if on:
            b.append(poly([(12, y + i * 58 - 18), (20, y + i * 58 - 10), (12, y + i * 58 - 2), (4, y + i * 58 - 10)], P["calabaza"]))
    y += len(items) * 58 + 10
    b.append(f'<rect x="28" y="{y}" width="{w - 56}" height="1" fill="{WHITE}" fill-opacity="0.25"/>')
    y += 44
    b.append(text(28, y, "ESTE DISPOSITIVO", 13, 700, P["niebla"]))
    for i, (label, on) in enumerate((("Modo ligero", False), ("Reducir movimiento", True), ("Sonido", False))):
        ry = y + 40 + i * 60
        b += [text(28, ry + 8, label, 18, 700, WHITE)] + toggle(w - 92, ry - 18, on, name=f"interruptor-{label.split(' ')[0].lower()}")
    y += 40 + 3 * 60 + 10
    if not guest:
        b += [text(28, y + 10, "Entró como rosa.samaca", 14, fill=P["niebla"])]
        b += [text(28, y + 46, "Cerrar sesión", 17, 700, P["trigo"]), f'<rect x="28" y="{y + 51}" width="114" height="2" fill="{P["trigo"]}"/>']
    else:
        b += paragraph(28, y + 10, ["Sin cuenta, lo que consulta no se guarda."], 14, fill=P["niebla"])
    return frame((w, h), b, P["noche"])


# ---------- Reportar un problema (P1) ----------

TICKETS = (("Un lote no me deja guardar la siembra", "9 oct", "Cerrado", "Soporte restauró una siembra borrada."),
           ("El calendario no muestra la cebolla", "2 oct", "En revisión", None))


def textarea(x, y, w, h, label, value_rows):
    body = [text(0, 0, label, 18, 700), poly(chamfer(1.5, 13.5, w - 3, h, 10), WHITE, P["noche"], 3)]
    body += paragraph(20, 46, value_rows, 17, 24)
    body.append(text(w - 16, h + 2, f"{sum(len(r) for r in value_rows)} de 1.000", 12, fill=SEC, anchor="end"))
    return [group("campo-mensaje", body, x, y)]


def report(mobile=False):
    w = MOBILE[0] if mobile else 1440
    cw = w - 24 if mobile else 720
    x0 = 12 if mobile else 96
    pad = 20 if mobile else 40
    iw = cw - 2 * pad
    c = link(pad, 44, "‹ Volver", 15)
    c += [text(pad, 92, "Reportar un problema", 28 if mobile else 36, 600, font=FONT_TITLE)]
    c += [poly(chamfer(cw - pad - 44, 70, 44, 24, 6), WHITE, D["cielo"], 1.5), text(cw - pad - 22, 87, "P1", 13, 700, D["cielo"], anchor="middle")]
    intro = (["Cuéntenos qué pasó. Soporte puede ver sus", "lotes para resolverlo, como dice el", "consentimiento."] if mobile else
             ["Cuéntenos qué pasó. Soporte puede ver sus lotes para resolverlo, como dice el consentimiento."])
    c += paragraph(pad, 126, intro, 15, 22, fill=SEC)
    y = 126 + len(intro) * 22 + 26
    c += field(pad, y, iw, "¿Sobre qué?", "El lote El Alto", trailing="▾", name="campo-sobre")
    y += 104
    msg = (["Registré la cosecha de papa y no", "aparece en el historial."] if mobile else ["Registré la cosecha de papa y no aparece en el historial."])
    c += textarea(pad, y, iw, 120, "¿Qué pasó?", msg)
    y += 160
    c += [poly(chamfer(pad, y, iw, 40, 8), P["niebla"]), text(pad + 16, y + 26, "Código para soporte: 9b1e-42c7 (se adjunta solo)" if not mobile else "Código: 9b1e-42c7 (se adjunta)", 14, 700)]
    y += 60
    c += paragraph(pad, y, ["No escriba contraseñas ni datos de otras", "personas."] if mobile else ["No escriba contraseñas ni datos de otras personas."], 13, 19, fill=SEC)
    y += (2 if mobile else 1) * 19 + 16
    if mobile:
        c += button(pad, y, iw, "Enviar") + link(pad + iw / 2, y + 86, "Cancelar", 16, anchor="middle")
        y += 110
    else:
        c += button(pad, y, 240, "Enviar") + link(pad + 268, y + 32, "Cancelar", 16)
        y += 70
    ch = y + 20
    top = 100 if mobile else 120
    b = [f'<rect width="{w}" height="3000" fill="{P["niebla"]}"/>'] + topbar(w, user=None if mobile else "Rosa")
    b += card(x0, top, cw, ch) + [group("reportar", c, x0, top)]
    # Mis reportes
    tx, ty, tw = (x0, top + ch + 28, cw) if mobile else (x0 + cw + 24, top, w - x0 - cw - 24 - 96)
    t = [text(24, 46, "Mis reportes", 22, 600, font=FONT_TITLE)]
    yy = 70
    for title, date, status, answer in TICKETS:
        lines = wrap_lines([title], 22 if mobile else 28)
        t += paragraph(24, yy + 20, lines, 16, 22, weight=700)
        st_fill = P["brote"] if status == "Cerrado" else P["trigo"]
        t += [poly(chamfer(tw - 24 - 110, yy + 2, 110, 26, 6), st_fill), text(tw - 24 - 55, yy + 20, status, 13, 700, anchor="middle")]
        yy += 20 + len(lines) * 22
        t.append(text(24, yy, f"Enviado el {date}", 13, fill=SEC))
        if answer:
            t += paragraph(24, yy + 22, wrap_lines([answer], 34 if mobile else 42), 13, 19)
            yy += 22 + len(wrap_lines([answer], 34 if mobile else 42)) * 19
        yy += 22
        t.append(f'<rect x="24" y="{yy}" width="{tw - 48}" height="1" fill="{BORDE}"/>')
        yy += 12
    t += link(24, yy + 26, "Ver mi actividad", 15)
    th = yy + 50
    b += card(tx, ty, tw, th, "mis-reportes") + [group("mis-reportes-texto", t, tx, ty)]
    h = max(top + ch, ty + th) + 60
    return frame((w, h), b, P["niebla"])


SCREENS = {
    "transversal-01-como-funciona-escritorio": how,
    "transversal-01-como-funciona-movil": lambda: how(mobile=True),
    "transversal-02-estados-escritorio": states,
    "transversal-02-estados-movil": lambda: states(mobile=True),
    "transversal-03-menu-movil": menu,
    "transversal-03-menu-invitado-movil": lambda: menu(guest=True),
    "transversal-05-reportar-escritorio": report,
    "transversal-05-reportar-movil": lambda: report(mobile=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
