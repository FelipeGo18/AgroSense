"""Pantallas finales de «Qué sembrar después» (tanda 4; rediseño, tanda 6): prioridades, ranking de rotaciones y opciones excluidas.

Rediseño: sin semestres. La primera siembra empieza en `sowing_date` y cada cultivo de la secuencia se evalúa en su
propia ventana; una opción que no se da en la zona se excluye con su motivo (R3). Estas prioridades se llaman
«¿Qué busca en la rotación?», para no confundirlas con «¿Qué le importa al elegir la fecha?» (las seis señales).

EP-10 (HU-101, HU-102) sobre EP-08 y el suelo de EP-18 (HU-184). El puntaje total se calcula aquí igual que en el
motor: promedio de los criterios ponderado por las prioridades (0 a 5). Las cifras son de muestra.
Cada control lleva a algo definido: las semillas cambian el orden; «Cambiar» vuelve a elegir el cultivo anterior;
«Ver diagnóstico» consulta POST /diagnostics; «Ver calendario» abre HU-180; «Ver por qué» despliega las excluidas.

    python design/pantallas/rotaciones.py     # escribe svg/rotaciones-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from build_kit_svg import priority_row  # noqa: E402
from ui import (BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, frame, group, inner, link,  # noqa: E402
                paragraph, poly, scene, text, topbar)

PRIORITIES = (("water", "Agua", 3, "Que gaste poca agua"), ("soil", "Suelo", 5, "Que recupere el suelo"),
              ("income", "Ingreso", 2, "Que deje ingreso pronto"), ("risk", "Riesgo", 4, "Que el clima la favorezca"))

SOWING = "15 de enero de 2027"  # `sowing_date` de la primera siembra
OPTIONS = (  # secuencia de dos ciclos, puntaje por criterio (0 a 100), razones con su regla y la ventana de cada ciclo
    ("Arveja", "Papa", {"water": 70, "soil": 90, "income": 75, "risk": 80},
     ["Leguminosa: fija nitrógeno para la papa que sigue.", "Raíz distinta a la de la papa: alterna la profundidad."],
     "Reglas: bonificar leguminosas · alternar la raíz", "Arveja 15 ene – may 2027 · papa desde jun 2027"),
    ("Avena con vicia", "Papa", {"water": 85, "soil": 100, "income": 20, "risk": 85},
     ["Abono verde: el carbono orgánico de su zona es medio.", "No deja cosecha esta temporada."],
     "Regla: abono verde si el carbono orgánico es bajo o medio", "Avena 15 ene – abr 2027 · papa desde may 2027"),
    ("Haba", "Maíz", {"water": 60, "soil": 80, "income": 70, "risk": 60},
     ["Leguminosa y luego un cereal de otra familia.", "El maíz de julio pasa por meses con más heladas."],
     "Reglas: bonificar leguminosas · no repetir familia", "Haba 15 ene – jun 2027 · maíz desde jul 2027"),
    ("Descanso", "Papa", {"water": 100, "soil": 70, "income": 0, "risk": 90},
     ["El lote descansa una temporada y corta el ciclo de plagas.", "No deja ingreso esta temporada."],
     "Regla: no repetir la familia del cultivo", "Descanso ene – jun 2027 · papa desde jul 2027"),
)

EXCLUDED = (
    ("Papa → Papa", "Misma familia que el cultivo anterior (solanáceas): repite plagas y enfermedades.", "Regla: no repetir la familia · catálogo de rotación"),
    ("Papa criolla → Arveja", "La papa criolla también es solanácea, como la papa que acaba de cosechar.", "Regla: no repetir la familia · catálogo de rotación"),
    ("Cebolla → Papa", "Tolera pH de 6,0 a 7,5 y su suelo estimado es de 5,2 a 5,8: queda fuera en todo el intervalo.", "Regla: pH fuera del rango (R3) · SoilGrids"),
    ("Yuca → Papa", "No se da en su zona: Samacá está a 2.660 m y la yuca se da hasta 1.800 m.", "Regla: aptitud del cultivo (R3) · ficha del cultivo"),
)


def wrap(t, n):
    words, line, out = t.split(" "), "", []
    for wd in words:
        if line and len(line) + len(wd) + 1 > n:
            out.append(line)
            line = ""
        line = (line + " " + wd).strip()
    out.append(line)
    return out


def total(scores):
    weights = {k: v for k, _, v, _ in PRIORITIES}
    return round(sum(scores[k] * weights[k] for k in weights) / sum(weights.values()))


RANKED = sorted(OPTIONS, key=lambda o: (-total(o[2]), o[0]))  # desempate determinista por nombre


# ---------- Piezas ----------

def priorities_panel(x, y, w, mobile):
    out = [text(0, 0, "¿Qué busca en la rotación?", 22, 600, font=FONT_TITLE),
           text(0, 26, "Toque las semillas: el orden cambia al instante.", 15, fill=SEC)]
    for i, (_, label, value, hint) in enumerate(PRIORITIES):
        yy = 52 + i * (66 if mobile else 60)
        out += [text(0, yy + 22, label, 18, 700), text(0, yy + 42, hint, 13, fill=SEC)]
        px, sc = (130, 0.6) if mobile else (190, 0.62)
        out.append(f'<g transform="translate({px} {yy + 2}) scale({sc})">{inner(priority_row(value))}</g>')
        if not mobile:
            out.append(text(w, yy + 28, f"{value} de 5", 14, 700, SEC, anchor="end"))
    return [group("prioridades", out, x, y)]


def bar(x, y, w, label, value, weight):
    return [text(x, y + 13, label, 14, 700), poly(chamfer(x + 74, y, w, 16, 4), P["niebla"]),
            poly(chamfer(x + 74, y, max(6, w * value / 100), 16, 4), P["brote"] if value >= 50 else P["trigo"]),
            text(x + 84 + w, y + 13, f"{value}", 14, 700), text(x + 120 + w, y + 13, f"peso {weight}", 12, fill=SEC)]


def option_card(x, y, w, h, rank, opt, mobile):
    first, second, scores, reasons, rule, when = opt
    score = total(scores)
    body = [poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE, P["calabaza"] if rank == 1 else None, 3 if rank == 1 else 0)]
    body += [poly([(34, 14), (54, 34), (34, 54), (14, 34)], P["calabaza"] if rank == 1 else P["niebla"], P["noche"], 2),
             text(34, 41, f"{rank}", 20, 700, anchor="middle")]
    seq = f"{first} → {second}"
    body.append(text(70, 42, seq, 18 if mobile else 26, 600, font=FONT_TITLE))
    if mobile:  # dos líneas: una por ciclo, para no tapar el puntaje
        body += [text(70, 62, part, 12, fill=SEC) for part in when.split(" · ")[:1]] + [text(70, 78, when.split(" · ")[1], 12, fill=SEC)]
    dy = 12 if mobile else 0
    if not mobile:
        body.append(text(70, 66, when, 14, fill=SEC))
    body += [text(w - 24, 44, f"{score}", 34, 600, P["noche"], FONT_TITLE, anchor="end"), text(w - 24, 64, "de 100", 13, fill=SEC, anchor="end")]
    bw = (w - 220) if not mobile else (w - 190)
    for i, (k, label, weight, _) in enumerate(PRIORITIES):
        body += bar(24, 90 + dy + i * 26, bw, label, scores[k], weight)
    ry = 90 + dy + 4 * 26 + 18
    lines = [ln for r in reasons for ln in (wrap("· " + r, 44) if mobile else ["· " + r])]
    body += paragraph(24, ry, lines, 14, 20)
    ry += len(lines) * 20 + 8
    rlines = wrap(rule, 46) if mobile else [rule]
    rh = 12 + 16 * len(rlines)
    body += [poly(chamfer(24, ry, min(w - 48, max(len(x) for x in rlines) * 6.8 + 34), rh, 6), "#F2F5F7", BORDE, 1.5),
             poly([(36, ry + 8), (42, ry + 14), (36, ry + 20), (30, ry + 14)], D["brote"])]
    body += [text(48, ry + 19 + 16 * k, ln, 12, 700) for k, ln in enumerate(rlines)]
    ry += rh + 16
    if first not in ("Descanso",) and first != "Avena con vicia":
        body += button(24, ry, 260 if not mobile else w - 48, f"Ver diagnóstico de {first.lower()}", "secondary", h=44)
        if not mobile:
            body += link(300, ry + 28, "Ver calendario", 15)
    else:
        body += link(24, ry + 24, "Ver calendario" if first != "Descanso" else "¿Por qué descansar el lote?", 15)
    return [group(f"opcion-{rank}", body, x, y)]


def excluded_box(x, y, w, opened, mobile):
    if not opened:
        body = [poly(chamfer(0, 0, w, 64, 12), WHITE, D["cielo"], 2, "4 4"),
                text(24, 39, f"{len(EXCLUDED)} excluidas, con su motivo" if mobile else f"{len(EXCLUDED)} opciones excluidas, cada una con su regla o motivo", 17, 700)]
        body += link(w - 24, 39, "Ver por qué", 16, anchor="end")
        return [group("excluidas", body, x, y)], 64
    row_h = 124 if mobile else 78
    h = 74 + len(EXCLUDED) * row_h + 10
    body = [poly(chamfer(0, 0, w, h, 12), WHITE, D["cielo"], 2, "4 4"),
            text(24, 40, f"{len(EXCLUDED)} excluidas, con su motivo" if mobile else f"{len(EXCLUDED)} opciones excluidas, cada una con su regla o motivo", 17, 700)]
    body += link(w - 24, 40, "Ocultar", 16, anchor="end")
    for i, (seq, why, rule) in enumerate(EXCLUDED):
        yy = 70 + i * row_h
        body += [f'<rect x="24" y="{yy}" width="{w - 48}" height="1" fill="{BORDE}"/>',
                 poly(chamfer(24, yy + 14, 22, 22, 0), WHITE, P["noche"], 2), f'<path d="M29 {yy + 19} l12 12 M41 {yy + 19} l-12 12" stroke="{P["noche"]}" stroke-width="2.5"/>',
                 text(58, yy + 32, seq, 17, 700)]
        if mobile:
            words, line, lines = why.split(" "), "", []
            for wd in words:
                if len(line) + len(wd) > 40:
                    lines.append(line.strip())
                    line = ""
                line += wd + " "
            lines.append(line.strip())
            body += paragraph(58, yy + 54, lines[:3], 13, 18) + [text(58, yy + 54 + min(3, len(lines)) * 18 + 4, rule.split(" · ")[0], 12, 700, SEC)]
        else:
            body += [text(58, yy + 54, why, 14), text(w - 24, yy + 32, rule, 13, 700, SEC, anchor="end")]
    return [group("excluidas", body, x, y)], h


# ---------- Pantalla ----------

def rotations(mobile=False, opened=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    header_h = 520 if mobile else 440
    b = scene("a5-municipio", w, header_h, "recorte-rotaciones" + ("-m" if mobile else "") + ("-e" if opened else ""), 0.12)
    b += topbar(w, "Consultar", None if mobile else "Rosa")
    if mobile:
        x, y, cw, pad = 12, 92, 366, 22
    else:
        x, y, cw, pad = 96, 116, 1248, 36
    fw = cw - 2 * pad
    c = [text(pad, 44, "QUÉ SEMBRAR DESPUÉS · SAMACÁ" if mobile else "QUÉ SEMBRAR DESPUÉS · SAMACÁ, BOYACÁ", 14, 700, SEC)]
    if mobile:
        c += [text(pad, 84, "¿Qué sembrar después", 26, 600, font=FONT_TITLE), text(pad, 116, "de la papa?", 26, 600, font=FONT_TITLE)]
        cy0 = 140
    else:
        c.append(text(pad, 92, "¿Qué sembrar después de la papa?", 38, 600, font=FONT_TITLE))
        cy0 = 120
    # contexto: cultivo anterior y suelo usado (el mismo de la señal de suelo)
    ctx_w = fw if mobile else 520
    c += [poly(chamfer(pad, cy0, ctx_w, 52, 10), P["niebla"]), text(pad + 18, cy0 + 22, "Cultivo anterior", 13, fill=SEC), text(pad + 18, cy0 + 42, "Papa · elegida a mano (sin cuenta)", 16, 700)]
    c += link(pad + ctx_w - 16, cy0 + 22, "Cambiar", 14, anchor="end")
    c += [poly(chamfer(pad, cy0 + 64, ctx_w, 52, 10), P["niebla"]), text(pad + 18, cy0 + 86, "Suelo estimado de Samacá", 13, fill=SEC),
          text(pad + 18, cy0 + 106, "pH 5,2 a 5,8 · carbono medio" if mobile else "pH 5,2 a 5,8 · carbono orgánico medio", 16, 700)]
    c += link(pad + ctx_w - 16, cy0 + 86, "Ver suelo", 14, anchor="end")
    c += [poly(chamfer(pad, cy0 + 128, ctx_w, 52, 10), P["niebla"]), text(pad + 18, cy0 + 150, "Primera siembra", 13, fill=SEC),
          text(pad + 18, cy0 + 170, SOWING, 16, 700)]
    c += link(pad + ctx_w - 16, cy0 + 150, "Cambiar", 14, anchor="end")
    c += paragraph(pad, cy0 + 208, ["Cada cultivo se evalúa en su propia ventana.", "Con cuenta, se usan el historial y el suelo", "de su lote dibujado."] if mobile else
                   ["Cada cultivo se evalúa en su propia ventana. Con cuenta, se usan el historial y el suelo de su lote dibujado."], 14, 20, fill=SEC)
    if mobile:
        pp_y = cy0 + 290
        c += priorities_panel(pad, pp_y, fw, True)
        ch = pp_y + 52 + 4 * 66 + 20
    else:
        c += priorities_panel(pad + 620, 74, fw - 620, False)
        ch = 420
    b += card(x, y, cw, ch) + [group("contexto", c, x, y)]
    top = max(header_h, y + ch + 40)
    # ranking
    pad2 = 20 if mobile else 96
    s = [text(pad2, 50, "Opciones ordenadas por lo que le importa", 22 if mobile else 32, 600, font=FONT_TITLE) if not mobile else
         text(pad2, 50, "Opciones ordenadas", 26, 600, font=FONT_TITLE)]
    s += paragraph(pad2, 82, ["Solo secuencias que cumplen las reglas.", "Puntaje de 0 a 100 por criterio."] if mobile else
                   ["Solo secuencias que cumplen las reglas de rotación. Puntaje de 0 a 100 por criterio, ponderado por sus prioridades."], 16, 22, fill=SEC)
    gy = 130 if mobile else 116
    if mobile:
        ow, oh = 350, 440
        for i, opt in enumerate(RANKED):
            s += option_card(pad2, gy + i * (oh + 20), ow, oh, i + 1, opt, True)
        ey = gy + 4 * (oh + 20) + 10
    else:
        ow, oh = (w - 2 * pad2 - 24) / 2, 360
        for i, opt in enumerate(RANKED):
            s += option_card(pad2 + (i % 2) * (ow + 24), gy + (i // 2) * (oh + 28), ow, oh, i + 1, opt, False)
        ey = gy + 2 * (oh + 28) + 10
    box, bh = excluded_box(pad2, ey, w - 2 * pad2, opened, mobile)
    s += box
    vy = ey + bh + 44
    s.append(text(pad2, vy, "Datos 2026.11.0 · Reglas 1.0.0 · Cifras de muestra", 15, fill=SEC))
    s += link(pad2 if mobile else w - pad2, vy + (30 if mobile else 0), "¿Cómo se arma este orden?", 15, anchor="start" if mobile else "end")
    h = top + vy + 70
    b = [f'<rect y="{header_h}" width="{w}" height="{h - header_h}" fill="{P["niebla"]}"/>'] + b + [group("ranking", s, 0, top)]
    foot, fh = ui.footer(w, h, mobile, above=P["niebla"])
    return frame((w, h + fh), b + foot)


SCREENS = {
    "rotaciones-01-ranking-escritorio": lambda: rotations(),
    "rotaciones-02-excluidas-escritorio": lambda: rotations(opened=True),
    "rotaciones-01-ranking-movil": lambda: rotations(mobile=True),
    "rotaciones-02-excluidas-movil": lambda: rotations(mobile=True, opened=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
    for o in RANKED:
        print(f"  {o[0]} -> {o[1]}: {total(o[2])}")
