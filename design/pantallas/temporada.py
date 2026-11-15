"""Tanda 11 · «Editar o borrar una siembra» (HU-165). Escritorio, móvil y la confirmación de borrar.

Se abre con «Editar» en una siembra del historial (historial.py). Corrige el cultivo, el área, la fecha de siembra,
la de cosecha y lo que había antes en ese terreno, con PATCH /seasons/{id} y las mismas validaciones de registrar
(el área cabe en el lote; lo de antes está cosechado y es del mismo lote). «Borrar esta siembra» llama a
DELETE /seasons/{id}: es reversible durante 30 días desde «Borrados hace poco» en el historial (HU-204, P1).

A la derecha, cómo queda el historial con el cambio: de qué siembra viene y si la rotación cumple su regla. Una
rotación que no cumple se muestra como un hecho, sin puntaje ni regaño.

Qué hace cada control: «Guardar cambios» envía el PATCH; «Cancelar» y «‹ El Alto» vuelven al historial sin
guardar; «Borrar esta siembra» abre la confirmación; «No, volver» la cierra; «Sí, borrar la siembra» envía el DELETE.

Por decidir (no está en las specs): qué pasa con el diagnóstico guardado al sembrar si se corrige el cultivo o la
fecha. Aquí se dice lo único seguro: el diagnóstico guardado es el que se vio ese día y no se recalcula (R4).
El ejemplo es la arveja de enero de 2026 de El Alto. Los nombres y las cifras son de muestra.

    python design/pantallas/temporada.py     # escribe svg/finca-11-editar-siembra-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from historial import check, form_page, wrap_lines  # noqa: E402
from ui import BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, checkbox, field, frame, group, link, paragraph, poly, text  # noqa: E402

UNTIL = "10 de noviembre"  # hoy, 11 de octubre, más 30 días
BEFORE = (("Arveja", "1,68 ha · cosechada el 18 dic 2025", True), ("Zanahoria", "0,41 ha · cosechada el 24 ene 2026", False),
          ("Nada: primera siembra aquí", "Tierra del lote que no había sembrado", False))


def before_list(x, y, w, mobile=False):
    """«¿Qué había antes en este terreno?», con lo que estaba cosechado antes de esta siembra (`follows_season_ids`)."""
    out = [text(0, 0, "¿Qué había antes en este terreno?", 18, 700), text(0, 24, "Marque una o varias.", 14, fill=SEC)]
    ry = 40
    for name, sub, on in BEFORE:
        out.append(poly(chamfer(0, ry, w, 58, 10), "#FFF6EA" if on else WHITE, P["calabaza"] if on else BORDE, 2 if on else 1.5))
        out += checkbox(14, ry + 13, on, name=f"casilla-{name.lower().split(':')[0].replace(' ', '-')}")
        out += [text(58, ry + 25, name, 16, 700), text(58, ry + 45, sub, 13, fill=SEC)]
        ry += 68
    return [group("antes-en-este-terreno", out, x, y)], ry


def saved_diagnosis(x, y, w):
    n = int((w - 70) / 7.2)
    lines = wrap_lines(["El diagnóstico que vio al sembrar se conserva como lo vio ese día: luz amarilla, sin riego (datos 2026.01.0 · reglas 1.0.0). No se vuelve a calcular."], n)
    h = 28 + len(lines) * 20
    body = [poly(chamfer(0, 0, w, h, 10), "#F2F5F7", BORDE, 1.5), poly([(26, h / 2 - 10), (36, h / 2), (26, h / 2 + 10), (16, h / 2)], D["cielo"])]
    body += paragraph(50, 26, lines, 14, 20)
    return [group("diagnostico-guardado", body, x, y)], h


def delete_block(x, y, w, mobile=False):
    out = [f'<rect x="0" y="0" width="{w}" height="2" fill="{BORDE}"/>', text(0, 40, "Borrar esta siembra", 18, 700)]
    rows = (["Deja de verse en el historial y no cuenta", "en su progreso. Puede restaurarla durante", "30 días."] if mobile else
            ["Deja de verse en el historial y no cuenta en su progreso.", "Puede restaurarla durante 30 días."])
    out += paragraph(0, 66, rows, 15, 21, fill=SEC)
    by = 66 + len(rows) * 21 + 6
    out += button(0, by, min(w, 260), "Borrar esta siembra", "danger")
    return [group("borrar-siembra", out, x, y)], by + 60


def history_card(x, y, w):
    """Cómo queda el historial con el cambio: la relación con la siembra anterior y si cumple su regla."""
    body = [text(24, 40, "CÓMO QUEDA EL HISTORIAL", 14, 700, SEC), text(24, 72, "Arveja después de arveja", 20, 600, font=FONT_TITLE)]
    rows = (("Arveja", "1,68 ha · ago – dic 2025", None), ("Arveja", "0,42 ha · ene – jun 2026 · la que edita", "bad"))
    yy = 96
    for i, (name, sub, state) in enumerate(rows):
        on = i == 1
        body.append(poly(chamfer(24, yy, w - 48, 60, 10), "#FFF6EA" if on else WHITE, P["calabaza"] if on else BORDE, 2 if on else 1.5))
        body += [text(40, yy + 26, name, 16, 700), text(40, yy + 46, sub, 13, fill=SEC)]
        yy += 60
        if i == 0:
            body.append(poly([(w / 2 - 7, yy + 6), (w / 2 + 7, yy + 6), (w / 2, yy + 18)], P["noche"]))
            yy += 24
    yy += 20
    body += check(34, yy + 2, False, 0.9)
    lines = wrap_lines(["Repite la familia (leguminosas)."], int((w - 100) / 7.4))
    body += paragraph(52, yy + 7, lines, 15, 20, weight=700, fill=D["rojo"])
    yy += len(lines) * 20 + 10
    note = wrap_lines(["Se muestra como un hecho de su historial: no tiene puntaje ni cambia lo que ya cosechó.", "Regla: no repetir la familia · catálogo de rotación"], int((w - 48) / 7.3))
    body += paragraph(24, yy + 10, note, 14, 21, fill=SEC)
    h = yy + 10 + len(note) * 21 + 14
    return card(x, y, w, h, "tarjeta-historial") + [group("historial", body, x, y)], h


def edit(mobile=False, dialog=False):
    w = MOBILE[0] if mobile else 1440
    b, pad = form_page(w, mobile)
    fx, fy, fw = (pad, 150, w - 2 * pad) if mobile else (48, 172, 640)
    ip = 20 if mobile else 36
    iw = fw - 2 * ip
    c = [text(ip, 46, "EDITAR SIEMBRA · EL ALTO", 14, 700, SEC), text(ip, 88, "Arveja de enero de 2026", 26 if mobile else 32, 600, font=FONT_TITLE),
         text(ip, 114, "0,42 ha · cosechada" if mobile else "0,42 ha · sembrada el 12 de enero de 2026 · cosechada el 20 de junio de 2026", 15, fill=SEC)]
    yy = 156
    c += field(ip, yy, iw, "Cultivo", "Arveja", trailing="▾", name="campo-cultivo")
    yy += 104
    half = iw if mobile else (iw - 16) / 2
    c += field(ip, yy, half, "Área que sembró (ha)", "0,42", name="campo-area")
    if mobile:
        yy += 104
    c += field(ip if mobile else ip + half + 16, yy, half, "Fecha de siembra", "12 de enero de 2026", trailing="▾", name="campo-fecha-siembra")
    yy += 104
    c += field(ip, yy, half, "Fecha de cosecha", "20 de junio de 2026", trailing="▾", name="campo-fecha-cosecha", hint="Vacía, si sigue en curso.")
    yy += 136
    bl, bh = before_list(ip, yy, iw, mobile)
    c += bl
    yy += bh + 18
    sd, sh = saved_diagnosis(ip, yy, iw)
    c += sd
    yy += sh + 24
    c += button(ip, yy, iw, "Guardar cambios")
    c += link(fw - ip, yy + 90, "Cancelar", 16, anchor="end")
    yy += 116
    db, dh = delete_block(ip, yy, iw, mobile)
    c += db
    ch = yy + dh + 20
    b += card(fx, fy, fw, ch) + [group("formulario", c, fx, fy)]
    sx, sy, sw = (pad, fy + ch + 24, w - 2 * pad) if mobile else (48 + fw + 24, fy, w - 96 - fw - 24)
    hc, hh = history_card(sx, sy, sw)
    b += hc
    h = max(fy + ch, sy + hh) + 60
    if dialog:
        b.append(f'<rect id="velo" width="{w}" height="{h}" fill="{P["noche"]}" fill-opacity="0.62"/>')
        dw = w - 32 if mobile else 560
        dx, dy = (16, 240) if mobile else ((w - dw) / 2, 250)
        d = [text(24, 52, "¿Borrar esta siembra?", 24 if mobile else 30, 600, font=FONT_TITLE)]
        items = (["Arveja · 0,42 ha · ene – jun 2026 deja de", "verse en el historial de El Alto."] if mobile else ["Arveja · 0,42 ha · ene – jun 2026 deja de verse en el historial de El Alto."],
                 ["Puede restaurarla hasta el", f"{UNTIL}, en «Borrados", "hace poco»."] if mobile else [f"Puede restaurarla hasta el {UNTIL} en «Borrados hace poco»."],
                 ["Las siembras que vinieron después", "quedan sin lo que había antes."] if mobile else ["Las siembras que vinieron después quedan sin lo que había antes."])
        yy = 92
        for rows in items:
            d.append(poly([(24, yy - 13), (36, yy - 13), (36, yy - 1), (24, yy - 1)], D["rojo"]))
            d += paragraph(48, yy, rows, 16, 22)
            yy += len(rows) * 22 + 14
        if mobile:
            d += button(24, yy + 6, dw - 48, "No, volver") + button(24, yy + 76, dw - 48, "Sí, borrar la siembra", "danger")
            dh_ = yy + 154
        else:
            bw = (dw - 64) / 2
            d += button(24, yy + 6, bw, "No, volver") + button(40 + bw, yy + 6, bw, "Sí, borrar la siembra", "danger")
            dh_ = yy + 88
        b += card(dx, dy, dw, dh_, "dialogo") + [group("dialogo-contenido", d, dx, dy)]
    return frame((w, h), b, P["niebla"])


SCREENS = {
    "finca-11-editar-siembra-escritorio": lambda: edit(),
    "finca-11-editar-siembra-movil": lambda: edit(mobile=True),
    "finca-11-editar-siembra-borrar-escritorio": lambda: edit(dialog=True),
    "finca-11-editar-siembra-borrar-movil": lambda: edit(mobile=True, dialog=True),
}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
