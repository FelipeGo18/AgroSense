"""Pantalla «Editar lote» (rediseño, tanda 4, HU-164). Escritorio, móvil y la confirmación de borrar.

Se abre con «Editar lote» en la cabecera del lote. Cambia el nombre, el contorno (moviendo los puntos en el mapa) y
si el lote tiene riego (`irrigated`), con PATCH /lots/{id}. «Borrar este lote» llama a DELETE /lots/{id}: es reversible
durante 30 días desde «Borrados hace poco» en Mi finca (POST /lots/{id}/restore). Los nombres y las cifras son de muestra.

    python design/pantallas/editar.py     # escribe svg/finca-02-editar-lote-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from lote import G, LOT_OK, area_box, area_ha, attribution, draw_toolbar, fmt_ha, irrigation_question, lot_shape, area_chip, map_view, scale_bar, tool_button, zoom_controls  # noqa: E402
from finca import ALTO, crops_label, planted  # noqa: E402
from ui import BORDE, D, DESKTOP, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, field, frame, group, link, paragraph, poly, text, topbar  # noqa: E402

SOWN = sum(p["area"] for p in planted(ALTO))  # área ocupada por los cultivos en curso
UNTIL = "10 de noviembre"  # hoy, 11 de octubre, más 30 días


def note(x, y, w, rows, size=14):
    h = 24 + len(rows) * 20
    body = [poly(chamfer(0, 0, w, h, 10), "#EEF2E4"), *paragraph(16, 28, rows, size, 20)]
    return [group("nota-riego", body, x, y)], h


def form(pad, fw, compact=False):
    """Campos del lote: área, nombre, zona, riego y la nota de qué cambia. Devuelve las piezas y el alto."""
    c = area_box(pad, 0, fw, LOT_OK)
    c += paragraph(pad, 112, ["Mueva los puntos en el mapa para cambiar el", "contorno. No puede quedar más chico que lo", f"sembrado ({fmt_ha(SOWN)})."] if compact else
                   ["Mueva los puntos en el mapa para cambiar el contorno.", f"No puede quedar más chico que lo sembrado ({fmt_ha(SOWN)})."], 14, 20, fill=SEC)
    y = 112 + (3 if compact else 2) * 20 + 14
    c += field(pad, y, fw, "Nombre del lote", "El Alto", name="campo-nombre")
    y += 104
    c += [text(pad, y, "Zona", 18, 700), text(pad, y + 26, "Samacá, Boyacá", 17)]
    c += paragraph(pad, y + 50, ["El contorno debe quedar dentro del municipio."], 14, fill=SEC)
    y += 86
    rq, rh = irrigation_question(pad, y, fw, on=1, compact=compact)
    c += rq
    y += rh + 14
    rows = (["Al cambiar el riego se recalculan el", "diagnóstico, el calendario y el agua de", "este lote. Las siembras ya registradas", "guardan el diagnóstico que vieron."] if compact else
            ["Al cambiar el riego se recalculan el diagnóstico, el calendario", "y el agua de este lote. Las siembras ya registradas", "guardan el diagnóstico que vieron."])
    nt, nh = note(pad, y, fw, rows)
    c += nt
    return c, y + nh


def delete_block(pad, fw, y, compact=False):
    c = [f'<rect x="{pad}" y="{y}" width="{fw}" height="2" fill="{BORDE}"/>', text(pad, y + 40, "Borrar este lote", 18, 700)]
    rows = ([f"Deja de verse con sus {len(planted(ALTO))} cultivos en curso", "y su historial. Puede restaurarlo durante", "30 días desde Mi finca."] if compact else
            [f"Deja de verse con sus {len(planted(ALTO))} cultivos en curso y su historial.", "Puede restaurarlo durante 30 días desde Mi finca."])
    c += paragraph(pad, y + 66, rows, 15, 21, fill=SEC)
    by = y + 66 + len(rows) * 21 + 6
    c += button(pad, by, min(fw, 240), "Borrar este lote", "danger")
    return c, by + 52


def desktop():
    w = DESKTOP[0]
    pad, cw = 30, 440
    fw = cw - 2 * pad
    f, fh = form(pad, fw)
    c = [text(pad, 48, "EDITAR LOTE", 15, 700, SEC), text(pad, 92, "El Alto", 34, 600, font=FONT_TITLE),
         text(pad, 120, f"{crops_label(ALTO)} · {fmt_ha(area_ha(LOT_OK))}", 15, fill=SEC)]
    c.append(group("formulario", f, 0, 146))
    y = 146 + fh + 24
    c += button(pad, y, fw, "Guardar cambios")
    c += link(pad + fw / 2, y + 86, "Cancelar", 17, anchor="middle")
    db, dh = delete_block(pad, fw, y + 116)
    c += db
    ch = dh + 30
    h = max(DESKTOP[1], 112 + ch + 40)
    zoom = 1.5
    center = (sum(x for x, _ in LOT_OK) / 5 - 210 / zoom, sum(y for _, y in LOT_OK) / 5 - 120 / zoom)
    b = map_view(w, h, center, zoom, lot_shape(LOT_OK, s=zoom) + area_chip(LOT_OK, zoom), "recorte-editar")
    b += topbar(w, active="Mi finca", user="Rosa")
    b += zoom_controls(w - 88, 116)
    bar, bw = draw_toolbar(0, 0, "mover")
    b += [group("dibujo", bar, 500 + (w - 500 - bw) / 2, h - 132)]
    b += scale_bar(500, h - 44, zoom)
    b += attribution(w - 12, h - 30)
    b += card(32, 112, cw, ch) + [group("panel", c, 32, 112)]
    return frame((w, h), b)


def mobile(dialog=False):
    w = MOBILE[0]
    zoom = 1.1
    center = (sum(x for x, _ in LOT_OK) / 5, sum(y for _, y in LOT_OK) / 5 - 20)
    mh = 330
    b = map_view(w, mh + 40, center, zoom, lot_shape(LOT_OK, s=zoom) + area_chip(LOT_OK, zoom), "recorte-editar-m" + ("d" if dialog else ""))
    b += topbar(w)
    b += [group("editar", tool_button(0, 0, G["mover"], True, name="mover-puntos"), w - 60, 86)]
    b += attribution(w - 8, mh - 4)
    pad, fw = 22, w - 44
    f, fh = form(pad, fw, compact=True)
    s = [poly(chamfer(w / 2 - 28, 10, 56, 6, 3), BORDE)]
    s += link(pad, 50, "‹ Volver al lote", 15)
    s += [text(pad, 82, "EDITAR LOTE", 14, 700, SEC), text(pad, 116, "El Alto", 28, 600, font=FONT_TITLE)]
    s.append(group("formulario", f, 0, 140))
    y = 140 + fh + 24
    s += button(pad, y, fw, "Guardar cambios")
    s += link(w / 2, y + 86, "Cancelar", 17, anchor="middle")
    db, dh = delete_block(pad, fw, y + 116, compact=True)
    s += db
    sh = dh + 40
    s = [poly(chamfer(0, 0, w, sh, 20), WHITE)] + s
    b += [group("hoja", s, 0, mh)]
    h = mh + sh
    if dialog:
        b.append(f'<rect id="velo" width="{w}" height="{h}" fill="{P["noche"]}" fill-opacity="0.62"/>')
        dw, dy = w - 32, 220
        d = [text(24, 52, "¿Borrar El Alto?", 26, 600, font=FONT_TITLE)]
        items = ([f"Deja de verse en Mi finca con sus", f"{len(planted(ALTO))} cultivos en curso y su historial."],
                 [f"Puede restaurarlo hasta el {UNTIL}", "en «Borrados hace poco»."],
                 ["Pasados 30 días se borra del todo."])
        yy = 92
        for rows in items:
            d.append(poly([(24, yy - 13), (36, yy - 13), (36, yy - 1), (24, yy - 1)], D["rojo"]))
            d += paragraph(48, yy, rows, 16, 22)
            yy += len(rows) * 22 + 14
        d += button(24, yy + 6, dw - 48, "No, volver") + button(24, yy + 76, dw - 48, "Sí, borrar el lote", "danger")
        dh_ = yy + 154
        b += card(16, dy, dw, dh_, "dialogo") + [group("dialogo-contenido", d, 16, dy)]
    return frame((w, h), b)


SCREENS = {
    "finca-02-editar-lote-escritorio": desktop,
    "finca-02-editar-lote-movil": mobile,
    "finca-02-editar-lote-borrar-movil": lambda: mobile(dialog=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
