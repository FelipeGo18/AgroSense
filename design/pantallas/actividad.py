"""Tanda 8: «Mi actividad» en Mi cuenta (HU-178). Escritorio y móvil.

GET /me/activity: los eventos de `activity_log` del usuario y las acciones de soporte sobre sus datos, del más
reciente al más antiguo, de a 50 («Ver más antiguos» pide la página siguiente con `before`). Cada evento dice quién
(usted o soporte), qué, cuándo y su resultado (`ok`, `denied`, `failed`) con forma y texto, nunca solo color. Nunca
muestra valores de los campos, el polígono ni el usuario de un intento fallido: solo qué campos cambiaron. Como un
intento de entrada fallido no guarda de quién fue, tampoco aparece aquí. Se guarda 180 días. Los eventos son los
mismos que ve el administrador en la bitácora (admin.py) y los reportes de transversal.py. Nombres y fechas de muestra.

    python design/pantallas/actividad.py     # escribe svg/cuenta-08-mi-actividad-*.svg
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402,F401
from calendario import wrap_lines  # noqa: E402
from ui import BORDE, D, DIR, FONT_TITLE, MOBILE, P, SEC, WHITE, button, card, chamfer, frame, group, link, paragraph, poly, text, topbar  # noqa: E402

OK, DENIED, FAILED = "ok", "denied", "failed"
OUTCOME = {OK: ("Hecho", D["oliva"], "#E9F2D8"), DENIED: ("Rechazado", D["rojo"], "#FBE6E2"), FAILED: ("Falló", D["calabaza"], "#FCEBD6")}
# (día, hora, quién, qué, detalle, resultado). `details.fields` solo trae nombres de campos, nunca valores.
EVENTS = (
    ("Hoy", "10:42", "Usted", "Editó el lote El Alto", "Cambió: riego", OK),
    ("Hoy", "10:30", "Usted", "Entró a su cuenta", None, OK),
    ("10 oct", "17:50", "Usted", "Cerró sesión", None, OK),  # `auth.logout`. Un intento fallido no guarda de quién fue: no puede salir aquí
    ("9 oct", "16:20", "Soporte", "Vio sus lotes para resolver su reporte", "Reporte del 9 de octubre", OK),
    ("8 oct", "07:55", "Usted", "Intentó cambiar la contraseña", "La contraseña actual no era correcta", DENIED),
    ("3 oct", "09:12", "Usted", "Borró el lote La Loma", "Se puede restaurar hasta el 2 nov", OK),
    ("3 oct", "09:05", "Usted", "Borró una siembra de fríjol en El Alto", "Se puede restaurar hasta el 2 nov", OK),
    ("1 sep", "07:15", "Usted", "Registró la siembra de haba en El Alto", None, OK),
    ("16 ago", "11:03", "Usted", "Registró la siembra de cebolla en El Alto", None, OK),
    ("2 ago", "08:40", "Usted", "Registró la siembra de papa en El Alto", None, OK),
)


def outcome_mark(x, y, outcome):
    label, ink, fill = OUTCOME[outcome]
    out = [poly(chamfer(x, y, 22, 22, 4 if outcome == OK else 0), fill, ink, 2)]
    cx, cy = x + 11, y + 11
    if outcome == OK:
        out.append(f'<polyline points="{cx - 6},{cy} {cx - 2},{cy + 5} {cx + 6},{cy - 5}" fill="none" stroke="{ink}" stroke-width="2.5" stroke-linecap="round"/>')
    elif outcome == DENIED:
        out.append(f'<path d="M{cx - 5} {cy - 5} l10 10 M{cx + 5} {cy - 5} l-10 10" stroke="{ink}" stroke-width="2.5" stroke-linecap="round"/>')
    else:
        out.append(f'<rect x="{cx - 1.5}" y="{cy - 6}" width="3" height="8" fill="{ink}"/><rect x="{cx - 1.5}" y="{cy + 4}" width="3" height="3" fill="{ink}"/>')
    return out


def event_row(x, y, w, ev, mobile=False):
    day, hour, who, what, detail, outcome = ev
    label, ink, _ = OUTCOME[outcome]
    support = who == "Soporte"
    lines = wrap_lines([what], 30 if mobile else 70)
    h = 30 + len(lines) * 22 + (20 if detail else 0) + (22 if mobile else 0) + 10
    body = [f'<rect x="0" y="{h - 1}" width="{w}" height="1" fill="{BORDE}"/>']
    body += outcome_mark(0, 16, outcome)
    tx = 38
    body += paragraph(tx, 32, lines, 16, 22, weight=700)
    yy = 32 + len(lines) * 22 - 2
    if detail:
        body.append(text(tx, yy, detail, 13, fill=SEC))
        yy += 20
    who_label = f"{who} · {day}, {hour}"
    if mobile:
        body.append(text(tx, yy, who_label, 13, 700 if support else 400, D["cielo"] if support else SEC))
        body.append(text(w, 32, label, 13, 700, ink, anchor="end"))
    else:
        body.append(text(w, 32, who_label, 14, 700 if support else 400, D["cielo"] if support else SEC, anchor="end"))
        body.append(text(w, 52, label, 13, 700, ink, anchor="end"))
    return [group("evento", body, x, y)], h


def legend(x, y, mobile=False):
    out, lx, ly = [], 0, 0
    for k in (OK, DENIED, FAILED):
        out += outcome_mark(lx, ly, k)
        out.append(text(lx + 30, ly + 16, OUTCOME[k][0], 14))
        lx += 130 if not mobile else 110
    return [group("leyenda", out, x, y)]


def activity(mobile=False):
    w = MOBILE[0] if mobile else 1440
    cw = w - 24 if mobile else 960
    x0 = 12 if mobile else (w - cw) / 2
    pad = 20 if mobile else 40
    iw = cw - 2 * pad
    c = []
    c += link(pad, 44, "‹ Mi cuenta", 15)
    c += [text(pad, 92, "Mi actividad", 30 if mobile else 38, 600, font=FONT_TITLE)]
    intro = (["Lo que se hizo con su cuenta y sus lotes,", "también lo que hizo soporte. Se guarda", "180 días y no muestra lo que escribió."] if mobile else
             ["Lo que se hizo con su cuenta y sus lotes, también lo que hizo soporte. Se guarda 180 días y no muestra lo que escribió."])
    c += paragraph(pad, 124, intro, 15, 22, fill=SEC)
    y = 124 + len(intro) * 22 + 10
    c += legend(pad, y, mobile)
    y += 46
    for ev in EVENTS:
        r, rh = event_row(pad, y, iw, ev, mobile)
        c += r
        y += rh
    y += 24
    c += button(pad, y, iw if mobile else 280, "Ver más antiguos", "secondary")
    y += 92
    c += paragraph(pad, y, ["Lo anterior al 14 de abril de 2026 ya se borró."], 13, fill=SEC)
    c += link(pad, y + 34, "¿Ve algo que no hizo? Repórtelo" if mobile else "¿Ve algo que no hizo? Reporte un problema", 15)
    ch = y + 64
    top = 100 if mobile else 120
    b = [f'<rect width="{w}" height="3000" fill="{P["niebla"]}"/>'] + topbar(w, user=None if mobile else "Rosa")
    b += card(x0, top, cw, ch) + [group("mi-actividad", c, x0, top)]
    return ui.long_page((w, top + ch + 60), b, P["niebla"])


SCREENS = {"cuenta-08-mi-actividad-escritorio": activity, "cuenta-08-mi-actividad-movil": lambda: activity(mobile=True)}

if __name__ == "__main__":
    out = DIR / "svg"
    for name, draw in SCREENS.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8", newline="\n")
        print(name)
