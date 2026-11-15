"""Pantallas finales de Inicio y Descenso (tanda 2): portada y buscar mi municipio.
Dibujar el lote en el mapa está en lote.py (HU-164).

EP-17 (HU-173, pantalla de inicio) y el descenso de HU-155. Escritorio y móvil.

    python design/pantallas/inicio.py     # escribe svg/inicio-*.svg y svg/descenso-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401  (agrega design/kit y design/mascota al camino de importación)
from build_kit_svg import PIECES  # noqa: E402

from consulta import light, tag  # noqa: E402
from senales import KEY_TO_KIND, kind  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "globo"))
from build_globo import globe, space  # noqa: E402
from ui import (BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, field, frame, group, link,  # noqa: E402
                logo, mascot, paragraph, poly, scene, svg, text, topbar)



# ---------- Piezas propias del descenso ----------

def stepper(x, y, w, current, mobile=False):
    """Dónde va el descenso: satélite, región, municipio y finca. Las pasadas, llenas; la actual, en calabaza."""
    steps = ("Satélite", "Región", "Municipio", "Finca")
    body = [poly(chamfer(0, 6, w, 64, 12), BORDE), poly(chamfer(0, 0, w, 64, 12), WHITE)]
    gap = (w - 60) / 3
    body.append(f'<rect x="30" y="22" width="{w - 60:g}" height="4" fill="{BORDE}"/>')
    body.append(f'<rect x="30" y="22" width="{gap * current:g}" height="4" fill="{D["oliva"]}"/>')
    for i, label in enumerate(steps):
        cx = 30 + gap * i
        r = 11 if i == current else 8
        fill = P["calabaza"] if i == current else (D["oliva"] if i < current else WHITE)
        stroke = P["noche"] if i == current else (D["oliva"] if i < current else D["cielo"])
        body.append(poly([(cx, 24 - r), (cx + r, 24), (cx, 24 + r), (cx - r, 24)], fill, stroke, 2.5))
        if not mobile or i == current:
            body.append(text(cx, 54, label, 14, 700 if i == current else 400, P["noche"] if i <= current else SEC, anchor="middle"))
    return [group("descenso", body, x, y)]


def dropdown(x, y, w, rows, active=0):
    """Lista abierta de un selector con autocompletado: la semilla marca la opción activa."""
    h = len(rows) * 52 + 16
    body = [poly(chamfer(0, 8, w, h, 12), BORDE), poly(chamfer(0, 0, w, h, 12), WHITE, BORDE, 2)]
    for i, (name, hint) in enumerate(rows):
        ry = 8 + i * 52
        if i == active:
            body.append(poly(chamfer(6, ry, w - 12, 48, 8), "#E3EECF"))
            body.append(poly([(26, ry + 16), (34, ry + 24), (26, ry + 32), (18, ry + 24)], D["brote"]))
        body.append(text(46, ry + 31, name, 18, 700 if i == active else 400))
        body.append(text(w - 18, ry + 31, hint, 15, fill=SEC, anchor="end"))
    return [group("lista", body, x, y)]


# ---------- Portada ----------

QUESTIONS = (  # el flujo del MVP (decisión 12): estrategias, cada ciclo, agua del plan y qué cambió
    ("¿Qué siembro y en qué orden?", ["Estrategias de rotación de hasta 3 ciclos, comparadas por agua,", "suelo, ingreso y riesgo según lo que a usted le importa."],
     ["Estrategias de rotación de hasta 3 ciclos,", "comparadas por agua, suelo, ingreso y", "riesgo según lo que a usted le importa."], "prioridad-3", "germinada"),
    ("¿Conviene cada siembra?", ["Un semáforo por ciclo con seis señales:", "agua, heladas, calor, suelo, oferta y mercado."],
     ["Un semáforo por ciclo con seis señales:", "agua, heladas, calor, suelo, oferta y", "mercado."], "semaforo-verde", "frijol"),
    ("¿Cuánta agua va a necesitar?", ["Mes a mes, el agua que faltaría en cada ciclo, en rangos.", "Es una estimación con el clima de la zona."],
     ["Mes a mes, el agua que faltaría en cada", "ciclo, en rangos. Es una estimación con", "el clima de la zona."], "rotulo-estimacion", "maiz"),
    ("¿Qué cambió en su zona?", ["Heladas, lluvia y calor de dos periodos de la historia,", "lado a lado. No es un pronóstico."],
     ["Heladas, lluvia y calor de dos periodos", "de la historia, lado a lado.", "No es un pronóstico."], "heladas", "germinada"),
)
Q_H = {False: 880, True: 1550}  # alto de la sección: dos filas de dos tarjetas en escritorio; cuatro tarjetas en móvil

SOURCES = (
    ("Clima", "NASA POWER", ["Lluvia, temperatura, heladas y", "calor de su municipio."]),
    ("Suelo", "SoilGrids · ISRIC", ["pH, carbono orgánico y textura,", "estimados en celdas de 250 m."]),
    ("Oferta", "Evaluaciones Agropecuarias (EVA)", ["Cuánto se sembró de cada cultivo,", "por municipio, junto a otras fuentes."]),
    ("Mercado", "SIPSA · DANE", ["Precios mayoristas,", "cuando hay datos de la zona."]),
)


CREDITO_GLOBO = "Contornos: Natural Earth · Color: NASA Blue Marble"


def hero(w, h, mobile):
    """La Tierra real gira en el espacio (build_globo.py); al bajar, frena con Colombia al frente y empieza el descenso."""
    clip_id = "recorte-portada" + ("-m" if mobile else "")
    if mobile:
        earth = globe(-74, 5, 205, 195, 735)
    else:
        earth = globe(-74, 5, 330, 1060, 500)
    b = [f'<defs><clipPath id="{clip_id}"><rect width="{w}" height="{h}"/></clipPath></defs>',
         f'<g id="fondo" clip-path="url(#{clip_id})">{"".join(space(w, h))}<g id="globo">{"".join(earth)}</g></g>']
    b += topbar(w)
    if mobile:
        b.append(text(20, 170, "AgroSense", 58, 600, WHITE, FONT_TITLE))
        b += paragraph(20, 220, ["¿Qué sembrar y en qué orden?", "Le mostramos estrategias de", "rotación con datos del satélite y", "reglas que se pueden explicar.", "Usted decide."], 22, 31, fill=WHITE)
        b += button(20, 392, 350, "Consultar sin cuenta") + button(20, 464, 350, "Entrar", "secondary")
        b += mascot(292, 528, 0.4, "vuelo")
        b.append(text(195, h - 30, "Baje para empezar el recorrido ↓", 16, 700, WHITE, anchor="middle"))
        b.append(text(195, h - 10, CREDITO_GLOBO, 11, fill="#C9D6E0", anchor="middle"))
    else:
        b.append(text(96, 300, "AgroSense", 120, 600, WHITE, FONT_TITLE))
        b += paragraph(100, 372, ["¿Qué sembrar y en qué orden?", "Le mostramos estrategias de rotación con datos", "del satélite y reglas que se pueden explicar. Usted decide."], 30, 42, fill=WHITE)
        b += button(100, 520, 300, "Consultar sin cuenta") + button(424, 520, 180, "Entrar", "secondary")
        b += mascot(700, 110, 0.8, "vuelo")
        b.append(text(560, h - 36, "Baje para empezar el recorrido ↓", 18, 700, WHITE, anchor="middle"))
        b.append(text(w - 32, h - 14, CREDITO_GLOBO, 13, fill="#C9D6E0", anchor="end"))
    return b


def questions(y0, w, mobile):
    b = [f'<rect y="{y0}" width="{w}" height="{Q_H[mobile]}" fill="{P["niebla"]}"/>']
    pad = 20 if mobile else 96
    b.append(text(pad, y0 + (80 if mobile else 110), "Cuatro preguntas," if mobile else "Cuatro preguntas, cuatro respuestas claras", 30 if mobile else 44, 600, font=FONT_TITLE))
    if mobile:
        b.append(text(pad, y0 + 118, "cuatro respuestas claras", 30, 600, font=FONT_TITLE))
    b.append(text(pad, y0 + (158 if mobile else 156), "Para su lote o, sin cuenta, para su municipio.", 16 if mobile else 20, fill=SEC))
    cw = 350 if mobile else (w - 2 * pad - 24) / 2
    ch = 290 if mobile else 280
    for i, (title, rows, rows_m, piece, seed) in enumerate(QUESTIONS):
        cx, cy = (pad, y0 + 200 + i * 330) if mobile else (pad + (i % 2) * (cw + 24), y0 + 210 + (i // 2) * (ch + 34))
        c = [text(28, 54, f"{i + 1}", 34, 600, P["calabaza"], FONT_TITLE), text(64, 52, title, 20 if mobile else 24, 600, font=FONT_TITLE)]
        c += paragraph(28, 96, rows_m if mobile else rows, 15 if mobile else 17, 24)
        c.append(piece_icon(piece, ch))
        c.append(f'<g transform="translate({cw - 112:g} {ch - 104}) scale(0.32)">{"".join(seed_svg(seed))}</g>')
        b += card(cx, cy, cw, ch, f"pregunta-{i + 1}") + [group(f"pregunta-{i + 1}-contenido", c, cx, cy)]
    return b


PREVIEW = (  # el mismo caso del resultado amarillo (diagnostico.py, muestra.SIGNALS_CASE), rotulado como ejemplo (R5)
    ("water", "Agua", "favorable", "86/100 · alcanzó en 7 de 10 años"),
    ("frost", "Heladas", "moderado", "58/100 · heló 12 de cada 100 años"),
    ("heat", "Calor", "favorable", "94/100 · aguanta hasta 28 °C"),
    ("soil", "Suelo", "favorable", "80/100 · pH apto (estimado)"),
    ("supply", "Oferta", "desfavorable", "30/100 · +35 % de área sembrada"),
    ("market", "Mercado", "insuficiente", "Sin datos de precios"),
)


def example_label(x, y):
    """Rótulo de ejemplo del kit: estos datos no son reales (R5)."""
    return [group("rotulo-ejemplo", [poly([(14, 0), (118, 0), (118, 32), (14, 32), (0, 16)], P["calabaza"], D["calabaza"], 2),
                                      f'<circle cx="14" cy="16" r="4" fill="{WHITE}" stroke="{D["calabaza"]}" stroke-width="2"/>',
                                      text(68, 22, "Ejemplo", 15, 700, anchor="middle")], x, y)]


def preview(y0, w, mobile):
    """Así se ve una consulta: un resultado de muestra con la acción primero y las seis señales."""
    h = 1320 if mobile else 720
    b = [f'<rect y="{y0}" width="{w}" height="{h}" fill="#E9F0E1"/>']
    pad = 20 if mobile else 96
    b.append(text(pad, y0 + (80 if mobile else 100), "Así se revisa un ciclo", 30 if mobile else 44, 600, font=FONT_TITLE))
    b += paragraph(pad, y0 + (118 if mobile else 144), ["Papa en Samacá, sembrando el 2 de agosto", "de 2027. Cifras de muestra."] if mobile else
                   ["Papa en Samacá, sembrando el 2 de agosto de 2027. Primero lo que conviene hacer; después, por qué. Cifras de muestra."], 16 if mobile else 20, 24, fill=SEC)
    cw = w - 2 * pad
    cy = y0 + (180 if mobile else 190)
    c = example_label(24 if mobile else 32, 24)
    c += light("amarillo", 24 if mobile else 32, 76, 0.5)
    if mobile:
        c += [text(24, 170, "Mejor otro cultivo", 28, 600, font=FONT_TITLE), text(24, 204, "en esta fecha", 28, 600, font=FONT_TITLE)]
        c += paragraph(24, 238, ["Se está sembrando mucha más papa", "que antes en Samacá. El clima de", "esta fecha sí le sirve."], 16, 23)
        ry, row_w, row_h = 330, cw - 48, 104
    else:
        c += [text(32, 190, "Mejor otro cultivo en esta fecha", 34, 600, font=FONT_TITLE)]
        c += paragraph(32, 228, ["Se está sembrando mucha más papa que antes", "en Samacá. El clima de esta fecha sí le sirve:", "agua y calor bien, heladas moderadas."], 18, 26)
        c += button(32, 310, 340, "Pruébelo con su municipio")
        ry, row_w, row_h = 30, 560, 64
    rx = 24 if mobile else cw - 32 - row_w
    for i, (k, name, status, reason) in enumerate(PREVIEW):
        yy = ry + i * row_h
        row = [poly(chamfer(0, 0, row_w, row_h - 10, 10), "#F5F8F2" if status != "insuficiente" else WHITE, BORDE if status != "insuficiente" else D["cielo"],
                    1.5, None if status != "insuficiente" else "3 5")]
        row += [f'<g transform="translate(10 6) scale(0.95)">{"".join(kind(KEY_TO_KIND[k], 0, 0))}</g>', text(66, 26, name, 18, 700), text(66, 46, reason, 14, fill=SEC)]
        tw = 150 if mobile else 168
        row += tag(row_w - tw - 12, (row_h - 10) / 2 - 17, status, tw, 34) if not mobile else tag(66, 56, status, tw, 28)
        c.append(group(f"vista-{k}", row, rx, yy))
    if mobile:
        by = ry + len(PREVIEW) * row_h + 10
        c += button(24, by, cw - 48, "Pruébelo con su municipio")
        ch = by + 90
    else:
        ch = 440
    b += card(pad, cy, cw, ch, "ejemplo-de-consulta") + [group("ejemplo-de-consulta-contenido", c, pad, cy)]
    return b


def piece_icon(piece, ch=290):
    """Pieza del kit en pequeño, como ícono de cada pregunta. Va al pie de la tarjeta, de alto `ch`."""
    dy = ch - 290
    if piece == "heladas":  # el cristal de la señal de heladas
        return f'<g transform="translate(28 {160 + dy}) scale(1.5)">{"".join(kind("heladas", 0, 0))}</g>'
    if piece == "rotulo-estimacion":  # gota facetada, como la del rótulo de estimación
        return (f'<g transform="translate(28 {168 + dy}) scale(2)"><polygon points="12,1 22,17 18,27 6,27 2,17" fill="#8FA9B8" stroke="#4A6576" stroke-width="2" stroke-linejoin="round"/>'
                '<polygon points="12,1 22,17 18,27 12,27" fill="#4A6576"/></g>')
    markup = PIECES[piece]
    return f'<g transform="translate(28 {162 + dy}) scale(0.7)">{markup[markup.index(">") + 1 : markup.rindex("</svg>")]}</g>'


def seed_svg(seed):
    from semilla_sputnik import seed_mascot

    return seed_mascot("reposo", seed)


def sources(y0, w, mobile):
    h = 1180 if mobile else 560
    b = [f'<rect y="{y0}" width="{w}" height="{h}" fill="{P["cielo"]}"/>']
    pad = 20 if mobile else 96
    b.append(text(pad, y0 + 90, "De dónde salen los datos", 30 if mobile else 44, 600, font=FONT_TITLE))
    b += paragraph(pad, y0 + 132, ["Datos abiertos y reglas que se pueden leer.", "Cada respuesta dice de dónde sale."] if mobile else
                   ["Datos abiertos y reglas que se pueden leer. Cada respuesta dice de dónde sale y qué versión de los datos usó."], 16 if mobile else 20, 26)
    cw = 350 if mobile else (w - 2 * pad - 3 * 24) / 4
    for i, (kind, name, rows) in enumerate(SOURCES):
        cx, cy = (pad, y0 + 200 + i * 190) if mobile else (pad + i * (cw + 24), y0 + 190)
        c = [text(28, 46, kind.upper(), 14, 700, SEC), text(28, 80, name if len(name) < 26 else "EVA", 24, 600, font=FONT_TITLE)]
        if len(name) >= 26:
            c.append(text(28, 104, "Evaluaciones Agropecuarias", 15, fill=SEC))
        c += paragraph(28, 132 if len(name) >= 26 else 112, rows, 16, 22)
        b += card(cx, cy, cw, 170 if mobile else 190, f"fuente-{kind.lower()}") + [group(f"fuente-{kind.lower()}-contenido", c, cx, cy)]
    ny = y0 + (980 if mobile else 410)
    note = [poly([(0, 0), (8, 0), (8, 70 if not mobile else 120), (0, 70 if not mobile else 120)], P["calabaza"])]
    note += paragraph(24, 30, ["AgroSense no adivina el futuro:", "le muestra el riesgo histórico", "de su zona. No es un pronóstico."] if mobile else
                      ["AgroSense no adivina el futuro: le muestra el riesgo histórico de su zona con reglas que puede leer. No es un pronóstico."], 16 if mobile else 18, 24, weight=700)
    note += link(24, 108 if mobile else 60, "¿Cómo funciona?" if mobile else "¿Cómo funciona y de dónde sale esto?", 16)
    b.append(group("aviso", note, pad, ny))
    return b


def landing(mobile=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    hero_h = 844 if mobile else 900
    q_h = Q_H[mobile]
    p_h = 1320 if mobile else 720
    s_h = 1180 if mobile else 560
    foot, f_h = ui.footer(w, 0, mobile, above=P["cielo"])
    h = hero_h + q_h + p_h + s_h + f_h
    b = hero(w, hero_h, mobile)
    b += questions(hero_h, w, mobile)
    b += preview(hero_h + q_h, w, mobile)
    b += sources(hero_h + q_h + p_h, w, mobile)
    b.append(f'<g transform="translate(0 {hero_h + q_h + p_h + s_h})">{"".join(foot)}</g>')
    return svg(w, h, [f'<rect width="{w}" height="{h}" fill="{P["cielo"]}"/>'] + b)


# ---------- Buscar mi municipio ----------

RESULTS = (("Samacá", "Boyacá"), ("Saboyá", "Boyacá"), ("Santa Sofía", "Boyacá"), ("Sativanorte", "Boyacá"))


def find_municipality(mobile=False):
    w, h = MOBILE if mobile else DESKTOP
    b = scene("a3-region", w, h, "recorte-buscar" + ("-m" if mobile else ""))
    b += topbar(w)
    if mobile:
        b += stepper(12, 92, 366, 1, True)
        x, y, cw, pad = 12, 186, 366, 22
    else:
        b += stepper(96, 116, 640, 1)
        b += mascot(820, 170, 1.4, "vuelo")
        x, y, cw, pad = 96, 216, 560, 40
    fw = cw - 2 * pad
    c = [text(pad, 56, "PASO 1 DE 2", 15, 700, SEC), text(pad, 102, "¿Dónde está su finca?", 28 if mobile else 40, 600, font=FONT_TITLE),
         text(pad, 138, "Escriba su municipio; puede ser sin tildes.", 16 if mobile else 18)]
    c += field(pad, 186, fw, "Municipio", "sa", state="foco", name="campo-municipio")
    c += dropdown(pad, 254, fw, RESULTS)
    c += paragraph(pad, 534, ["Solo aparecen los municipios de la región", "piloto. Si no está el suyo, aún no tenemos", "sus datos."] if mobile else
                   ["Solo aparecen los municipios de la región piloto.", "Si no está el suyo, aún no tenemos sus datos."], 15, 22, fill=SEC)
    ch = 534 + (3 if mobile else 2) * 22 + 20
    b += card(x, y, cw, ch) + [group("contenido", c, x, y)]
    return frame((w, h), b)


SCREENS = {
    "inicio-01-portada-escritorio": lambda: landing(),
    "inicio-01-portada-movil": lambda: landing(mobile=True),
    "descenso-01-buscar-municipio-escritorio": lambda: find_municipality(),
    "descenso-01-buscar-municipio-movil": lambda: find_municipality(mobile=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
