"""Pantalla final «Las seis señales y gráficas» (rediseño, tanda 2; HU-093). Escritorio y móvil.

Una tarjeta por señal con su gráfica, en la ventana de siembra consultada: el agua frente a lo que necesita la papa
(con la textura del suelo), las heladas en las etapas sensibles, el calor frente a lo que aguanta, el pH del suelo,
la oferta con sus fuentes juntas (EVA y siembras registradas en AgroSense) y el mercado. Al final, cómo salió la
luz, paso a paso, con los pesos usados. Es la historia de la zona, no un pronóstico. Los datos salen de muestra.py.

    python design/pantallas/detalle.py     # escribe svg/consulta-03-senales-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
import muestra as m  # noqa: E402
import senales as sg  # noqa: E402
from consulta import bars, frost_chart, ph_scale  # noqa: E402
from ui import BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, chamfer, frame, group, link, paragraph, poly, shade, text, topbar  # noqa: E402


def water_chart(x, y, w, h, short=False):
    """Por año: la lluvia de los meses de la ventana (barra) frente a lo que el cultivo necesitaba (línea)."""
    out = [text(0, -14, "Lluvia de ago a dic frente a lo que necesita la papa (mm)" if not short else "Lluvia ago–dic vs. necesidad (mm)", 14, 700, SEC)]
    vmax = 600
    n = len(m.WATER_YEARS)
    bw = w / n * 0.6
    out.append(f'<rect x="0" y="{h}" width="{w}" height="2" fill="{P["noche"]}"/>')
    for t in (0.5, 1.0):
        ty = h - h * t
        out += [f'<rect x="0" y="{ty:.1f}" width="{w}" height="1" fill="{BORDE}"/>', text(-8, ty + 5, f"{round(vmax * t)}", 12, fill=SEC, anchor="end")]
    for i, (yr, rain, need) in enumerate(m.WATER_YEARS):
        bx = i * w / n + (w / n - bw) / 2
        bh = h * rain / vmax
        short_year = rain < need
        out.append(poly(chamfer(bx, h - bh, bw, bh, 3), P["cielo"] if not short_year else WHITE, D["cielo"], 1.5, None if not short_year else "4 3"))
        out.append(text(bx + bw / 2, h + 20, str(yr)[-2:], 12, fill=SEC, anchor="middle"))
    ny = h - h * m.WATER_YEARS[0][2] / vmax
    out += [f'<line x1="0" y1="{ny:.1f}" x2="{w}" y2="{ny:.1f}" stroke="{P["noche"]}" stroke-width="2" stroke-dasharray="8 5"/>',
            text(w, ny - 8, "Lo que necesita: 430 mm", 13, 700, anchor="end")]
    out += [poly(chamfer(0, h + 34, 16, 14, 2), WHITE, D["cielo"], 1.5, "4 3"), text(24, h + 46, "Años en que la lluvia no alcanzó: 3 de 10", 12, fill=SEC)]
    return [group("grafica-agua", out, x, y)]


def heat_chart(x, y, w, h):
    """Por mes de la ventana: la máxima que se supera uno de cada diez días, frente a lo que aguanta el cultivo."""
    out = [text(0, -14, "Máxima de 1 de cada 10 días, por mes (°C)", 14, 700, SEC)]
    vmax = 32
    n = len(m.TMAX_P90)
    bw = w / n * 0.5
    out.append(f'<rect x="0" y="{h}" width="{w}" height="2" fill="{P["noche"]}"/>')
    for i, (mon, t) in enumerate(m.TMAX_P90):
        bx = i * w / n + (w / n - bw) / 2
        bh = h * t / vmax
        out += [poly(chamfer(bx, h - bh, bw, bh, 3), shade(P["calabaza"], 0.25), D["calabaza"], 1.5),
                text(bx + bw / 2, h - bh - 6, f"{t:.0f}".replace(".", ","), 12, 700, anchor="middle"),
                text(bx + bw / 2, h + 20, mon, 12, fill=SEC, anchor="middle")]
    ly = h - h * m.HEAT_MAX_PAPA / vmax
    out += [f'<line x1="0" y1="{ly:.1f}" x2="{w}" y2="{ly:.1f}" stroke="{P["rojo"]}" stroke-width="2.5" stroke-dasharray="8 5"/>',
            text(w, ly - 8, f"La papa aguanta hasta {m.HEAT_MAX_PAPA} °C", 13, 700, D["rojo"], anchor="end")]
    return [group("grafica-calor", out, x, y)]


def sources_box(x, y, w):
    """Las fuentes de la oferta juntas, para contrastar; nunca mezcladas (decisión 11)."""
    a = m.AGROSENSE_SUPPLY
    rows = (("EVA (estadística oficial)", "+35 % de área en 2025 B, preliminar", "Calcula la señal"),
            ("Siembras en AgroSense", f"{a['ha']} ha en curso, {a['accounts']} cuentas, al {a['date']}", "Para contrastar"))
    out = [poly(chamfer(0, 0, w, 24 + len(rows) * 46, 10), "#F2F5F7", BORDE, 1.5), text(16, 22, "Fuentes de la oferta", 13, 700, SEC)]
    for i, (src, val, use) in enumerate(rows):
        ry = 48 + i * 46
        out += [text(16, ry, src, 14, 700), text(16, ry + 18, val, 13, fill=SEC)]
        out += [poly(chamfer(w - 136, ry - 16, 120, 24, 5), D["oliva"] if i == 0 else WHITE, None if i == 0 else BORDE, 0 if i == 0 else 1.5),
                text(w - 76, ry + 1, use, 12, 700, WHITE if i == 0 else P["noche"], anchor="middle")]
    return [group("fuentes-oferta", out, x, y)]


def detail_panel(x, y, w, h, key, sub, body_fn):
    """Tarjeta de una señal con su nota y su gráfica."""
    case = m.SIGNALS_CASE[key]
    status = m.level_of(case["score"], case.get("status"))
    ins = status == "insuficiente"
    out = [poly(chamfer(0, 8, w, h, 18), BORDE),
           poly(chamfer(0, 0, w, h, 18), WHITE, D["cielo"] if ins else None, 2.5 if ins else 0, "3 5" if ins else None)]
    if ins:
        out += sg.mist(w, h)
    narrow = w < 500
    out += sg.kind(sg.KEY_TO_KIND[key], 24, 22) + [text(80, 50, m.SIGNAL_NAME[key], 26, 600, font=FONT_TITLE)]
    out += sg.tag(24, 70, status, 176, 36) if narrow else sg.tag(w - 200, 24, status, 176, 38)
    if case["score"] is not None:
        out += sg.score_bar(24 if narrow else w - 200, 128 if narrow else 84, 176, case["score"])
    out += paragraph(24, 168 if narrow else 120, sub, 15, 21, fill=SEC)
    out += [f'<g transform="translate(0 {70 if narrow else 0})">{"".join(body_fn(w))}</g>']
    out += link(24, h - 22, "¿De dónde sale este dato?", 14)
    return [group(f"detalle-{key}", out, x, y)]


def signals(mobile=False):
    w = MOBILE[0] if mobile else DESKTOP[0]
    pad = 16 if mobile else 96
    pw = w - 2 * pad if mobile else (w - 2 * pad - 24) / 2
    ph = 640 if mobile else 560
    b = topbar(w, "Consultar", None if mobile else m.NAME)
    hy = 120 if mobile else 140
    head = link(0, 0, "← Volver al resultado", 16)
    head += [text(0, 48, "Las seis señales", 30 if mobile else 40, 600, font=FONT_TITLE)]
    head += paragraph(0, 82, ["Papa · siembra 2 ago 2027 · Samacá.", "Historia de la zona; no es pronóstico."] if mobile else
                      ["Papa · siembra el 2 de agosto de 2027, cosecha estimada el 27 de diciembre · Samacá. Historia de la zona; no es un pronóstico."], 16, 22, fill=SEC)
    b.append(group("encabezado", head, pad, hy))
    gw = lambda wp: wp - 100  # noqa: E731

    def water(wp):
        out = water_chart(64, 250, gw(wp), 130, short=wp < 500)
        out += paragraph(24, 448, ["Su suelo (franco arcillosa) guarda agua:", "entra en el cálculo."] if wp < 500 else ["Su suelo (franco arcillosa) guarda agua: entra en el cálculo."], 13, 18, fill=SEC)
        return out

    def frost(wp):
        return frost_chart(64, 250, gw(wp), 130, m.FROST, 7, m.PAPA_CYCLE_MONTHS, short=wp < 500)

    def heat(wp):
        return heat_chart(64, 250, gw(wp), 130)

    def soil(wp):
        out = ph_scale(40, 240, wp - 80)
        out += [text(40, 380, "Carbono orgánico: 32 g/kg (medio) · Textura: franco arcillosa", 13, 700) if wp >= 500 else
                text(40, 380, "Carbono: 32 g/kg (medio)", 13, 700)]
        return out

    def supply(wp):
        short = wp < 500
        out = bars(64, 220, gw(wp), 100, [v for _, v in m.AREA_B], [str(y_)[-2:] if short else str(y_) for y_, _ in m.AREA_B],
                   shade(P["trigo"], 0.2), D["trigo"], "Papa sembrada en el semestre B (ha), EVA",
                   ref=m.AREA_B_AVG3, ref_label="Prom. 3 anteriores: 843 ha", last_label="preliminar")
        out += sources_box(24, 372, wp - 48)
        return out

    def market(wp):
        return paragraph(24, 250, ["SIPSA no publica precios mayoristas de", "papa para esta zona.", "",
                                   "Sin datos, esta señal no califica: no", "cambia la luz y se lista en las", "limitaciones."], 16, 24)

    items = (
        ("water", ["En 7 de los últimos 10 años, la lluvia de", "agosto a diciembre cubrió lo que necesita", "la papa. Evaluado sin riego. Fuente: NASA POWER."], water),
        ("frost", ["Sembrando en agosto, heló en el llenado", f"(diciembre) {m.FROST[11]} de cada 100 años. Etapas", "sensibles: toda la papa en campo. NASA POWER."], frost),
        ("heat", ["De agosto a diciembre, la máxima rara vez", "pasa de 22 °C; la papa aguanta hasta", "28 °C. Fuente: NASA POWER; ficha: EcoCrop."], heat),
        ("soil", ["El pH estimado cae en el rango de la papa.", "Fuente: SoilGrids (ISRIC), celdas de 250 m.", "Un análisis de suelo es más preciso."], soil),
        ("supply", ["En 2025 B (último dato, preliminar) se", "sembró 35 % más que en los tres semestres", "B anteriores. Calcula: EVA."], supply),
        ("market", ["Sin datos de precios para Samacá.", "Fuente prevista: SIPSA (DANE)."], market),
    )
    gy = hy + (150 if mobile else 140)
    for i, (k, sub, fn) in enumerate(items):
        px, py = (pad, gy + i * (ph + 24)) if mobile else (pad + (i % 2) * (pw + 24), gy + (i // 2) * (ph + 24))
        b += detail_panel(px, py, pw, ph, k, sub, fn)
    # Cómo salió la luz, paso a paso (R2), con los pesos usados (R4)
    rx, ry = (pad, gy + 6 * (ph + 24)) if mobile else (pad, gy + 3 * (ph + 24))
    rw = pw if mobile else w - 2 * pad
    steps = (("0", "La papa se da en Samacá:", "aptitud 92/100."), ("1", "Agua y oferta tienen datos:", "se puede evaluar."),
             ("2", "Ninguna señal crítica y una sola", "desfavorable (oferta): no es rojo."), ("3", "Hay una desfavorable:", "no es verde."),
             ("4", "Queda amarillo. Como la oferta no", "cambia con la fecha: mejor otro cultivo."))
    r = [poly(chamfer(0, 8, rw, 0, 18), BORDE)]
    body = [text(24, 50, "Cómo salió el amarillo", 26, 600, font=FONT_TITLE),
            text(24, 76, "Con los pesos de AgroSense: agua 3 · heladas 3 · calor 3 · suelo 2 · oferta 3 · mercado 2", 13, fill=SEC) if not mobile else
            text(24, 76, "Con los pesos de AgroSense.", 13, fill=SEC)]
    cols = 1 if mobile else 3
    colw = (rw - 48) / cols
    for i, (n, a, c2) in enumerate(steps):
        cx, cy = 24 + (i % cols) * colw, 120 + (i // cols) * 74
        body += [poly(chamfer(cx, cy - 22, 36, 36, 6), P["trigo"] if i == 4 else P["niebla"]), text(cx + 18, cy + 2, n, 18, 700, anchor="middle"),
                 text(cx + 52, cy - 2, a, 15, 700), text(cx + 52, cy + 18, c2, 14, fill=SEC)]
    rh = 120 + ((len(steps) + cols - 1) // cols) * 74 + 40
    body += link(24, rh - 26, "Ver todas las reglas del semáforo", 15)
    r = [poly(chamfer(0, 8, rw, rh, 18), BORDE), poly(chamfer(0, 0, rw, rh, 18), WHITE)] + body
    b.append(group("como-se-decidio", r, rx, ry))
    h = ry + rh + 60
    b.append(text(pad, h - 20, f"{m.VERSIONS} · Pesos de AgroSense", 14, fill=SEC))
    foot, fh = ui.footer(w, h + 20, mobile, above=P["niebla"])
    return frame((w, h + 20 + fh), b + foot, P["niebla"])


SCREENS = {"consulta-03-senales-escritorio": lambda: signals(), "consulta-03-senales-movil": lambda: signals(mobile=True)}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
