"""Tanda 12 · «Precios en la central de abastos» (HU-221). Escritorio y móvil.

El último precio por kilo de cada producto en Corabastos o en Tunja (SIPSA del DANE) y, al abrir uno, su último año y en
qué meses suele estar más caro o más barato. Es historia de precios, nunca pronóstico (decisión 4): la pantalla lo dice.
Se puede ver sin cuenta. La pantalla ya está programada (web/src/pages/prices/): esta lámina la describe para revisarla
y aprobarla en Figma.

Las cifras son **reales**: SIPSA del 19 de octubre de 2026 en Corabastos, copiadas a mano de `GET /api/v1/market/prices`
(la serie del último año, una de cada seis). No son de `muestra.py`, que cuenta el caso de Rosa con cifras de muestra.

    python design/pantallas/precios.py     # escribe svg/precios-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402
from cuenta import wrap  # noqa: E402
from ui import BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, field, group, paragraph, poly, text, topbar, width_of  # noqa: E402

DATE = "19 de octubre de 2026"
MARKET = "Corabastos (Bogotá)"
# La cita textual que piden los términos del DANE (HU-221), igual que en la pantalla.
SOURCE = "Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co. Datos de SIPSA, precios mayoristas diarios."
NOT_FORECAST = "Así se ha movido el precio en la central. No es un pronóstico."

# (producto, junta variedades, precio medio por kilo, cambio en una semana en %, fecha del último precio si no es hoy).
GROUPS = (
    ("Tubérculos, raíces y plátanos", [
        ("Arracacha", True, 4021, -23.4, None),
        ("Papa criolla", False, 4972, -24.2, None),
        ("Papa negra", True, 2925, -7.1, None),
        ("Plátano hartón verde", False, 2813, -9.1, None),
        ("Yuca", True, 2521, 2.6, None),
    ]),
    ("Verduras y hortalizas", [
        ("Arveja verde en vaina", False, 6675, 8.1, None),
        ("Cebolla cabezona blanca", False, 2313, -13.5, None),
        ("Habichuela", False, 6750, 43.4, None),
        ("Remolacha", False, 1396, 0.0, None),
        ("Zanahoria", False, 1583, -14.6, None),
    ]),
    ("Frutas", [
        ("Mora de Castilla", False, 9583, 48.4, None),
        ("Papaya maradol", False, 2350, None, "31 de julio de 2021"),
    ]),
)

# Papa negra en Corabastos: el último año (una fecha de cada seis) y su temporada de 2021 a 2025.
SERIES = [838, 825, 755, 1113, 1213, 1163, 1053, 1213, 1038, 1150, 1250, 1513, 1450, 1950, 1763, 1925, 1725, 1700, 1550,
          1500, 1650, 1650, 1713, 1538, 1638, 1538, 1563, 1638, 1642, 1475, 1713, 2088, 2050, 2263, 1900, 1625, 1588, 1738,
          1771, 1875, 1746, 2200, 2200, 2325, 2550, 2538, 2500, 2375, 2500, 2513, 3075, 3088, 2925]
SERIES_TICKS = ("20 oct", "19 feb", "19 jun", "19 oct")
SEASON = (1.063, 1.066, 1.167, 1.259, 1.177, 0.942, 0.884, 0.795, 0.774, 0.841, 0.961, 1.07)
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic")

TEAM_NOTE = ("Cifras reales de SIPSA del 19 de octubre de 2026, copiadas a mano de la API. La pantalla ya está",
             "programada (/precios): esta lámina es para revisarla. Este recuadro no se dibuja en la app.")


def pesos(value):
    """«$ 2.925», como Intl.NumberFormat("es-CO") en la web."""
    return "$ " + f"{value:,}".replace(",", ".")


def change_mark(change, x, y):
    """Flecha con forma propia: sube (triángulo calabaza), baja (triángulo cielo) o igual (raya)."""
    if change == 0:
        return [poly([(x, y - 7), (x + 14, y - 7), (x + 14, y - 4), (x, y - 4)], SEC)]
    if change > 0:
        return [poly([(x + 7, y - 13), (x + 14, y), (x, y)], P["calabaza"], D["calabaza"], 1.5)]
    return [poly([(x, y - 12), (x + 14, y - 12), (x + 7, y + 1)], P["cielo"], D["cielo"], 1.5)]


def change_text(change):
    if change == 0:
        return "Igual que hace una semana"
    number = f"{abs(change):.1f}".replace(".", ",").replace(",0", "")
    return f"{'Sube' if change > 0 else 'Baja'} {number} % en una semana"


def product_row(w, name, several, price, change, stale, selected=False):
    """Una fila de la lista: nombre a la izquierda; precio y cambio a la derecha."""
    h = 66
    body = [poly(chamfer(0, 0, w, h, 0), "#E9F2D8" if selected else WHITE, D["oliva"] if selected else BORDE, 2)]
    # El nombre siempre en la primera línea: centrado chocaría con el cambio de precio de la segunda en el celular.
    body.append(text(16, 30, name, 18, 700))
    if several:
        body.append(text(16, 52, "Varias variedades", 13, fill=SEC))
    body.append(text(w - 44, 30, pesos(price), 18, 700, anchor="end"))
    body.append(text(w - 14, 30, "/kg", 14, fill=SEC, anchor="end"))
    if stale:
        body.append(text(w - 14, 52, f"Último precio: {stale}", 13, 700, D["calabaza"], anchor="end"))
    else:
        label = change_text(change)
        body.append(text(w - 14, 52, label, 13, fill=SEC, anchor="end"))
        body += change_mark(change, w - 14 - width_of(label, 13) - 20, 52)
    return [group(f"fila-{name.lower().replace(' ', '-')}", body)], h


def product_list(w, groups=GROUPS, selected=None):
    body, y = [], 0
    for title, rows in groups:
        body.append(text(0, y + 14, title.upper(), 14, 700, SEC))
        y += 26
        for row in rows:
            r, h = product_row(w, *row, selected=row[0] == selected)
            body.append(group(f"producto-{row[0].lower().replace(' ', '-')}", r, 0, y))
            y += h + 8
        y += 18
    return body, y


def market_choice(x, y, w):
    """«Central de abastos»: dos opciones a la vista, la elegida rellena en verde oliva (como «¿Este lote tiene riego?»)."""
    body = [text(0, 0, "Central de abastos", 18, 700)]
    bw = (w - 10) / 2
    for i, (label, on) in enumerate((("Corabastos", True), ("Tunja", False))):
        bx = i * (bw + 10)
        body.append(poly(chamfer(bx, 14, bw, 52, 10), D["oliva"] if on else WHITE, ui.OLIVA_CANTO if on else BORDE, 2))
        body.append(text(bx + bw / 2, 47, label, 18, 700, WHITE if on else P["noche"], anchor="middle"))
    body.append(text(0, 92, MARKET, 15, fill=SEC))
    return [group("central-de-abastos", body, x, y)]


def price_chart(w, h=210):
    """El precio medio del último año: línea oliva sobre tres guías con su valor."""
    left, right, top, bottom = 62, 8, 12, 26
    lo, hi = 0, 4000
    pw, ph = w - left - right, h - top - bottom
    x = lambda i: left + i * pw / (len(SERIES) - 1)  # noqa: E731
    y = lambda v: top + (1 - (v - lo) / (hi - lo)) * ph  # noqa: E731
    body = []
    for value in (0, 2000, 4000):
        body.append(f'<rect x="{left}" y="{y(value):.1f}" width="{pw}" height="1" fill="{BORDE}"/>')
        body.append(text(left - 6, y(value) + 4, pesos(value), 12, fill=SEC, anchor="end"))
    line = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(SERIES))
    body.append(f'<polyline points="{line}" fill="none" stroke="{D["oliva"]}" stroke-width="2.5" stroke-linejoin="round"/>')
    for i, label in enumerate(SERIES_TICKS):
        anchor = "end" if i == 0 else "start" if i == len(SERIES_TICKS) - 1 else "middle"
        tx = left + i * pw / (len(SERIES_TICKS) - 1)
        body.append(text(tx + (24 if i == 0 else -24 if i == len(SERIES_TICKS) - 1 else 0), h - 6, label, 12, fill=SEC, anchor=anchor))
    return body


def season_chart(w, h=210):
    """Barras desde la línea del promedio del año: arriba más caro (calabaza), abajo más barato (cielo), con su %."""
    top, bottom, side = 22, 44, 4
    zero = top + (h - top - bottom) / 2
    percents = [round((i - 1) * 100) for i in SEASON]
    scale = (h - top - bottom) / 2 / max(10, *map(abs, percents))
    slot = (w - 2 * side) / 12
    body = []
    for i, p in enumerate(percents):
        cx = side + slot * i + slot / 2
        bh = abs(p) * scale
        above = p > 0
        body.append(f'<rect x="{cx - slot * 0.32:.1f}" y="{(zero - bh if above else zero):.1f}" width="{slot * 0.64:.1f}" height="{max(bh, 1):.1f}" '
                    f'fill="{P["calabaza"] if above else P["cielo"]}" stroke="{D["calabaza"] if above else D["cielo"]}" stroke-width="1.5"/>')
        body.append(text(cx, zero - bh - 6 if above else zero + bh + 16, f"+{p}" if p > 0 else str(p), 11, 700, anchor="middle"))
        body.append(text(cx, h - 6, MONTHS[i], 11, fill=SEC, anchor="middle"))
    body.append(f'<rect x="{side}" y="{zero - 0.75:.1f}" width="{w - 2 * side}" height="1.5" fill="{P["noche"]}"/>')
    return body


def detail(w, mobile=False):
    """La tarjeta de un producto: su último precio, su último año, su temporada, el rótulo y la fuente."""
    pad = 22 if mobile else 32
    iw = w - 2 * pad
    c, y = [], 44
    c.append(text(pad, y, "Papa negra", 26 if mobile else 30, 600, font=FONT_TITLE))
    y += 28
    sub = f"{MARKET} · el DANE junta varias variedades"
    for row in wrap(sub, 38 if mobile else 70):
        c.append(text(pad, y, row, 15, fill=SEC))
        y += 22
    y += 30
    c.append(text(pad, y, pesos(2925), 40, 700))
    c.append(text(pad + len(pesos(2925)) * 40 * 0.5 + 14, y, "por kilo", 18))
    y += 28
    for row in wrap(f"Precio medio del {DATE}. Entre {pesos(2800)} y {pesos(3000)} por kilo.", 44 if mobile else 80):
        c.append(text(pad, y, row, 15, fill=SEC))
        y += 22
    y += 26
    c.append(text(pad, y, "El último año", 20, 600, font=FONT_TITLE))
    y += 10
    c.append(group("grafica-ultimo-ano", price_chart(iw), pad, y))
    y += 226
    caption = ("La línea es el precio medio de cada día; la franja, el mínimo y el máximo. Precio medio más bajo: "
               f"{pesos(750)} el 29 de oct. Más alto: {pesos(3150)} el 12 de oct.")
    for row in wrap(caption, 44 if mobile else 80):
        c.append(text(pad, y, row, 15, fill=SEC))
        y += 22
    y += 26
    for row in wrap("¿En qué meses suele estar más caro?", 30 if mobile else 60):
        c.append(text(pad, y, row, 20, 600, font=FONT_TITLE))
        y += 28
    for row in wrap("Suele estar más barato en septiembre (-23 %) y más caro en abril (+26 %) que el promedio de su año.", 40 if mobile else 72):
        c.append(text(pad, y, row, 17))
        y += 25
    c.append(group("grafica-temporada", season_chart(iw), pad, y))
    y += 228
    note = ("Cada barra compara el precio de ese mes con el promedio de su mismo año, en %: así no cuenta la inflación. "
            "Con los años completos de 2021 a 2025.")
    for row in wrap(note, 44 if mobile else 80):
        c.append(text(pad, y, row, 15, fill=SEC))
        y += 22
    y += 14
    rows = wrap(NOT_FORECAST, 34 if mobile else 70)
    nh = 24 + len(rows) * 24
    c.append(group("rotulo-no-es-pronostico", [poly([(0, 0), (iw, 0), (iw, nh), (0, nh)], P["niebla"]),
                                               poly([(0, 0), (8, 0), (8, nh), (0, nh)], P["calabaza"]),
                                               *paragraph(22, 30, rows, 17, 24, weight=700)], pad, y))
    y += nh + 30
    for row in wrap(SOURCE, 46 if mobile else 84):
        c.append(text(pad, y, row, 14, fill=SEC))
        y += 20
    y += 16
    c += button(pad, y, 260, "Ver todos los productos", "secondary")
    return c, y + 90


def team_note(x, y, w, mobile=False):
    rows = wrap(" ".join(TEAM_NOTE), 44) if mobile else list(TEAM_NOTE)
    nh = 24 + len(rows) * 20
    return [group("nota-equipo", [poly(chamfer(1, 1, w - 2, nh, 10), WHITE, D["cielo"], 2, "6 5"), *paragraph(16, 28, rows, 14, 20, fill=D["cielo"])], x, y)], nh


def header(pad, top, mobile):
    b = [text(pad, top - 44, "PRECIOS MAYORISTAS", 15, 700, SEC)]
    title = ["¿A cuánto se paga", "en la central?"] if mobile else ["¿A cuánto se paga en la central?"]
    b += paragraph(pad, top, title, 30 if mobile else 48, 38, weight=600, font=FONT_TITLE)
    y = top + (len(title) - 1) * 38 + (34 if mobile else 44)
    intro = ("El precio por kilo que el DANE registra cada día en la central de abastos. Es el precio al por mayor, lo "
             "que se paga en la central, no en la tienda.")
    rows = wrap(intro, 40 if mobile else 96)
    b += paragraph(pad, y, rows, 16 if mobile else 18, 24)
    return b, y + len(rows) * 24


def date_line(pad, y, limit):
    rows = wrap(f"Precios del {DATE} en {MARKET}. {SOURCE}", limit)
    return paragraph(pad, y, rows, 15, 22, fill=SEC), len(rows) * 22


def desktop():
    w, pad = 1440, 96
    b = [f'<rect width="{w}" height="9000" fill="{P["niebla"]}"/>'] + topbar(w, active="Precios")
    head, y = header(pad, 196, False)
    b += head
    y += 24
    b += market_choice(pad, y + 18, 420)
    b += field(pad + 460, y + 18, 420, "Buscar producto", placeholder="Por ejemplo, papa", name="campo-buscar")
    y += 136
    line, lh = date_line(pad, y, 120)
    b += line
    y += lh + 24
    lw = 560
    rows, list_h = product_list(lw, selected="Papa negra")
    b.append(group("lista-de-productos", rows, pad, y))
    dx, dw = pad + lw + 48, w - 2 * pad - lw - 48
    body, dh = detail(dw)
    b += card(dx, y, dw, dh, name="producto-abierto", c=16) + [group("contenido-producto", body, dx, y)]
    y += max(list_h, dh + 20) + 10
    note, nh = team_note(pad, y, 880)
    b += note
    return ui.long_page((w, y + nh + 60), b, P["niebla"])


def mobile_list():
    w, pad = MOBILE[0], 16
    b = [f'<rect width="{w}" height="9000" fill="{P["niebla"]}"/>'] + topbar(w)
    head, y = header(pad, 160, True)
    b += head
    y += 20
    b += market_choice(pad, y + 18, w - 2 * pad)
    y += 140
    b += field(pad, y + 18, w - 2 * pad, "Buscar producto", placeholder="Por ejemplo, papa", name="campo-buscar")
    y += 104
    line, lh = date_line(pad, y, 44)
    b += line
    y += lh + 20
    rows, list_h = product_list(w - 2 * pad)
    b.append(group("lista-de-productos", rows, pad, y))
    y += list_h
    note, nh = team_note(pad, y, w - 2 * pad, True)
    b += note
    return ui.long_page((w, y + nh + 50), b, P["niebla"])


def mobile_detail():
    """En el celular el producto abierto va arriba de la lista: se ve sin bajar."""
    w, pad = MOBILE[0], 12
    b = [f'<rect width="{w}" height="9000" fill="{P["niebla"]}"/>'] + topbar(w)
    line, lh = date_line(pad + 4, 112, 44)
    b += line
    y = 112 + lh + 6
    body, dh = detail(w - 2 * pad, mobile=True)
    b += card(pad, y, w - 2 * pad, dh, name="producto-abierto", c=14) + [group("contenido-producto", body, pad, y)]
    y += dh + 36
    rows, list_h = product_list(w - 2 * pad - 8, groups=GROUPS[:1], selected="Papa negra")
    b.append(group("lista-de-productos", rows, pad + 4, y))
    y += list_h
    note, nh = team_note(pad, y, w - 2 * pad, True)
    b += note
    return ui.long_page((w, y + nh + 50), b, P["niebla"])


SCREENS = {
    "precios-01-central-escritorio": desktop,
    "precios-01-central-movil": mobile_list,
    "precios-02-producto-movil": mobile_detail,
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
