"""Tanda 11 · Estados que faltaban del resultado (HU-092, HU-094). Escritorio y móvil.

El resultado del diagnóstico (diagnostico.py) ya tenía amarillo, dos luces, rojo, rojo sin fechas, no evaluable y
«no se da en su zona». Faltaban:

- **Luz verde, y con riego.** La acción es «Sembrar en esta fecha». Con riego, la falta de lluvia no es un riesgo:
  la señal de agua es favorable y su razón dice cuánto riego haría falta, como estimación (R10).
- **Lo que se ve mientras llega o cuando no llega el resultado:** cargando (la forma de lo que viene, sin datos
  inventados), un error del servidor con su código para soporte, un municipio sin cobertura, una entrada que la API
  no acepta (422) dicha en palabras sencillas, y sin conexión.

Qué hace cada control: «Reintentar» repite POST /diagnostics; «Reportar» abre «Reportar un problema» con el código;
«Buscar otro municipio» y «Cambiar la fecha» vuelven a «Elegir» con ese campo abierto.
Los nombres y las cifras son de muestra.

    python design/pantallas/estados_resultado.py     # escribe svg/consulta-02-resultado-verde-riego-* y svg/consulta-06-estados-del-resultado-*
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
import muestra as m  # noqa: E402
import diagnostico as dg  # noqa: E402
from calendario import wrap_lines  # noqa: E402
from transversal import state_card  # noqa: E402
from ui import BORDE, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, chamfer, frame, group, mascot, paragraph, poly, text, topbar  # noqa: E402

# Papa en Samacá, sembrando el 1 de marzo de 2027, con riego. Las notas son las de marzo en `muestra._W`; con riego,
# el agua no depende de la lluvia. La oferta es moderada: no hay nada desfavorable y el agua es favorable -> verde.
m.CASES["verde-riego"] = dict(
    crop="Papa", town="Samacá", kicker="PAPA · SIEMBRA 1 MAR 2027 → COSECHA ESTIMADA ~26 JUL · SAMACÁ", suitability=m.SUITABILITY,
    signals=dict(
        water=dict(score=92, critical=False, reasons=["Con riego, que no llueva no es", "un riesgo. Haría falta regar de", "20 a 45 mm en jun y jul (estimación)."], note="Con riego"),
        frost=dict(score=80, critical=False, reasons=["Heló en la floración (jun)", "1 de cada 100 años."], note=None),
        heat=dict(score=94, critical=False, reasons=["La máxima rara vez pasa de", "22 °C; la papa aguanta", "hasta 28 °C."], note=None),
        soil=dict(score=80, critical=False, reasons=["pH estimado 5,2 a 5,8: en", "el rango de la papa.", "Estimación de 250 m."], note=None),
        supply=dict(score=68, critical=False, reasons=["En 2025 A, área sembrada", "algo mayor que en los tres", "semestres A anteriores."], note=None),
        market=dict(score=None, critical=False, reasons=["Sin datos de precios", "para Samacá."], note=None),
    ),
)
dg.TEXTS["verde-riego"] = dict(
    reasons=["En esta fecha no hay nada en contra: el agua, las heladas, el calor y el suelo le sirven a la papa.",
             "Lo que más limita es la oferta, y es moderada. Con riego, los meses secos no son un riesgo."],
    buttons=("Crear cuenta y registrarla", "Ver estrategias de rotación"),
    limits=["Evaluado con riego, como usted indicó: el riego que haría falta es una estimación con el clima de la zona.",
            "El suelo es el estimado para el municipio, no para su lote.", "Sin datos de mercado: el precio no se evaluó."])

STATES = (
    ("Algo falló de nuestro lado", ["No pudimos calcular su diagnóstico. No es su culpa: lo que eligió sigue aquí. Vuelva a intentar en un momento."], "reposo",
     (("Reintentar", "primary"), ("Reportar", "secondary")), "9b1e-42c7", False),
    ("Sin datos de este municipio", ["AgroSense cubre la región piloto. No inventamos un resultado: puede consultar un municipio cercano que sí esté."], "sin-datos",
     (("Buscar otro municipio", "secondary"),), None, True),
    ("Esa fecha no se puede consultar", ["Elija un mes de los próximos doce: una fecha que ya pasó o más lejana no tiene ventana que evaluar."], "guia",
     (("Cambiar la fecha", "primary"),), None, False),
    ("Sin conexión", ["Revise la señal. Lo que ya consultó sigue en pantalla; para calcular otra fecha hace falta internet."], "reposo",
     (("Reintentar", "primary"),), None, False),
)


def loading(x, y, w, mobile=False):
    """Cargando el resultado: la forma de lo que viene (la luz, la acción y seis señales), sin un solo dato inventado."""
    cols = 2 if mobile else 6
    gw = (w - 48 - (cols - 1) * 10) / cols
    rows = 3 if mobile else 1
    h = 190 + rows * 88
    body = [poly(chamfer(0, 8, w, h, 16), BORDE), poly(chamfer(0, 0, w, h, 16), WHITE)]
    body += [f'<g transform="translate({w - 118} 12) scale(0.32)">{"".join(mascot(0, 0, 1, "vuelo"))}</g>']
    body += [text(24, 46, "Calculando…" if mobile else "Calculando su diagnóstico…", 21 if mobile else 22, 600, font=FONT_TITLE),
             text(24, 74, "Papa · 2 ago 2027" if mobile else "Papa · siembra 2 ago 2027 · Samacá", 15, fill=SEC)]
    body += [poly(chamfer(24, 96, 150, 44, 8), P["niebla"]), poly(chamfer(190, 100, max(110, (w - 330) * 0.7), 16, 4), P["niebla"]), poly(chamfer(190, 124, max(70, (w - 330) * 0.45), 12, 4), P["niebla"])]
    for i in range(6):
        cx, cy = 24 + (i % cols) * (gw + 10), 168 + (i // cols) * 88
        body += [poly(chamfer(cx, cy, gw, 76, 8), "#F4F6F8", BORDE, 1.5), poly(chamfer(cx + 12, cy + 14, gw * 0.5, 12, 3), P["niebla"]),
                 poly(chamfer(cx + 12, cy + 38, gw - 24, 10, 3), P["niebla"]), poly(chamfer(cx + 12, cy + 56, (gw - 24) * 0.6, 8, 3), P["niebla"])]
    return [group("estado-cargando-resultado", body, x, y)], h


def states(mobile=False):
    w = MOBILE[0] if mobile else 1440
    pad = 16 if mobile else 96
    cw = w - 2 * pad
    b = [f'<rect width="{w}" height="6000" fill="{P["niebla"]}"/>'] + topbar(w, "Consultar")
    b.append(text(pad, 150 if mobile else 180, "Estados del resultado", 28 if mobile else 48, 600, font=FONT_TITLE))
    intro = (["Lo que se ve mientras llega el diagnóstico", "o cuando no llega. Nunca se inventa un", "resultado para llenar el espacio."] if mobile else
             ["Lo que se ve mientras llega el diagnóstico o cuando no llega. Nunca se inventa un resultado para llenar el espacio."])
    b += paragraph(pad, 186 if mobile else 220, intro, 16, 23, fill=SEC)
    y = (186 if mobile else 220) + len(intro) * 23 + 20
    lc, lh = loading(pad, y, cw, mobile)
    b += lc
    y += lh + 28
    cols = 1 if mobile else 2
    gw = (cw - (cols - 1) * 24) / cols
    heights = []
    for title, rows, mood, buttons, code, dashed in STATES:
        lines = wrap_lines([" ".join(rows)], int((gw - 140) / 7.4))
        heights.append(78 + len(lines) * 22 + 10 + (50 if code else 0) + (len(buttons) * 64 if mobile else (64 if buttons else 0)) + 20)
    hmax = max(heights)
    for i, (title, rows, mood, buttons, code, dashed) in enumerate(STATES):
        if mobile:
            b += state_card(pad, y, gw, heights[i], title, rows, mood, buttons, code, dashed, True)
            y += heights[i] + 28
        else:
            b += state_card(pad + (i % cols) * (gw + 24), y + (i // cols) * (hmax + 28), gw, hmax, title, rows, mood, buttons, code, dashed)
    if not mobile:
        y += ((len(STATES) + 1) // 2) * (hmax + 28)
    note = (["Borde punteado: no hay datos, no es un error.", "El código para soporte es el request_id."] if mobile else
            ["Borde punteado: no hay datos, no es un error. El código para soporte es el request_id de la respuesta (cabecera X-Request-ID). «Sin datos» nunca se pinta como riesgo (R1)."])
    b += paragraph(pad, y + 20, note, 14, 21, fill=SEC)
    return frame((w, y + 100), b, P["niebla"])


SCREENS = {
    "consulta-02-resultado-verde-riego-escritorio": lambda: dg.result(case_key="verde-riego"),
    "consulta-02-resultado-verde-riego-movil": lambda: dg.result(mobile=True, case_key="verde-riego"),
    "consulta-06-estados-del-resultado-escritorio": lambda: states(),
    "consulta-06-estados-del-resultado-movil": lambda: states(mobile=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
