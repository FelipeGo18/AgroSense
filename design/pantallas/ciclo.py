"""Tanda 11 · «Ciclo de una estrategia» (HU-215). Escritorio y móvil, y el ciclo de descanso.

Al tocar un ciclo en las estrategias (estrategias.py) se abre su detalle. No pide un diagnóstico aparte: usa el
`diagnosis` que ya vino con la estrategia (`strategies[].cycles[].diagnosis`) y las mismas piezas del resultado
(senales.py): la luz con su acción, las seis señales calificadas y lo que más limita.

Suma tres cosas del ciclo:
- **Agua del plan** (POST /water-plans con el cultivo, su fecha y el área de la entrada, `area_pct` 100): el déficit
  de cada mes y el volumen, en rangos, para un año normal o un año seco. Es una estimación con el clima de la zona
  (R10). Sin riego no se llama «riego probable»: «el cultivo pasaría sed».
- **Humedad del suelo de la zona**, como contraste: la de NASA POWER y, si existe, la de SMAP, cada una en su unidad
  y con su fuente. Nunca un valor combinado (decisión 11) y no cambia el déficit.
- **Verdor** (serie `ndvi` de GET /trends): cuándo suele estar verde el campo de la zona junto a la ventana del
  ciclo. Es de la zona, no del lote.

Un ciclo de descanso no tiene semáforo: muestra cuánto dura y la regla que lo propone.
Qué hace cada control: las pestañas y los botones de ciclo cambian de ciclo; «Volver a las estrategias» regresa;
«Crear cuenta y registrarla» lleva a crear cuenta (con cuenta, en el primer ciclo dice «Registrar esta siembra» y
crea la temporada con el diagnóstico visto, HU-165); «Año normal / Año seco» cambia la tabla; «Ver detalle» abre la
gráfica de la señal; «Ver qué cambió en su zona» abre HU-219 (cambio.py) con el municipio y el cultivo.
Los nombres y las cifras son de muestra.

    python design/pantallas/ciclo.py     # escribe svg/estrategias-05-ciclo-*.svg
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402
import muestra as m  # noqa: E402
import senales as sg  # noqa: E402
from agua import fmt, m3, year_toggle  # noqa: E402
from diagnostico import limits_box, wrap  # noqa: E402
from estrategias import STRATEGIES, label_strip, title_of  # noqa: E402
from finca import drop  # noqa: E402
from ui import (BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, frame, group, link, mascot,  # noqa: E402
                paragraph, poly, scene, text, topbar, width_of)

STRATEGY = STRATEGIES[0]      # Arveja → Avena con vicia → Papa
REST = STRATEGIES[1]          # Descanso → Arveja → Papa
AREA = 1.26                   # el área de la entrada (HU-214)

# El diagnóstico del ciclo 1: arveja en Samacá, sembrando el 2 de agosto de 2027, sin riego. Coincide con
# `muestra.ALTERNATIVES`: sale bien en clima y lo que más limita son las heladas, moderadas-altas.
ARVEJA = dict(
    water=dict(score=82, critical=False, reasons=["En 8 de los últimos 10 años la", "lluvia de ago a nov cubrió lo", "que necesita la arveja."], note="Sin riego"),
    frost=dict(score=72, critical=False, reasons=["Heló en la floración (oct)", "4 de cada 100 años."], note=None),
    heat=dict(score=95, critical=False, reasons=["La máxima rara vez pasa de", "22 °C; la arveja aguanta", "hasta 27 °C."], note=None),
    soil=dict(score=78, critical=False, reasons=["pH estimado 5,2 a 5,8: en", "el rango de la arveja.", "Estimación de 250 m."], note=None),
    supply=dict(score=76, critical=False, reasons=["En 2025 B (último dato,", "preliminar) se sembró menos", "arveja que antes."], note=None),
    market=dict(score=None, critical=False, reasons=["Sin datos de precios", "para Samacá."], note=None),
)
SUITABILITY = dict(score=95, reason="La altitud de Samacá (2.660 m) está dentro del rango de la arveja (2.000 a 3.000 m).", source=m.SUITABILITY["source"])
LIMITS = ["Los datos de EVA de 2025 son preliminares.", "El suelo es el estimado para el municipio, no para su lote.", "Sin datos de mercado: el precio no se evaluó.",
          "Evaluado sin riego, como usted indicó.", "La cosecha se estima por calendario, con la duración de la ficha."]

# Agua del ciclo (POST /water-plans): déficit por mes en mm, mínimo y máximo, en año normal. Sin déficit: la lluvia alcanza.
WATER_MONTHS = (("Ago", None), ("Sep", (8, 20)), ("Oct", None), ("Nov", (5, 14)))
# Humedad del suelo de la zona, de dos fuentes, cada una en su unidad. Es contraste: no cambia el déficit.
MOISTURE = (
    ("NASA POWER", "Humedad en la zona de raíces · modelo · celda de unos 50 km", "%", ("62", "58", "66", "70")),
    ("SMAP", "Humedad de la superficie · satélite · celda de 9 km", "m³/m³", ("0,31", "0,29", "0,34", "0,36")),
)
# Verdor normal de Samacá por periodo de 16 días (23 al año), de 0 a 1 (MODIS, 250 m). Dos épocas verdes al año.
NDVI = (0.52, 0.50, 0.49, 0.51, 0.56, 0.62, 0.67, 0.70, 0.71, 0.69, 0.65, 0.60, 0.57, 0.55, 0.56, 0.60, 0.65, 0.69, 0.72, 0.71, 0.67, 0.61, 0.56)
WINDOW = (13.4, 20.9)  # del 2 de agosto al 29 de noviembre, en periodos de 16 días


# ---------- Piezas ----------

def cycle_tabs(x, y, w, strategy, current):
    """Los ciclos de la estrategia, para pasar de uno a otro. El actual va lleno."""
    n = len(strategy["cycles"])
    gap = 10
    tw = (w - gap * (n - 1)) / n
    out = []
    for i, cycle in enumerate(strategy["cycles"]):
        on = i == current
        out.append(poly(chamfer(i * (tw + gap), 0, tw, 44, 9), P["noche"] if on else WHITE, None if on else BORDE, 0 if on else 1.5))
        label = f"{i + 1} · {cycle[0]}"
        out.append(text(i * (tw + gap) + tw / 2, 28, label if tw > 150 or len(label) < 14 else f"{i + 1} · {cycle[0].split()[0]}", 15, 700, WHITE if on else P["noche"], anchor="middle"))
    return [group("ciclos", out, x, y)]


def water_block(x, y, w, mobile=False):
    """Agua del ciclo: una columna por mes; en los meses con déficit, milímetros y metros cúbicos en rango."""
    out = [text(0, 0, "Agua de este ciclo", 24 if mobile else 30, 600, font=FONT_TITLE)]
    sub = (["Cuánta agua faltaría cada mes, para", f"{str(AREA).replace('.', ',')} ha. POST /water-plans."] if mobile else
           [f"Cuánta agua faltaría cada mes en {str(AREA).replace('.', ',')} ha de arveja, sembrando el 2 de agosto. Es una estimación, en rangos."])
    out += paragraph(0, 30, sub[:1] if mobile else sub, 15, 21, fill=SEC)
    if mobile:
        out += paragraph(0, 51, [f"{str(AREA).replace('.', ',')} ha de arveja. Estimación, en rangos."], 15, 21, fill=SEC)
    yy = 96 if mobile else 70
    lines = (["Estimación con el clima de la zona, no una", "medición de su lote. En los meses marcados", "la lluvia no alcanza: el cultivo pasaría sed.", "Verifique la humedad del suelo en campo."] if mobile else
             ["Estimación con el clima de la zona, no una medición de su lote. En los meses marcados la lluvia no alcanza:", "el cultivo pasaría sed. Verifique la humedad del suelo en campo."])
    bh = 28 + len(lines) * 22 + 10
    out.append(group("rotulo-de-estimacion", [poly(chamfer(0, 0, w, bh, 12), "#E6F0F5", D["cielo"], 2)] + drop(30, bh / 2, 1.6) + paragraph(60, 30, lines, 15 if mobile else 16, 22, weight=700), 0, yy))
    yy += bh + 20
    out += year_toggle(0, yy, 300 if mobile else 320)
    yy += 64
    if mobile:
        for name, deficit in WATER_MONTHS:
            row = [poly(chamfer(0, 6, w, 70, 12), BORDE), poly(chamfer(0, 0, w, 70, 12), WHITE), text(18, 42, name + " 2027", 18, 700)]
            if deficit:
                lo, hi = deficit
                row += drop(132, 34, 1.3) + [text(152, 30, f"{lo} a {hi} mm", 15, 700), text(152, 50, f"{fmt(m3(lo, AREA))} a {fmt(m3(hi, AREA))} m³ · pasaría sed", 13, fill=D["cielo"])]
            else:
                row += [f'<circle cx="132" cy="36" r="8" fill="none" stroke="{BORDE}" stroke-width="2.5"/>', text(152, 41, "La lluvia alcanza", 14, fill=SEC)]
            out.append(group(f"mes-{name.lower()}", row, 0, yy))
            yy += 84
    else:
        lab = 230
        cw = (w - lab - 16) / len(WATER_MONTHS)
        th = 196
        t = [poly(chamfer(0, 8, w, th, 16), BORDE), poly(chamfer(0, 0, w, th, 16), WHITE)]
        for i, (name, deficit) in enumerate(WATER_MONTHS):
            cx = lab + i * cw
            t.append(text(cx + cw / 2, 38, name + " 2027", 17, 700, anchor="middle"))
            if i:
                t.append(f'<rect x="{cx:.1f}" y="54" width="1" height="{th - 70}" fill="{BORDE}" fill-opacity="0.6"/>')
            if deficit:
                lo, hi = deficit
                t.append(poly(chamfer(cx + 10, 64, cw - 20, 104, 8), "#E6F0F5", D["cielo"], 1.5))
                t += drop(cx + 36, 98, 1.3)
                t += [text(cx + 58, 100, f"{lo} a {hi} mm", 16, 700), text(cx + 58, 124, f"{fmt(m3(lo, AREA))} a {fmt(m3(hi, AREA))} m³", 15), text(cx + 58, 146, "pasaría sed", 12, 700, D["cielo"])]
            else:
                t += [f'<circle cx="{cx + cw / 2 - 62:.1f}" cy="112" r="8" fill="none" stroke="{BORDE}" stroke-width="2.5"/>', text(cx + cw / 2 - 44, 117, "La lluvia alcanza", 14, fill=SEC)]
        t.append(f'<rect x="16" y="56" width="{w - 32}" height="1" fill="{BORDE}"/>')
        t += [text(20, 104, "Arveja", 18, 700), text(20, 126, f"{str(AREA).replace('.', ',')} ha · año normal", 14, fill=SEC), text(20, 148, "mm y m³ que faltarían", 13, fill=SEC)]
        out.append(group("agua-por-mes", t, 0, yy))
        yy += th + 20
    lo = sum(m3(d[0], AREA) for _, d in WATER_MONTHS if d)
    hi = sum(m3(d[1], AREA) for _, d in WATER_MONTHS if d)
    out.append(text(0, yy + 14, f"En el ciclo faltarían de {fmt(lo)} a {fmt(hi)} m³. Un tanque de 1.000 litros es 1 m³.", 15 if mobile else 16, 700))
    return [group("agua-del-ciclo", out, x, y)], yy + 34


def moisture_block(x, y, w, mobile=False):
    """La humedad del suelo de la zona según cada fuente, lado a lado y cada una en su unidad. Para contrastar."""
    out = [text(0, 0, "Humedad del suelo de la zona", 19 if mobile else 22, 600, font=FONT_TITLE)]
    note = (["Lo normal en esos meses. Es de la zona, no", "de su lote, y no cambia el cálculo del agua."] if mobile else
            ["Lo normal en esos meses, según cada fuente. Es de la zona, no de su lote, y no cambia el cálculo del agua: sirve para contrastar."])
    out += paragraph(0, 26, note, 14, 20, fill=SEC)
    yy = 26 + len(note) * 20 + 10
    months = [name for name, _ in WATER_MONTHS]
    for source, what, unit, values in MOISTURE:
        rh = 124 if mobile else 78
        row = [poly(chamfer(0, 0, w, rh, 10), WHITE, BORDE, 1.5), text(18, 28, source, 16, 700),
               poly(chamfer(18 + width_of(source, 16, True) + 30, 12, 118, 22, 5), WHITE, D["cielo"], 1.5),
               text(18 + width_of(source, 16, True) + 89, 27, "Para contrastar", 11, 700, D["cielo"], anchor="middle")]
        rows = wrap(what, 44) if mobile else [what]
        row += paragraph(18, 50, rows, 12, 16, fill=SEC)
        vx0 = 18 if mobile else w - 4 * 110 - 10
        vy = 100 if mobile else 34
        cwid = (w - 36) / 4 if mobile else 110
        for i, value in enumerate(values):
            row += [text(vx0 + i * cwid + cwid / 2, vy, value, 17, 700, anchor="middle"), text(vx0 + i * cwid + cwid / 2, vy + 18, f"{months[i]} · {unit}", 11, fill=SEC, anchor="middle")]
        out.append(group(f"humedad-{source.split()[-1].lower()}", row, 0, yy))
        yy += rh + 10
    return [group("humedad-del-suelo", out, x, y)], yy


def ndvi_block(x, y, w, mobile=False):
    """Cuándo suele estar verde el campo de la zona, junto a la ventana del ciclo (serie `ndvi` de GET /trends)."""
    out = [text(0, 0, "Verdor de la zona", 24 if mobile else 30, 600, font=FONT_TITLE)]
    label = ["Cuándo suele estar verde el campo en su", "zona · MODIS, 250 m"] if mobile else ["Cuándo suele estar verde el campo en su zona · MODIS, 250 m"]
    out += paragraph(0, 30, label, 15, 21, weight=700)
    yy = 30 + len(label) * 21 + 8
    ch, top, left = (170, 34, 40) if mobile else (200, 36, 56)
    cw = w - left - 20
    card_h = top + ch + 92
    c = [poly(chamfer(0, 8, w, card_h, 16), BORDE), poly(chamfer(0, 0, w, card_h, 16), WHITE)]
    X = lambda p: left + cw * p / 23  # noqa: E731
    Y = lambda v: top + ch - ch * (v - 0.3) / 0.5  # noqa: E731  (de 0,3 a 0,8)
    c.append(f'<rect x="{X(WINDOW[0]):.1f}" y="{top}" width="{X(WINDOW[1]) - X(WINDOW[0]):.1f}" height="{ch}" fill="{P["calabaza"]}" fill-opacity="0.16"/>')
    c.append(text((X(WINDOW[0]) + X(WINDOW[1])) / 2, top + 16, "este ciclo" if mobile else "ventana de este ciclo", 12, 700, D["calabaza"], anchor="middle"))
    for v in (0.4, 0.6, 0.8):
        c += [f'<rect x="{left}" y="{Y(v):.1f}" width="{cw}" height="1" fill="{BORDE}"/>', text(left - 8, Y(v) + 4, f"{v:.1f}".replace(".", ","), 12, fill=SEC, anchor="end")]
    pts_ = [(X(i + 0.5), Y(v)) for i, v in enumerate(NDVI)]
    area = [(pts_[0][0], top + ch)] + pts_ + [(pts_[-1][0], top + ch)]
    c.append(poly(area, P["brote"]).replace("<polygon", '<polygon fill-opacity="0.35"'))
    c.append(f'<polyline points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in pts_)}" fill="none" stroke="{D["brote"]}" stroke-width="3" stroke-linejoin="round"/>')
    c.append(f'<rect x="{left}" y="{top + ch}" width="{cw}" height="2" fill="{P["noche"]}"/>')
    for i, mon in enumerate("EFMAMJJASOND"):
        c.append(text(left + cw * (i + 0.5) / 12, top + ch + 20, mon, 12, fill=SEC, anchor="middle"))
    c.append(text(left, top - 12, "Verdor normal (NDVI, de 0 a 1)", 12, 700, SEC))
    foot = (["Dato de la zona, a 250 m: mezcla cultivos,", "pastos y bosque. No es su lote ni dice", "cómo le irá."] if mobile else
            ["Dato de la zona, a 250 m: mezcla cultivos, pastos y bosque. No es una medición de su lote ni dice cómo le irá a su cultivo."])
    c += paragraph(20, top + ch + 46, foot, 13, 17, fill=SEC)
    card_h += (len(foot) - 1) * 17
    c[0], c[1] = poly(chamfer(0, 8, w, card_h, 16), BORDE), poly(chamfer(0, 0, w, card_h, 16), WHITE)
    out.append(group("grafica-verdor", c, 0, yy))
    return [group("verdor", out, x, y)], yy + card_h + 8


def change_link(x, y, w, mobile=False):
    """Enlace a «Qué cambió en su zona» (HU-219) con el municipio y el cultivo del ciclo."""
    h = 132 if mobile else 96
    body = [poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE)]
    body.append(text(24, 38, "¿Qué cambió en su zona?", 20, 600, font=FONT_TITLE))
    body += paragraph(24, 62, ["Heladas, lluvia y calor de dos periodos de", "la historia de Samacá, para la arveja."] if mobile else
                      ["Heladas, lluvia y calor de dos periodos de la historia de Samacá, y cómo se movieron las mejores fechas de la arveja. No es un pronóstico."], 14, 20, fill=SEC)
    body += link(24 if mobile else w - 24, h - 18 if mobile else 40, "Ver qué cambió en su zona", 15, anchor="start" if mobile else "end")
    return [group("que-cambio", body, x, y)], h + 8


# ---------- Pantallas ----------

def header(mobile, strategy, current, cw, pad, guest=True):
    """Tarjeta de arriba: la estrategia, el ciclo, su ventana y, si se siembra, su luz con la acción."""
    fw = cw - 2 * pad
    crop, kind_, sow, harvest, light, _ = strategy["cycles"][current]
    n = len(strategy["cycles"])
    c = link(pad, 40, "‹ Volver a las estrategias", 15)
    kicker = f"ESTRATEGIA · {title_of(strategy).upper()}"
    c += paragraph(pad, 76, wrap(kicker, 40) if mobile else [kicker], 13 if mobile else 14, 18, weight=700, fill=SEC)
    yy = 76 + (len(wrap(kicker, 40)) - 1) * 18 if mobile else 76
    c += cycle_tabs(pad, yy + 16, fw, strategy, current)
    yy += 16 + 44 + 46
    c.append(text(pad, yy, f"Ciclo {current + 1} de {n}: {crop.lower()}", 27 if mobile else 36, 600, font=FONT_TITLE))
    yy += 30
    if kind_ == "descanso":
        c += paragraph(pad, yy, ["Del 2 de agosto al 28 de noviembre", "de 2027 · 17 semanas sin sembrar."] if mobile else
                       ["Del 2 de agosto al 28 de noviembre de 2027 · 17 semanas sin sembrar."], 16, 23, weight=700)
        yy += (2 if mobile else 1) * 23 + 14
        box = [poly(chamfer(0, 0, fw, 96 if mobile else 74, 10), WHITE, D["cielo"], 2, "5 4"),
               poly([(26, 20), (36, 32), (26, 44), (16, 32)], WHITE, D["cielo"], 2)]
        box += paragraph(52, 30, ["Sin semáforo: en un", "descanso no se siembra"] if mobile else ["Sin semáforo: en un descanso no se siembra"], 15, 19, weight=700)
        box += paragraph(52, 72 if mobile else 52, ["No hay fecha que evaluar."] if mobile else ["No hay fecha que evaluar ni señales que calificar. El clima de esos meses no cambia nada."], 14, 19, fill=SEC)
        c.append(group("sin-semaforo", box, pad, yy))
        yy += (96 if mobile else 74) + 22
        why = ["El terreno descansa después de la papa, un cultivo exigente, y se corta el ciclo de sus plagas antes de volver a sembrarla.",
               "El rastrojo queda sobre el suelo. No deja ingreso en este ciclo."]
        for r in why:
            rows = wrap(r, 40 if mobile else 92)
            c += paragraph(pad, yy, rows, 16, 23)
            yy += len(rows) * 23 + 6
        rule = "Regla: no repetir la familia del cultivo · catálogo de rotación"
        rw = min(fw, width_of(rule, 12, True) + 46)
        rrows = wrap(rule, 40) if mobile else [rule]
        c += [poly(chamfer(pad, yy + 4, rw, 12 + 17 * len(rrows), 6), "#F2F5F7", BORDE, 1.5), poly([(pad + 12, yy + 12), (pad + 18, yy + 18), (pad + 12, yy + 24), (pad + 6, yy + 18)], D["brote"])]
        c += paragraph(pad + 26, yy + 22, rrows, 12, 17, weight=700)
        yy += 12 + 17 * len(rrows) + 26
        c += link(pad, yy, "¿Por qué descansar el lote?", 15)
        yy += 30
        res = None
    else:
        last = "se incorpora" if kind_ == "abono" else "cosecha estimada"
        if mobile:
            c += [text(pad, yy, f"Siembra {sow}", 15, 700), text(pad, yy + 20, f"{last[0].upper() + last[1:]} {harvest}", 15, 700),
                  text(pad, yy + 40, "Estimada por calendario. No es pronóstico.", 13, fill=SEC)]
            yy += 68
        else:
            c += [text(pad, yy, f"Siembra {sow} → {last} {harvest}", 16, 700),
                  text(pad, yy + 20, "Estimada por calendario, con la duración de la ficha. No es pronóstico.", 13, fill=SEC)]
            yy += 48
        res = m.light_for(m.DEFAULT_WEIGHTS, ARVEJA)
        c += sg.light_block(pad, yy, fw, res, "Criterio de AgroSense", True)
        yy += 128 if mobile else 102
        for r in ["El clima de esta fecha le sirve a la arveja: agua y calor bien, y heladas raras en su floración.",
                  "En 2025 B, el último dato, se sembró menos arveja que antes en Samacá."]:
            rows = wrap(r, 40 if mobile else 92)
            c += paragraph(pad, yy, rows, 16, 23)
            yy += len(rows) * 23 + 6
        yy += 10
        primary = "Crear cuenta y registrarla" if guest else "Registrar esta siembra"
        if mobile:
            c += button(pad, yy, fw, primary)
            yy += 72
        else:
            c += button(pad, yy, 330, primary)
            yy += 76
        c += sg.priorities_summary(pad, yy, fw, m.DEFAULT_WEIGHTS, own=False)
        yy += 88 if mobile else 72
    # anterior y siguiente
    prev_ = strategy["cycles"][current - 1][0] if current else None
    next_ = strategy["cycles"][current + 1][0] if current + 1 < n else None
    c.append(f'<rect x="{pad}" y="{yy}" width="{fw}" height="1" fill="{BORDE}"/>')
    if prev_:
        c += link(pad, yy + 32, f"‹ Ciclo {current}: {prev_.lower()}", 15)
    if next_:
        c += link(pad + fw, yy + 32, f"Ciclo {current + 2}: {next_.lower()} ›", 15, anchor="end")
    return c, yy + 54, res


def cycle(mobile=False, rest=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    strategy = REST if rest else STRATEGY
    header_h = 560 if mobile else 440
    tagname = ("-m" if mobile else "") + ("-d" if rest else "")
    b = scene("a5-municipio", w, header_h, "recorte-ciclo" + tagname, 0.12)
    b += topbar(w, "Consultar")
    x, y, cw, pad = (12, 92, 366, 20) if mobile else (96, 116, 900, 36)
    c, ch, res = header(mobile, strategy, 0, cw, pad)
    b += card(x, y, cw, ch) + [group("ciclo", c, x, y)]
    if not mobile:
        b += mascot(1090, 130, 0.95, "reposo" if rest else "guia")
    top = max(header_h, y + ch + 40)
    pad2 = 16 if mobile else 96
    iw = w - 2 * pad2
    s, yy = [], 20
    if rest:
        # El descanso no tiene diagnóstico, agua ni verdor que mostrar: solo lo que sigue.
        rows = wrap("El ciclo 2 es arveja, sembrando el 29 de noviembre de 2027: su luz es amarilla y lo que más limita son las heladas.", 40 if mobile else 140)
        nh = 84 + len(rows) * 21 + 16
        nb = [poly(chamfer(0, 8, iw, nh, 16), BORDE), poly(chamfer(0, 0, iw, nh, 16), WHITE), text(24, 42, "Después del descanso", 20, 600, font=FONT_TITLE)]
        nb += paragraph(24, 68, rows, 15, 21)
        nb += link(24, 68 + len(rows) * 21 + 14, "Ver el ciclo 2: arveja", 15)
        s.append(group("lo-que-sigue", nb, pad2, yy))
        yy += nh + 30
    else:
        s += sg.suitability_line(pad2, yy, iw, SUITABILITY)
        ty = yy + (148 if mobile else 104)
        s.append(text(pad2, ty, "Las seis señales de este ciclo", 24 if mobile else 32, 600, font=FONT_TITLE))
        s += paragraph(pad2, ty + 32, ["Cada una calificada de 0 a 100 para", "la arveja. Ninguna se promedia con otra."] if mobile else
                       ["Las mismas del diagnóstico, calificadas de 0 a 100 frente a lo que necesita la arveja. Ninguna se promedia con otra. Toque una para ver su gráfica."], 15, 21, fill=SEC)
        gy = ty + (88 if mobile else 66)
        if mobile:
            sh = 300
            for i, k in enumerate(m.SIGNAL_ORDER):
                s += sg.signal_card(pad2, gy + i * (sh + 14), iw, sh, k, m.DEFAULT_WEIGHTS, res["limiting"], compact=True, signals=ARVEJA)
            yy = gy + 6 * (sh + 14) + 30
        else:
            gap, cols = 24, 3
            cw2, sh = (iw - (cols - 1) * gap) / cols, 300
            for i, k in enumerate(m.SIGNAL_ORDER):
                s += sg.signal_card(pad2 + (i % cols) * (cw2 + gap), gy + (i // cols) * (sh + gap), cw2, sh, k, m.DEFAULT_WEIGHTS, res["limiting"], signals=ARVEJA)
            yy = gy + 2 * (sh + gap) + 36
        wb, wh = water_block(pad2, yy + 30, iw, mobile)
        s += wb
        yy += 30 + wh + 30
        mb, mh = moisture_block(pad2, yy + 22, iw, mobile)
        s += mb
        yy += 22 + mh + 40
        nb, nh = ndvi_block(pad2, yy + 30, iw, mobile)
        s += nb
        yy += 30 + nh + 30
        cl, clh = change_link(pad2, yy, iw, mobile)
        s += cl
        yy += clh + 30
        lb, lh = limits_box(pad2, yy, iw, LIMITS, mobile)
        s += lb
        yy += lh + 30
    cb, cbh = label_strip(pad2, yy, iw, ["Es información para decidir.", "La decisión es suya."] if mobile else ["Es información para decidir. La decisión es suya."], "call")
    s += cb
    vy = yy + cbh + 40
    s.append(text(pad2, vy, f"{m.VERSIONS} · Pesos de AgroSense · Cifras de muestra" if not mobile else f"{m.VERSIONS} · Cifras de muestra", 15, fill=SEC))
    s += link(pad2 if mobile else w - pad2, vy + (30 if mobile else 0), "¿Cómo funciona y de dónde sale esto?", 15, anchor="start" if mobile else "end")
    h = top + vy + 70
    b = [f'<rect y="{header_h}" width="{w}" height="{h - header_h}" fill="{P["niebla"]}"/>'] + b + [group("detalle", s, 0, top)]
    foot, fh = ui.footer(w, h, mobile, above=P["niebla"])
    return frame((w, h + fh), b + foot)


SCREENS = {
    "estrategias-05-ciclo-escritorio": lambda: cycle(),
    "estrategias-05-ciclo-movil": lambda: cycle(mobile=True),
    "estrategias-05-ciclo-descanso-escritorio": lambda: cycle(rest=True),
    "estrategias-05-ciclo-descanso-movil": lambda: cycle(mobile=True, rest=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
    assert math.isclose(sum(1 for _ in NDVI), 23)
